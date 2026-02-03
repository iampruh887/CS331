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

