"""
NLP Engine for the Nexus Intelligent Chatbot System.

Parses natural language commands into structured intents and entities
using Gemini API and RAG service integration.
"""

import json
import re
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from chat.chat_api import _generate_gemini_reply
from model.rag_service import RAGService
from nexus.config import config
from nexus.models import (
    Intent, EntityType, Entity, ParsedIntent, User, UserRole
)


class NLPEngine:
    """
    Natural Language Processing Engine for Nexus.
    
    Parses natural language commands into structured intents and entities
    using Gemini API with structured prompts and RAG service integration.
    """
    
    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        rag_service: Optional[RAGService] = None,
        confidence_threshold: float = 0.5
    ):
        """
        Initialize NLP Engine.
        
        Args:
            gemini_api_key: Gemini API key. If None, uses config.
            rag_service: RAGService instance. If None, creates new.
            confidence_threshold: Minimum confidence for parsing (0-1).
        """
        self.gemini_api_key = gemini_api_key or config.GEMINI_API_KEY
        self.rag_service = rag_service or RAGService()
        self.confidence_threshold = confidence_threshold
        
        # Intent descriptions for Gemini prompts
        self._intent_descriptions = {
            Intent.CHECK_STATUS: "Check the status of a server, service, or system component",
            Intent.RESTART_SERVICE: "Restart or start a specific service",
            Intent.QUERY_METRICS: "Query system metrics like CPU, memory, disk usage",
            Intent.SCHEDULE_MEETING: "Schedule a meeting or appointment",
            Intent.SET_REMINDER: "Set a reminder for a future task",
            Intent.REGISTER_SCRIPT: "Register a new executable script",
            Intent.UNKNOWN: "Unknown or unrecognized command"
        }
        
        # Entity patterns for extraction
        self._entity_patterns = {
            EntityType.SERVER: [
                r'\b(server|host|machine|instance|vm)\s+(?:name|id)?\s*(?:is)?\s*["\']?([a-zA-Z0-9_-]+)["\']?',
                r'\b([a-zA-Z0-9_-]+)\.(?:com|net|org|local)\b',
                r'\b(?:on|at|to)\s+(?:the\s+)?(server|host)\b',
            ],
            EntityType.SERVICE: [
                r'\b(service|daemon|process)\s+(?:name|id)?\s*(?:is)?\s*["\']?([a-zA-Z0-9_-]+)["\']?',
                r'\b(restart|start|stop|status)\s+(?:of\s+)?(the\s+)?([a-zA-Z0-9_-]+)\b',
                r'\b([a-zA-Z0-9_-]+)\s+(?:service|daemon|process)\b',
            ],
            EntityType.TIME: [
                r'\b(in\s+)?(\d+)\s+(minutes?|hours?|days?|weeks?|months?)\b',
                r'\b(today|tomorrow|yesterday)\b',
                r'\b(at\s+)?(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?)\b',
                r'\b(next\s+(?:week|month|year))\b',
            ],
            EntityType.METRIC: [
                r'\b(cpu|memory|ram|disk|storage|network|bandwidth)\b',
                r'\b(usage|utilization|percentage|load)\b',
                r'\b(temperature|fan|voltage|power)\b',
            ],
            EntityType.SCRIPT_NAME: [
                r'\b(script|file|program)\s+(?:name|id)?\s*(?:is)?\s*["\']?([a-zA-Z0-9_.-]+)["\']?',
                r'\b([a-zA-Z0-9_-]+)\.(?:py|sh|bash|js)\b',
            ],
            EntityType.USER_EMAIL: [
                r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
                r'\b(user|email|account)\s+(?:for|of)?\s*["\']?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']?',
            ],
        }
    
    async def parse_command(self, user_input: str, user: Optional[User] = None) -> ParsedIntent:
        """
        Parse natural language command into intent and entities.
        
        Args:
            user_input: Raw user command
            user: Authenticated user (optional, for context)
            
        Returns:
            ParsedIntent with intent, entities, and confidence score
        """
        # Build context-aware prompt
        prompt = self._build_parse_prompt(user_input, user)
        
        # Call Gemini API for structured parsing
        response = await self._call_gemini_for_parsing(prompt)
        
        # Parse Gemini response
        parsed = self._parse_gemini_response(response, user_input)
        
        # Extract entities from command using patterns
        entities = self._extract_entities_with_patterns(user_input, parsed.intent)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(parsed.intent, entities, response)
        
        return ParsedIntent(
            intent=parsed.intent,
            entities=entities,
            confidence=confidence,
            raw_command=user_input
        )
    
    def _build_parse_prompt(self, user_input: str, user: Optional[User] = None) -> str:
        """Build structured prompt for Gemini parsing."""
        context_info = ""
        if user:
            context_info = f"User: {user.email} (Role: {user.role.value})\n"
        
        intent_list = "\n".join(
            f"- {intent.value}: {desc}"
            for intent, desc in self._intent_descriptions.items()
        )
        
        return f"""You are an intent parser for an infrastructure management system.
Your task is to analyze the user's command and extract the intent and entities.

{context_info}
User Command: "{user_input}"

Available Intents:
{intent_list}

Entity Types:
- server: Server/host names (e.g., "web-server", "db-host")
- service: Service names (e.g., "nginx", "mysql", "redis")
- time: Time expressions (e.g., "tomorrow", "3pm", "in 2 hours")
- metric: System metrics (e.g., "cpu", "memory", "disk")
- script_name: Script file names
- user_email: Email addresses

Instructions:
1. Identify the PRIMARY intent from the list above
2. Extract ALL entities mentioned in the command
3. Return a JSON object with:
   - intent: The intent value (string)
   - entities: Array of objects with type and value
   - confidence: Your confidence score (0.0 to 1.0)
   - explanation: Brief explanation of your analysis

Example output format:
{{
  "intent": "restart_service",
  "entities": [
    {{"type": "service", "value": "nginx"}},
    {{"type": "server", "value": "web-server-01"}}
  ],
  "confidence": 0.85,
  "explanation": "User wants to restart the nginx service on web-server-01"
}}

Only return valid JSON. Do not include markdown formatting.

Analysis:"""
    
    async def _call_gemini_for_parsing(self, prompt: str) -> str:
        """Call Gemini API for structured parsing."""
        try:
            # Use the existing chat API's Gemini integration
            # We need to modify the prompt to get structured output
            structured_prompt = f"{prompt}\n\nJSON Response:"
            
            # Call Gemini with structured prompt
            response = await self._generate_structured_reply(structured_prompt)
            
            return response.strip()
            
        except Exception as e:
            # Fallback to unknown intent on error
            return json.dumps({
                "intent": "unknown",
                "entities": [],
                "confidence": 0.0,
                "explanation": f"Error during parsing: {str(e)}"
            })
    
    async def _generate_structured_reply(self, message: str) -> str:
        """Generate reply using Gemini API with structured output."""
        # This is a simplified version that calls the Gemini API directly
        # In production, this would use the existing chat_api module
        
        from urllib import error, request
        import json
        
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_API_KEY}"
            f"?key={config.GEMINI_API_KEY}"
        )
        
        # Use a system instruction that enforces JSON output
        system_prompt = (
            "You are an infrastructure command parser. "
            "Always respond with valid JSON only. "
            "Do not include any markdown formatting or additional text."
        )
        
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": message}],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for structured output
                "maxOutputTokens": 1024,
            },
        }
        
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        try:
            with request.urlopen(req, timeout=30) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body)
                
                # Extract text from response
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                
                return ""
                
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise Exception(f"Gemini API error: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise Exception(f"Gemini network error: {exc.reason}") from exc
    
    def _parse_gemini_response(self, response: str, user_input: str) -> ParsedIntent:
        """Parse Gemini response into ParsedIntent."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                intent_str = data.get("intent", "unknown")
                intent = self._string_to_intent(intent_str)
                
                entities_data = data.get("entities", [])
                entities = [
                    Entity(
                        entity_type=EntityType(e.get("type", "unknown")),
                        value=e.get("value", ""),
                        confidence=e.get("confidence", 1.0)
                    )
                    for e in entities_data
                ]
                
                return ParsedIntent(
                    intent=intent,
                    entities=entities,
                    confidence=data.get("confidence", 0.0),
                    raw_command=user_input
                )
                
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback parsing
            pass
        
        # Fallback: try to extract intent from text
        intent = self._infer_intent_from_text(user_input)
        return ParsedIntent(
            intent=intent,
            entities=[],
            confidence=0.3,
            raw_command=user_input
        )
    
    def _string_to_intent(self, intent_str: str) -> Intent:
        """Convert string to Intent enum."""
        try:
            return Intent(intent_str.lower())
        except ValueError:
            return Intent.UNKNOWN
    
    def _infer_intent_from_text(self, text: str) -> Intent:
        """Infer intent from text keywords."""
        text_lower = text.lower()
        
        # Check for restart-related keywords
        if any(word in text_lower for word in ["restart", "reboot", "start", "stop", "kill"]):
            return Intent.RESTART_SERVICE
        
        # Check for status-related keywords
        if any(word in text_lower for word in ["status", "check", "health", "running"]):
            return Intent.CHECK_STATUS
        
        # Check for metrics-related keywords
        if any(word in text_lower for word in ["cpu", "memory", "disk", "metrics", "usage", "performance"]):
            return Intent.QUERY_METRICS
        
        # Check for calendar-related keywords
        if any(word in text_lower for word in ["meeting", "schedule", "calendar", "remind", "appointment"]):
            if "schedule" in text_lower or "meeting" in text_lower:
                return Intent.SCHEDULE_MEETING
            return Intent.SET_REMINDER
        
        # Check for script-related keywords
        if any(word in text_lower for word in ["script", "register", "upload", "add"]):
            return Intent.REGISTER_SCRIPT
        
        return Intent.UNKNOWN
    
    def _extract_entities_with_patterns(self, text: str, intent: Intent) -> List[Entity]:
        """Extract entities using regex patterns."""
        entities = []
        
        for entity_type, patterns in self._entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Get the matched group(s)
                    groups = match.groups()
                    if groups:
                        value = groups[-1]  # Last group is usually the value
                        entities.append(Entity(
                            entity_type=entity_type,
                            value=value,
                            confidence=0.8
                        ))
        
        return entities
    
    def _calculate_confidence(
        self,
        intent: Intent,
        entities: List[Entity],
        response: str
    ) -> float:
        """
        Calculate overall confidence score.
        
        Combines:
        - Intent confidence from Gemini
        - Entity extraction confidence
        - Response quality indicators
        """
        base_confidence = 0.5
        
        # Parse response for confidence if available
        try:
            json_match = re.search(r'"confidence":\s*([\d.]+)', response)
            if json_match:
                base_confidence = float(json_match.group(1))
        except (ValueError, AttributeError):
            pass
        
        # Boost confidence for known intents
        if intent != Intent.UNKNOWN:
            base_confidence = min(base_confidence + 0.1, 1.0)
        
        # Adjust based on entity count
        if len(entities) > 0:
            base_confidence = min(base_confidence + 0.05 * len(entities), 1.0)
        
        # Reduce confidence if response looks like an error
        if "error" in response.lower() or "unknown" in response.lower():
            base_confidence = max(base_confidence - 0.2, 0.0)
        
        return round(base_confidence, 2)
    
    def get_low_confidence_fallback(self, intent: Intent) -> str:
        """Generate fallback message for low confidence parsing."""
        if intent == Intent.UNKNOWN:
            return (
                "I'm not sure what you're asking. Could you please rephrase your command? "
                "I can help with checking status, restarting services, querying metrics, "
                "scheduling meetings, or registering scripts."
            )
        return (
            f"I'm not confident about the intent '{intent.value}'. "
            "Could you please provide more details or rephrase your request?"
        )
    
    def get_intent_description(self, intent: Intent) -> str:
        """Get human-readable description of an intent."""
        return self._intent_descriptions.get(intent, "Unknown command")
    
    def get_available_intents(self) -> List[Dict[str, str]]:
        """Get list of available intents with descriptions."""
        return [
            {
                "value": intent.value,
                "description": desc
            }
            for intent, desc in self._intent_descriptions.items()
        ]
