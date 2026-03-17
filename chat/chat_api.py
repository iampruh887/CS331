# chat_api.py  (at the project root, next to auth/ and model/)
import json
import subprocess
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from model.main import run_single_query

app = FastAPI(title="Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

class ScriptInfo(BaseModel):
    name: str
    description: str
    path: str

class ScriptOutput(BaseModel):
    script_name: str
    status: str
    output: str
    error: str = None

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    reply = await run_single_query(req.message)
    return ChatResponse(reply=reply)

@app.get("/scripts")
async def list_scripts():
    """List all approved scripts"""
    approved_dir = Path("scripts_registry/approved")
    scripts = []
    
    if approved_dir.exists():
        for script_file in approved_dir.glob("*.py"):
            scripts.append({
                "name": script_file.stem,
                "description": extract_script_description(script_file),
                "path": str(script_file)
            })
    
    return {"scripts": scripts}

@app.post("/scripts/{script_name}/run")
async def run_script(script_name: str):
    """Execute an approved script"""
    script_path = Path("scripts_registry/approved") / f"{script_name}.py"
    
    if not script_path.exists():
        return ScriptOutput(
            script_name=script_name,
            status="error",
            output="",
            error=f"Script not found: {script_name}"
        )
    
    try:
        result = subprocess.run(
            ["python", str(script_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return ScriptOutput(
            script_name=script_name,
            status="success" if result.returncode == 0 else "error",
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else None
        )
    except subprocess.TimeoutExpired:
        return ScriptOutput(
            script_name=script_name,
            status="error",
            output="",
            error="Script execution timed out"
        )
    except Exception as e:
        return ScriptOutput(
            script_name=script_name,
            status="error",
            output="",
            error=str(e)
        )

def extract_script_description(script_path: Path) -> str:
    """Extract description from script metadata"""
    try:
        with open(script_path, 'r') as f:
            content = f.read()
            if 'NEXUS_SCRIPT_METADATA' in content:
                start = content.find('{')
                end = content.find('}', start) + 1
                metadata_str = content[start:end]
                metadata = eval(metadata_str)
                return metadata.get('description', 'No description available')
    except:
        pass
    return "No description available"