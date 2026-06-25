from fastapi import FastAPI
import sys
import subprocess

app = FastAPI(
    title="ToolUniverse Proxy",
    description="Debug ToolUniverse Python SDK on Render.",
    version="1.0.0"
)

app.openapi_version = "3.0.3"


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "tooluniverse-proxy",
        "health": "/health",
        "safe_debug": "/safe_debug"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/safe_debug")
def safe_debug():
    result = {
        "status": "ok",
        "python": sys.executable,
        "python_version": sys.version.split()[0]
    }

    pip_show = subprocess.run(
        [sys.executable, "-m", "pip", "show", "tooluniverse"],
        capture_output=True,
        text=True
    )

    result["tooluniverse_installed"] = pip_show.returncode == 0

    try:
        import tooluniverse
        result["tooluniverse_imported"] = True

        try:
            from tooluniverse import ToolUniverse
            result["ToolUniverse_class_imported"] = True

            tu = ToolUniverse()
            result["ToolUniverse_instance_created"] = True

            result["methods_sample"] = [
                m for m in dir(tu)
                if "tool" in m.lower()
                or "run" in m.lower()
                or "execute" in m.lower()
                or "load" in m.lower()
                or "call" in m.lower()
            ][:50]

        except Exception as e:
            result["ToolUniverse_class_imported"] = False
            result["ToolUniverse_error"] = str(e)

    except Exception as e:
        result["tooluniverse_imported"] = False
        result["import_error"] = str(e)

    return result
