from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import subprocess
import json
import os
import shutil

app = FastAPI(
    title="ToolUniverse Proxy",
    description="OpenAPI service for ToolUniverse scientific tool discovery and execution.",
    version="1.0.0"
)

app.openapi_version = "3.0.3"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FindToolsRequest(BaseModel):
    query: str = Field(
        ...,
        description="Scientific task or query used to search suitable ToolUniverse tools.",
        examples=["EGFR drug target information"]
    )
    limit: int = Field(
        5,
        description="Maximum number of tools to return.",
        examples=[5]
    )


class RunToolRequest(BaseModel):
    tool_name: str = Field(
        ...,
        description="Exact ToolUniverse tool name returned by find_tools.",
        examples=["PubMed_search_articles"]
    )
    arguments: Any = Field(
        default_factory=dict,
        description="JSON arguments required by the selected ToolUniverse tool.",
        examples=[{"query": "EGFR cancer", "max_results": 3}]
    )


class ToolResponse(BaseModel):
    status: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    returncode: Optional[int] = None
    query: Optional[str] = None
    limit: Optional[int] = None
    tool_name: Optional[str] = None
    arguments: Optional[Any] = None
    error: Optional[str] = None


def normalize_arguments(arguments: Any) -> Dict[str, Any]:
    if arguments is None:
        return {}

    if isinstance(arguments, dict):
        return arguments

    if isinstance(arguments, str):
        if arguments.strip() == "":
            return {}
        try:
            parsed = json.loads(arguments)
            if isinstance(parsed, dict):
                return parsed
            return {}
        except Exception:
            return {}

    return {}


def get_tu_command():
    tu_path = shutil.which("tu")

    if tu_path:
        return tu_path

    return None


def run_find_tools(query: str, limit: int = 5):
    tu_cmd = get_tu_command()

    if not tu_cmd:
        return {
            "status": "error",
            "query": query,
            "limit": limit,
            "stdout": None,
            "stderr": None,
            "returncode": None,
            "error": "ToolUniverse CLI command 'tu' was not found in Render environment. Check requirements.txt and deployment logs."
        }

    cmd = [
        tu_cmd,
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
            timeout=180
        )

        return {
            "status": "ok" if result.returncode == 0 else "error",
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
            "limit": limit,
            "stdout": None,
            "stderr": None,
            "returncode": None,
            "error": str(e)
        }


def run_tooluniverse_tool(tool_name: str, arguments: Any):
    tu_cmd = get_tu_command()
    clean_arguments = normalize_arguments(arguments)

    if not tu_cmd:
        return {
            "status": "error",
            "tool_name": tool_name,
            "arguments": clean_arguments,
            "stdout": None,
            "stderr": None,
            "returncode": None,
            "error": "ToolUniverse CLI command 'tu' was not found in Render environment. Check requirements.txt and deployment logs."
        }

    args_json = json.dumps(clean_arguments, ensure_ascii=False)

    cmd = [
        tu_cmd,
        "run",
        tool_name,
        args_json
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=240
        )

        return {
            "status": "ok" if result.returncode == 0 else "error",
            "tool_name": tool_name,
            "arguments": clean_arguments,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    except Exception as e:
        return {
            "status": "error",
            "tool_name": tool_name,
            "arguments": clean_arguments,
            "stdout": None,
            "stderr": None,
            "returncode": None,
            "error": str(e)
        }


@app.get("/", include_in_schema=False)
def root():
    return {
        "status": "ok",
        "service": "tooluniverse-proxy",
        "openapi": "/openapi.json",
        "docs": "/docs",
        "tools": ["/find_tools", "/run_tool"],
        "debug": "/debug"
    }


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


@app.get("/debug", include_in_schema=False)
def debug():
    return {
        "tu_path": shutil.which("tu"),
        "uvx_path": shutil.which("uvx"),
        "PATH": os.getenv("PATH")
    }


@app.get("/find_tools", include_in_schema=False)
def find_tools_get(
    query: str = Query("EGFR drug target information"),
    limit: int = Query(5)
):
    return run_find_tools(query, limit)


@app.post(
    "/find_tools",
    operation_id="toolfind",
    summary="Find suitable ToolUniverse tools",
    description="Search ToolUniverse for suitable scientific tools based on a research task description.",
    response_model=ToolResponse
)
def find_tools_post(payload: FindToolsRequest):
    return run_find_tools(payload.query, payload.limit)


@app.get("/run_tool", include_in_schema=False)
def run_tool_get():
    return {
        "status": "ok",
        "message": "run_tool endpoint is available. Use POST with JSON body.",
        "example_body": {
            "tool_name": "PubMed_search_articles",
            "arguments": {
                "query": "EGFR cancer",
                "max_results": 3
            }
        }
    }


@app.post(
    "/run_tool",
    operation_id="toolrun",
    summary="Run a ToolUniverse tool",
    description="Execute a specific ToolUniverse tool with JSON arguments.",
    response_model=ToolResponse
)
def run_tool_post(payload: RunToolRequest):
    return run_tooluniverse_tool(payload.tool_name, payload.arguments)
