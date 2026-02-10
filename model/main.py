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
from google.genai import types

logging.basicConfig(level=logging.WARNING)  
LOG_FILE = Path("agent_logs.json")


def write_log(tool_used: str, user_input: str, response: str):
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
    Use this tool when the user asks about system performance, CPU, memory, disk usage, or system status.
    
    Returns:
        str: JSON string containing system metrics
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime_seconds = (datetime.datetime.now() - boot_time).total_seconds()
        
        metrics = {
            "status": "success",
            "timestamp": datetime.datetime.now().isoformat(),
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
        
        return json.dumps(metrics, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        })


llm_model = LiteLlm(
    model="ollama_chat/phi4-mini",
    api_base="http://localhost:11434"
)

root_agent = Agent(
    name="parsing_engine",
    model=llm_model,
    description="An intelligent assistant that processes user requests and provides accurate, helpful responses.",
    instruction="""You are a precise AI assistant with access to specific tools. You MUST use these tools to get accurate information.

MANDATORY TOOL USAGE:
1. Time/Date queries → CALL gettime() function
   - "what time", "current time", "what's the time", "time now"
   - "what date", "current date", "today's date"
   
2. System queries → CALL get_system_metrics() function
   - "system stats", "server stats", "system metrics"
   - "CPU usage", "memory usage", "disk space"
   - "how is the system", "system performance"

DO NOT GUESS OR MAKE UP:
- Current time or date (always call gettime)
- System performance data (always call get_system_metrics)

WORKFLOW:
1. Identify if query needs a tool
2. Call the appropriate function
3. Parse the JSON response
4. Present result naturally to user

For general conversation, respond directly without tools.

Response style: Direct, natural, concise (2-3 sentences max).""",
    tools=[gettime, get_system_metrics]
)


async def run_single_query(user_input: str) -> str:
    app_name = "parsing_engine_app"
    session_id = f"cli_session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    user_id = "cli_user"
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
    
    user_msg = types.Content(
        role="user",
        parts=[types.Part(text=user_input)]
    )
    
    tools_used = []
    response_text = ""
    
    async for event in runner.run_async(
        session_id=session_id,
        user_id=user_id,
        new_message=user_msg
    ):
        print(f"[DEBUG] Event type: {type(event).__name__}")
        print(f"[DEBUG] Event attributes: {dir(event)}")
        
        if hasattr(event, 'tool_call') and event.tool_call:
            tool_name = getattr(event.tool_call, 'name', 'unknown')
            tools_used.append(tool_name)
            print(f"[DEBUG] Tool call detected: {tool_name}")
        elif hasattr(event, 'function_call') and event.function_call:
            tool_name = getattr(event.function_call, 'name', 'unknown')
            tools_used.append(tool_name)
            print(f"[DEBUG] Function call detected: {tool_name}")
        
        if hasattr(event, 'content'):
            print(f"[DEBUG] Event has content: {type(event.content)}")
            if hasattr(event.content, 'parts'):
                for part in event.content.parts:
                    print(f"[DEBUG] Part type: {type(part).__name__}, attributes: {dir(part)}")
                    if hasattr(part, 'text') and part.text:
                        response_text = part.text
                        print(f"[DEBUG] Found text in part: {part.text[:100]}")
            elif isinstance(event.content, str):
                response_text = event.content
                print(f"[DEBUG] Content is string: {event.content[:100]}")
        elif hasattr(event, 'text') and event.text:
            response_text = event.text
            print(f"[DEBUG] Event has text: {event.text[:100]}")
    
    if not response_text:
        response_text = "No response received from agent."
    
    response_text = response_text.strip() if response_text else "No response received from agent."
    tool_name = tools_used[0] if tools_used else "conversation"
    write_log(tool_name, user_input, response_text)
    
    return response_text


async def interactive_mode():
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
            tools_used = []
            response_text = ""
            
            async for event in runner.run_async(
                session_id=session_id,
                user_id=user_id,
                new_message=user_msg
            ):
                if hasattr(event, 'tool_call') and event.tool_call:
                    tool_name = getattr(event.tool_call, 'name', 'unknown')
                    tools_used.append(tool_name)
                    print(f"[Tool Called: {tool_name}]")
                elif hasattr(event, 'function_call') and event.function_call:
                    tool_name = getattr(event.function_call, 'name', 'unknown')
                    tools_used.append(tool_name)
                    print(f"[Function Called: {tool_name}]")
                
                if hasattr(event, 'content'):
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text = part.text
                    elif isinstance(event.content, str):
                        response_text = event.content
                elif hasattr(event, 'text') and event.text:
                    response_text = event.text
            
            if not response_text:
                response_text = "No response received from agent."
            
            response_text = response_text.strip()
            
            if response_text != "No response received from agent.":
                print(f"Agent: {response_text}")
                print("-"*60)
            else:
                print("No response received from agent.")
            
            tool_name = tools_used[0] if tools_used else "conversation"
            write_log(tool_name, user_input, response_text)
                
        except KeyboardInterrupt:
            print("\nSession interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("\nContinuing...\n")
            

async def main():
    if len(sys.argv) > 1:
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
        user_prompt = " ".join(sys.argv[1:])
        response = await run_single_query(user_prompt)
        print(response)
    else:
        await interactive_mode()
        

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated.")
