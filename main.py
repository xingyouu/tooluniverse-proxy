from fastapi import FastAPI, Request
from pydantic import BaseModel
import subprocess
import json
import os

app = FastAPI()


class FindToolsRequest(BaseModel):
    query: str
    limit: int = 5


class RunToolRequest(BaseModel):
    tool_name: str
    arguments: dict = {}


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
        "routes": ["/health", "/find_tools", "/run_tool"]
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/find_tools")
async def find_tools(request: Request):
    if not check_token(request):
        return {"error": "unauthorized"}

    body = await request.json()
    query = body.get("query") or body.get("input") or body.get("text") or str(body)
    limit = body.get("limit", 5)

    cmd = [
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
            "query": query,
            "limit": limit,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    except Exception as e:
        return {
            "query": query,
            "error": str(e)
        }


@app.post("/run_tool")
async def run_tool(request: Request):
    if not check_token(request):
        return {"error": "unauthorized"}

    body = await request.json()

    tool_name = body.get("tool_name") or body.get("name")
    arguments = body.get("arguments") or body.get("args") or {}

    if not tool_name:
        return {
            "error": "missing tool_name",
            "example": {
                "tool_name": "Tool_Name_Here",
                "arguments": {}
            }
        }

    args_json = json.dumps(arguments, ensure_ascii=False)

    cmd = [
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
            "tool_name": tool_name,
            "arguments": arguments,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    except Exception as e:
        return {
            "tool_name": tool_name,
            "arguments": arguments,
            "error": str(e)
        }