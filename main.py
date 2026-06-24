from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import subprocess
import json
import os

app = FastAPI(
    title="ToolUniverse Proxy",
    description="OpenAPI service for ToolUniverse scientific tool discovery and execution.",
    version="1.0.0"
)

# 有些平台对 OpenAPI 3.1 支持不好，强制改成 3.0.3 更稳
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
        examples=["Tool_Name_Here"]
    )
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON arguments required by the selected ToolUniverse tool.",
        examples=[{}]
    )


class ToolResponse(BaseModel):
    status: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    returncode: Optional[int] = None
    query: Optional[str] = None
    limit: Optional[int] = None
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def check_token(request: Request):
    expected_token = os.getenv("PLUGIN_TOKEN")
    if not expected_token:
        return True

    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {expected_token}"


def run_find_tools(query: str, limit: int = 5):
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

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120
    )

    return {
        "status": "ok" if result.returncode == 0 else "error",
        "query": query,
        "limit": limit,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }


def run_tooluniverse_tool(tool_name: str, arguments: dict):
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

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=180
    )

    return {
        "status": "ok" if result.returncode == 0 else "error",
        "tool_name": tool_name,
        "arguments": arguments,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }


@app.get("/", include_in_schema=False)
def root():
    return {
        "status": "ok",
        "service": "tooluniverse-proxy",
        "openapi": "/openapi.json",
        "docs": "/docs",
        "tools": ["/find_tools", "/run_tool"]
    }


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


@app.get("/find_tools", include_in_schema=False)
def find_tools_get(
    query: str = Query("EGFR drug target information"),
    limit: int = Query(5)
):
    try:
        return run_find_tools(query, limit)
    except Exception as e:
        return {
            "status": "error",
            "query": query,
            "error": str(e)
        }


@app.post(
    "/find_tools",
    operation_id="toolfind",
    summary="Find suitable ToolUniverse tools",
    description="Search ToolUniverse for suitable scientific tools based on a research task description.",
    response_model=ToolResponse
)
def find_tools_post(payload: FindToolsRequest):
    try:
        return run_find_tools(payload.query, payload.limit)
    except Exception as e:
        return {
            "status": "error",
            "query": payload.query,
            "error": str(e)
        }


@app.get("/run_tool", include_in_schema=False)
def run_tool_get():
    return {
        "status": "ok",
        "message": "run_tool endpoint is available. Use POST with JSON body.",
        "example_body": {
            "tool_name": "Tool_Name_Here",
            "arguments": {}
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
    try:
        return run_tooluniverse_tool(payload.tool_name, payload.arguments)
    except Exception as e:
        return {
            "status": "error",
            "tool_name": payload.tool_name,
            "arguments": payload.arguments,
            "error": str(e)
        }
