from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def check_token(request: Request):
    expected_token = os.getenv("PLUGIN_TOKEN")
    if not expected_token:
        return True

    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {expected_token}"


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "tooluniverse-proxy",
        "routes": {
            "health": "/health",
            "find_tools": "/find_tools",
            "run_tool": "/run_tool"
        }
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/find_tools")
def find_tools_get():
    return {
        "status": "ok",
        "message": "find_tools endpoint is available. Use POST with JSON body.",
        "method": "POST",
        "example_body": {
            "query": "EGFR drug target information",
            "limit": 5
        }
    }


@app.post("/find_tools")
async def find_tools_post(request: Request):
    if not check_token(request):
        return {"error": "unauthorized"}

    try:
        body = await request.json()
    except Exception:
        body = {}

    query = (
        body.get("query")
        or body.get("input")
        or body.get("text")
        or "EGFR drug target information"
    )

    limit = body.get("limit", 5)

    cmd = [
        "uvx",
        "--from",
        "tooluniverse",
        "tu",
        "find",
        query,
        "--limit",
        str(limit)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        return {
            "status": "ok",
            "query": query,
            "limit": limit,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    except Exception as e:
        return {
            "status": "error",
            "query": query,
            "error": str(e)
        }


@app.get("/run_tool")
def run_tool_get():
    return {
        "status": "ok",
        "message": "run_tool endpoint is available. Use POST with JSON body.",
        "method": "POST",
        "example_body": {
            "tool_name": "Tool_Name_Here",
            "arguments": {}
        }
    }


@app.post("/run_tool")
async def run_tool_post(request: Request):
    if not check_token(request):
        return {"error": "unauthorized"}

    try:
        body = await request.json()
    except Exception:
        body = {}

    tool_name = body.get("tool_name") or body.get("name")
    arguments = body.get("arguments") or body.get("args") or {}

    if not tool_name:
        return {
            "status": "error",
            "error": "missing tool_name",
            "example_body": {
                "tool_name": "Tool_Name_Here",
                "arguments": {}
            }
        }

    args_json = json.dumps(arguments, ensure_ascii=False)

    cmd = [
        "uvx",
        "--from",
        "tooluniverse",
        "tu",
        "run",
        tool_name,
        args_json
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180
        )

        return {
            "status": "ok",
            "tool_name": tool_name,
            "arguments": arguments,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    except Exception as e:
        return {
            "status": "error",
            "tool_name": tool_name,
            "arguments": arguments,
            "error": str(e)
        }
