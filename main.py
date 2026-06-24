from fastapi import FastAPI
import sys
import subprocess
import traceback

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
        "debug": "/debug"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug")
def debug():
    result = {
        "status": "ok",
        "python": sys.executable,
        "python_version": sys.version
    }

    pip_show = subprocess.run(
        [sys.executable, "-m", "pip", "show", "tooluniverse"],
        capture_output=True,
        text=True
    )

    result["pip_show_tooluniverse_stdout"] = pip_show.stdout
    result["pip_show_tooluniverse_stderr"] = pip_show.stderr
    result["pip_show_tooluniverse_returncode"] = pip_show.returncode

    try:
        import tooluniverse

        result["tooluniverse_imported"] = True
        result["tooluniverse_module_file"] = getattr(tooluniverse, "__file__", None)

        try:
            from tooluniverse import ToolUniverse

            result["ToolUniverse_class_imported"] = True

            tu = ToolUniverse()
            result["ToolUniverse_instance_created"] = True

            result["ToolUniverse_methods_sample"] = [
                m for m in dir(tu)
                if "tool" in m.lower()
                or "run" in m.lower()
                or "execute" in m.lower()
                or "load" in m.lower()
                or "call" in m.lower()
            ][:100]

        except Exception as e:
            result["ToolUniverse_class_imported"] = False
            result["ToolUniverse_error"] = str(e)
            result["ToolUniverse_traceback"] = traceback.format_exc()

    except Exception as e:
        result["tooluniverse_imported"] = False
        result["import_error"] = str(e)
        result["import_traceback"] = traceback.format_exc()

    return result
