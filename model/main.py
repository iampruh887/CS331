import asyncio
import datetime
import json
import logging
import psutil
import platform
import sys
from pathlib import Path
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
                with open(LOG_FILE, "r") as f:
                    logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
        logs.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "tool_used": tool_used,
            "user_input": user_input,
            "response": response,
        })
        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=2)
    except Exception:
        pass


def gettime() -> str:
    """
    Returns the current server time in a structured JSON format.

    Use this tool when the user asks for:
    - Current time
    - Current date
    - What day it is
    - Timestamp information
    """
    now = datetime.datetime.now()
    return json.dumps({
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "timezone": "Local",
    }, indent=2)


def get_system_metrics() -> str:
    """
    Returns current system metrics in a structured JSON format.

    Use this tool when the user asks about:
    - System performance
    - CPU usage
    - Memory / RAM usage
    - Disk space
    - System status or server stats
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime_seconds = (datetime.datetime.now() - boot_time).total_seconds()
        return json.dumps({
            "status": "success",
            "timestamp": datetime.datetime.now().isoformat(),
            "system": {
                "platform": platform.system(),
                "hostname": platform.node(),
                "uptime_hours": round(uptime_seconds / 3600, 2),
            },
            "cpu": {
                "usage_percent": round(cpu_percent, 1),
                "logical_cores": psutil.cpu_count(logical=True),
                "physical_cores": psutil.cpu_count(logical=False),
            },
            "memory": {
                "total_gb": round(memory.total / (1024 ** 3), 2),
                "available_gb": round(memory.available / (1024 ** 3), 2),
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "usage_percent": round(memory.percent, 1),
            },
            "disk": {
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
                "usage_percent": round(disk.percent, 1),
            },
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, indent=2)


TOOL_MAP = {
    "gettime": gettime,
    "get_system_metrics": get_system_metrics,
}

llm_model = LiteLlm(
    model="ollama_chat/qwen2.5:latest",
    api_base="http://localhost:11434",
    temperature=0.1,
    max_tokens=512,
)

root_agent = Agent(
    name="assistant",
    model=llm_model,
    description="A helpful assistant with time and system monitoring tools.",
    instruction="""You are a helpful AI assistant. You have access to two tools:

1. gettime - call this for any question about the current time, date, or day of the week.
2. get_system_metrics - call this for any question about CPU, memory, disk, or system performance.

When a tool is needed, call it and then reply naturally using the data it returns.
Keep replies short and friendly.""",
    tools=[gettime, get_system_metrics],
)


def _parse_inline_tool_call(text: str):
    """
    gemma3:4b sometimes emits tool calls as raw JSON instead of a proper
    function_call part, e.g.:
        {"name": "gettime"}
        {"name": "get_system_metrics", "arguments": {}}

    Returns (func_name, func_args) or (None, None).
    """
    text = text.strip()
    if not text.startswith("{"):
        return None, None
    try:
        obj = json.loads(text)
        name = obj.get("name") or obj.get("function", {}).get("name")
        args = obj.get("arguments") or obj.get("function", {}).get("arguments") or {}
        if name and name in TOOL_MAP:
            return name, args
    except (json.JSONDecodeError, AttributeError):
        pass
    return None, None


async def process_agent_turn(runner, session_id: str, user_id: str, user_msg):
    """
    Run one conversational turn with robust tool-call handling.

    gemma3:4b often emits tool calls as plain JSON text rather than proper
    function_call parts. This function handles both cases:
      1. Native function_call parts (ADK-detected)
      2. Inline JSON tool calls emitted as plain text

    Returns (response_text, tools_used_list).
    """
    tools_used = []
    MAX_TOOL_ROUNDS = 5
    current_msg = user_msg

    for _ in range(MAX_TOOL_ROUNDS):
        text_chunks = []
        native_tool_calls = []

        async for event in runner.run_async(
            session_id=session_id,
            user_id=user_id,
            new_message=current_msg,
        ):
            if not hasattr(event, "content") or not event.content:
                continue
            if not hasattr(event.content, "parts"):
                continue

            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    fname = getattr(fc, "name", None)
                    fargs = getattr(fc, "args", {}) or {}
                    if fname and fname in TOOL_MAP:
                        native_tool_calls.append((fname, fargs))

                if hasattr(part, "text") and part.text:
                    text_chunks.append(part.text)

        full_text = "".join(text_chunks).strip()

        # Native function calls take priority
        if native_tool_calls:
            result_parts = []
            for fname, fargs in native_tool_calls:
                if fname not in tools_used:
                    tools_used.append(fname)
                tool_result = TOOL_MAP[fname](**fargs)
                result_parts.append(f"{fname} returned:\n{tool_result}")

            current_msg = types.Content(
                role="user",
                parts=[types.Part(text=(
                    "Tool results:\n" + "\n\n".join(result_parts) +
                    "\n\nNow give a short, natural language answer to the user."
                ))],
            )
            continue

        # Inline JSON tool call
        if full_text:
            fname, fargs = _parse_inline_tool_call(full_text)
            if fname:
                if fname not in tools_used:
                    tools_used.append(fname)
                tool_result = TOOL_MAP[fname](**(fargs or {}))
                current_msg = types.Content(
                    role="user",
                    parts=[types.Part(text=(
                        f"{fname} returned:\n{tool_result}\n\n"
                        "Now give a short, natural language answer to the user."
                    ))],
                )
                continue

        # Real text answer
        if full_text:
            return full_text, tools_used

        break

    return "Sorry, I could not produce an answer.", tools_used


async def run_single_query(user_input: str) -> str:
    session_service = InMemorySessionService()
    app_name = "assistant_app"
    session_id = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    user_id = "user"

    await session_service.create_session(
        app_name=app_name, session_id=session_id, user_id=user_id
    )
    runner = Runner(app_name=app_name, agent=root_agent, session_service=session_service)
    user_msg = types.Content(role="user", parts=[types.Part(text=user_input)])

    response_text, tools_used = await process_agent_turn(runner, session_id, user_id, user_msg)

    write_log(
        tool_used=tools_used[0] if tools_used else "none",
        user_input=user_input,
        response=response_text,
    )
    return response_text


async def interactive_mode():
    print("Agent initialized")
    print(f"Model : {llm_model.model}")
    print(f"Tools : {list(TOOL_MAP.keys())}")
    print(f"Logs  : {LOG_FILE.absolute()}")
    print("-" * 60)
    print("Type 'exit' or 'quit' to end the session.")
    print("-" * 60)

    session_service = InMemorySessionService()
    app_name = "assistant_app"
    session_id = "interactive_session"
    user_id = "user"

    await session_service.create_session(
        app_name=app_name, session_id=session_id, user_id=user_id
    )
    runner = Runner(app_name=app_name, agent=root_agent, session_service=session_service)

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "bye", "goodbye"):
                print("Goodbye!")
                break

            user_msg = types.Content(role="user", parts=[types.Part(text=user_input)])
            response_text, tools_used = await process_agent_turn(
                runner, session_id, user_id, user_msg
            )

            print(f"\nAssistant: {response_text}")
            if tools_used:
                print(f"[tools used: {', '.join(tools_used)}]")

            write_log(
                tool_used=tools_used[0] if tools_used else "none",
                user_input=user_input,
                response=response_text,
            )

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


async def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print("Usage:")
            print("  python main.py                # interactive mode")
            print("  python main.py <prompt>       # single query")
            return
        user_prompt = " ".join(sys.argv[1:])
        response = await run_single_query(user_prompt)
        print(f"Assistant: {response}")
    else:
        await interactive_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated.")
