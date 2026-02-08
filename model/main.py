import asyncio
import datetime
import json
import logging
import psutil
import platform
import sys
from pathlib import Path
from typing import Any

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types  # Used for constructing user messages

logging.basicConfig(level=logging.WARNING)  
LOG_FILE = Path("agent_logs.json")


def write_log(tool_used: str, user_input: str, response: str):
    """Write a log entry to the JSON log file."""
    try:
        logs = []
        if LOG_FILE.exists():
            try:
                with open(LOG_FILE, 'r') as f:
                    logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
        
        log_entry = {
            "TOOL_USED": tool_used,
            "TIMESTAMP": datetime.datetime.now().isoformat(),
            "USER_INPUT": user_input,
            "RESPONSE": response
        }
        
        logs.append(log_entry)
        
        with open(LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to write log: {e}")

#tools
def gettime() -> str:
    """
    Returns the current server time in a structured JSON format.
    Use this tool when the user asks for the current time, date, or timestamp.
    
    Returns:
        str: JSON string with current time information
    """
    now = datetime.datetime.now()
    result = {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "timezone": "Local"
    }
    return json.dumps(result)


def get_system_metrics() -> str:
    """
    Returns current system metrics in a structured JSON format.
    Use this tool when the user asks about system performance, resource usage, or system status.
    
    Returns:
        str: JSON string containing system metrics
    """
    try:
        # Quick CPU check (no interval for speed)
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        
        # Memory Information
        memory = psutil.virtual_memory()
        
        # Disk Information
        disk = psutil.disk_usage('/')
        
        # System Information
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime_seconds = (datetime.datetime.now() - boot_time).total_seconds()
        
        metrics = {
            "status": "success",
            "system": {
                "platform": platform.system(),
                "hostname": platform.node(),
                "uptime_hours": round(uptime_seconds / 3600, 2)
            },
            "cpu": {
                "usage_percent": round(cpu_percent, 1),
                "cores": cpu_count_logical,
                "physical_cores": cpu_count_physical
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "usage_percent": round(memory.percent, 1)
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "usage_percent": round(disk.percent, 1)
            }
        }
        
        return json.dumps(metrics)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        })


#defining the llm model and its endpoint with ollama
llm_model = LiteLlm(
    model="ollama_chat/phi4-mini",
    api_base="http://localhost:11434"
)

root_agent = Agent(
    name="parsing_engine",
    model=llm_model,
    description="An intelligent assistant that processes user requests and provides accurate, helpful responses.",
    instruction="""You are a precise and efficient AI assistant. Your role is to understand user intent and respond appropriately.

CORE PRINCIPLES:
1. Be direct and concise - avoid unnecessary elaboration
2. Use tools when appropriate to provide accurate information
3. Parse tool outputs (which are in JSON format) and present them naturally to users
4. Stay focused on the user's actual question

TOOL USAGE GUIDELINES:

When user asks about TIME/DATE:
- Use 'gettime' tool
- Parse the JSON response and present it naturally
- Example: "It's 10:30 AM on Monday, February 9th, 2026"

When user asks about SYSTEM PERFORMANCE/METRICS:
- Use 'get_system_metrics' tool
- Parse the JSON response and highlight key information
- Example: "Your system is running well. CPU usage is at 15%, memory usage is 45% (7.2GB used of 16GB), and disk usage is 60%."

For GENERAL CONVERSATION:
- Respond naturally and helpfully
- Keep responses brief and relevant
- Don't mention tools or technical details unless asked

RESPONSE STYLE:
- Direct and conversational
- No unnecessary preambles like "Based on the information..." or "According to..."
- Present information as if you know it directly
- Use natural language, not technical jargon
- Keep responses under 3 sentences when possible

EXAMPLES:

User: "What time is it?"
You: "It's 10:30:45 PM on Sunday, February 9th, 2026."

User: "How's my system doing?"
You: "Your system is running smoothly. CPU is at 12%, memory usage is 45% (7.2GB of 16GB), and you have 150GB free disk space."

User: "Hello"
You: "Hi! How can I help you today?"

Remember: Be helpful, accurate, and concise. Parse tool outputs and present them naturally.""",
    tools=[gettime, get_system_metrics]
)

async def run_single_query(user_input: str) -> str:
    """Execute a single query and return the response."""
    app_name = "parsing_engine_app"
    session_id = f"cli_session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    user_id = "cli_user"
    session_service = InMemorySessionService()
    
    # Create the session
    try:
        await session_service.create_session(
            app_name=app_name,
            session_id=session_id,
            user_id=user_id
        )
    except Exception:
        pass  
    
    runner = Runner(
        app_name=app_name,
        agent=root_agent,
        session_service=session_service
    )
    
    # Wrap the input in a Content object
    user_msg = types.Content(
        role="user",
        parts=[types.Part(text=user_input)]
    )
    
    tools_used = []
    
    final_response = None
    async for event in runner.run_async(
        session_id=session_id,
        user_id=user_id,
        new_message=user_msg
    ):
        # Track tool usage - check multiple possible attributes
        if hasattr(event, 'tool_call') and event.tool_call:
            tool_name = event.tool_call.name if hasattr(event.tool_call, 'name') else 'unknown'
            tools_used.append(tool_name)
        elif hasattr(event, 'function_call') and event.function_call:
            tool_name = event.function_call.name if hasattr(event.function_call, 'name') else 'unknown'
            tools_used.append(tool_name)
        elif hasattr(event, 'type') and 'tool' in str(event.type).lower():
            # Generic tool event detection
            if hasattr(event, 'name'):
                tools_used.append(event.name)
        
        # Capture content from events
        if hasattr(event, 'content') and event.content:
            final_response = event.content
        elif hasattr(event, 'text') and event.text:
            final_response = event.text
    
    response_text = "No response received from agent."
    
    try:
        session = await session_service.get_session(
            app_name=app_name,
            session_id=session_id,
            user_id=user_id
        )
        
        if session and session.messages and len(session.messages) > 0:
            last_message = session.messages[-1]
            if last_message.role == "model" and last_message.parts and len(last_message.parts) > 0:
                # Extract text from the Part object
                part = last_message.parts[0]
                if hasattr(part, 'text'):
                    response_text = part.text.strip()
    except Exception:
        pass
    
    # Fallback to final_response if session didn't work
    if response_text == "No response received from agent." and final_response:
        if isinstance(final_response, str):
            response_text = final_response.strip()
        elif hasattr(final_response, 'parts') and len(final_response.parts) > 0:
            if hasattr(final_response.parts[0], 'text'):
                response_text = final_response.parts[0].text.strip()
        elif hasattr(final_response, 'text'):
            response_text = final_response.text.strip()
    
    # Log the interaction
    tool_name = tools_used[0] if tools_used else "conversation"
    write_log(tool_name, user_input, response_text)
    
    return response_text

async def interactive_mode():
    """Run the agent in interactive mode."""
    print(f"Agent '{root_agent.name}' initialized")
    print(f"Model: {llm_model.model}")
    print(f"Tools: {[tool.__name__ for tool in root_agent.tools]}")
    print(f"Logs: {LOG_FILE.absolute()}")
    print("\nType 'exit' or 'quit' to end the session.\n")
    print("="*60)
    
    app_name = "parsing_engine_app"
    session_id = "interactive_session"
    user_id = "user_01"
    
    session_service = InMemorySessionService()
    
    try:
        await session_service.create_session(
            app_name=app_name,
            session_id=session_id,
            user_id=user_id
        )
    except Exception:
        pass
    
    runner = Runner(
        app_name=app_name,
        agent=root_agent,
        session_service=session_service
    )
    
    while True:
        try:
            user_input = input("\nUser: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("\nGoodbye!")
                break
            
            user_msg = types.Content(
                role="user",
                parts=[types.Part(text=user_input)]
            )
            
            print("Processing...\n")
            # Track tools used
            tools_used = []
            final_response = None
            
            async for event in runner.run_async(
                session_id=session_id,
                user_id=user_id,
                new_message=user_msg
            ):
                # Track tool usage
                if hasattr(event, 'tool_call') and event.tool_call:
                    tools_used.append(event.tool_call.name if hasattr(event.tool_call, 'name') else 'unknown')
                
                if hasattr(event, 'content') and event.content:
                    final_response = event.content
                elif hasattr(event, 'text') and event.text:
                    final_response = event.text
            
            response_text = "No response received from agent."
            
            try:
                session = await session_service.get_session(
                    app_name=app_name,
                    session_id=session_id,
                    user_id=user_id
                )
                
                if session and session.messages and len(session.messages) > 0:
                    last_message = session.messages[-1]
                    if last_message.role == "model" and last_message.parts and len(last_message.parts) > 0:
                        part = last_message.parts[0]
                        if hasattr(part, 'text'):
                            response_text = part.text.strip()
            except Exception:
                pass
            
            if response_text == "No response received from agent." and final_response:
                if isinstance(final_response, str):
                    response_text = final_response.strip()
                elif hasattr(final_response, 'parts') and len(final_response.parts) > 0:
                    if hasattr(final_response.parts[0], 'text'):
                        response_text = final_response.parts[0].text.strip()
                elif hasattr(final_response, 'text'):
                    response_text = final_response.text.strip()
            
            # Display response
            if response_text != "No response received from agent.":
                print(f" Agent: {response_text}")
                print("-"*60)
            else:
                print("No response received from agent.")
            
            # Log the interaction
            tool_name = tools_used[0] if tools_used else "conversation"
            write_log(tool_name, user_input, response_text)
                
        except KeyboardInterrupt:
            print("\n Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n Error: {str(e)}")
            print("\nContinuing...\n")
            
async def main():
    """Main entry point - handles CLI arguments or interactive mode."""
    if len(sys.argv) > 1:
        # CLI mode - single query
        if sys.argv[1] in ["-h", "--help"]:
            print("Usage:")
            print("  python main.py <prompt>           # Single query mode")
            print("  python main.py                    # Interactive mode")
            print("  python main.py --help             # Show this help")
            print("\nExamples:")
            print("  python main.py 'What time is it?'")
            print("  python main.py 'Show me system metrics'")
            print(f"\nLogs are stored in: {LOG_FILE.absolute()}")
            return
        
