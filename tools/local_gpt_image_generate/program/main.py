from __future__ import annotations

import sys
from typing import Any

from tiance_runtime import run_tool

from credentials import CREDENTIAL_TARGET, ENVIRONMENT_VARIABLE, load_api_key
from errors import ToolError, failure
from image_output import build_resource, save_image
from image_api_client import generate_image
from settings import BASE_URL, MODEL, parse_options


def run(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        options = parse_options(payload)
        api_key = load_api_key()
        if not api_key:
            raise ToolError(
                "API_KEY_MISSING",
                "缺少本机图片服务凭据。",
                {
                    "credential_target": CREDENTIAL_TARGET,
                    "environment_variable": ENVIRONMENT_VARIABLE,
                },
            )
        image_bytes, response_metadata = generate_image(options, api_key)
        file_metadata, warnings = save_image(image_bytes, options)
        data = {
            **file_metadata,
            **response_metadata,
            "provider": "OpenAI-compatible Image API",
            "base_url": BASE_URL,
            "model": MODEL,
        }
        return {
            "ok": True,
            "summary": f"图片生成完成：{file_metadata['output_path']}。",
            "content": [build_resource(file_metadata)],
            "structuredContent": data,
            "data": data,
            "warnings": warnings,
        }
    except ToolError as exc:
        return failure(exc.code, exc.message, exc.details)
    except Exception as exc:
        return failure("IMAGE_GENERATION_FAILED", str(exc)[:500] or type(exc).__name__)


if __name__ == "__main__":
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    run_tool(run)
