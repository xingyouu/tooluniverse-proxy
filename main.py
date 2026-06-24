from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List
import json
import traceback

try:
    from tooluniverse import ToolUniverse
except Exception as e:
    ToolUniverse = None
    IMPORT_ERROR = str(e)
else:
    IMPORT_ERROR = None


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
        description="Exact ToolUniverse tool name returned by toolfind.",
        examples=["PubMed_search_articles"]
    )
    arguments: Any = Field(
        default_factory=dict,
        description="JSON arguments required by the selected ToolUniverse tool.",
        examples=[{"query": "EGFR cancer", "max_results": 3}]
    )


class ToolResponse(BaseModel):
    status: str
    query: Optional[str] = None
    limit: Optional[int] = None
    tool_name: Optional[str] = None
    arguments: Optional[Any] = None
    result: Optional[Any] = None
    tools: Optional[List[str]] = None
    error: Optional[str] = None
    traceback: Optional[str] = None


_TU = None


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


def get_tu():
    global _TU

    if ToolUniverse is None:
        raise RuntimeError(f"Failed to import tooluniverse: {IMPORT_ERROR}")

    if _TU is None:
        tu = ToolUniverse()

        # 不要先加载全部工具，Render 免费环境可能很慢。
        # 先优先加载文献相关工具，够 showcase 用。
        try:
            tu.load_tools(
                include_tools=[
                    "PubMed_search_articles",
                    "PubMed_get_article_details",
                    "EuropePMC_search_articles",
                    "EuropePMC_get_article_details"
                ]
            )
        except TypeError:
            # 兼容旧版本参数差异
            tu.load_tools()

        _TU = tu

    return _TU


def safe_tool_names(tu) -> List[str]:
    try:
        return tu.list_built_in_tools(mode="list_name")
    except Exception:
        try:
            return list(tu.all_tools.keys())
        except Exception:
            return []


def run_find_tools(query: str, limit: int = 5):
    try:
        tu = get_tu()
        all_names = safe_tool_names(tu)

        query_lower = query.lower()

        # 简单规则匹配，避免依赖 ToolUniverse 内置 embedding finder。
        # 你的 showcase 先稳，不要把自己献祭给“智能工具发现”。
        scored = []

        for name in all_names:
            name_lower = name.lower()
            score = 0

            if "pubmed" in name_lower:
                score += 5
            if "europepmc" in name_lower:
                score += 4
            if "search" in name_lower:
                score += 3
            if "article" in name_lower or "literature" in name_lower:
                score += 2
            if "drug" in query_lower and ("drug" in name_lower or "chembl" in name_lower):
                score += 3
            if "target" in query_lower and ("target" in name_lower or "opentarget" in name_lower):
                score += 3
            if "egfr" in query_lower and "pubmed" in name_lower:
                score += 2

            if score > 0:
                scored.append((score, name))

        scored.sort(reverse=True)

        tools = [name for _, name in scored[:limit]]

        if not tools:
            tools = all_names[:limit]

        return {
            "status": "ok",
            "query": query,
            "limit": limit,
            "tools": tools,
            "result": {
                "message": "Candidate ToolUniverse tools found.",
                "recommended_next_step": "Use toolrun with one exact tool_name and JSON arguments."
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "query": query,
            "limit": limit,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def run_tooluniverse_tool(tool_name: str, arguments: Any):
    clean_arguments = normalize_arguments(arguments)

    try:
        tu = get_tu()

        # ToolUniverse 常见调用方式之一：tu.run({...})
        # 如果当前版本不支持，会进入 except，再尝试其他方式。
        try:
            result = tu.run({
                "name": tool_name,
                "arguments": clean_arguments
            })
        except Exception:
            try:
                result = tu.run({
                    "tool_name": tool_name,
                    "arguments": clean_arguments
                })
            except Exception:
                # 有些版本可能支持 execute_tool / run_tool，做兜底。
                if hasattr(tu, "execute_tool"):
                    result = tu.execute_tool(tool_name, clean_arguments)
                elif hasattr(tu, "run_tool"):
                    result = tu.run_tool(tool_name, clean_arguments)
                else:
                    raise

        return {
            "status": "ok",
            "tool_name": tool_name,
            "arguments": clean_arguments,
            "result": result
        }

    except Exception as e:
        return {
            "status": "error",
            "tool_name": tool_name,
            "arguments": clean_arguments,
            "error": str(e),
            "traceback": traceback.format_exc()
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
    try:
        tu = get_tu()
        names = safe_tool_names(tu)
        return {
            "status": "ok",
            "tooluniverse_imported": ToolUniverse is not None,
            "import_error": IMPORT_ERROR,
            "loaded_tool_count": len(names),
            "first_tools": names[:10],
            "has_run": hasattr(tu, "run"),
            "has_execute_tool": hasattr(tu, "execute_tool"),
            "has_run_tool": hasattr(tu, "run_tool")
        }
    except Exception as e:
        return {
            "status": "error",
            "tooluniverse_imported": ToolUniverse is not None,
            "import_error": IMPORT_ERROR,
            "error": str(e),
            "traceback": traceback.format_exc()
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
