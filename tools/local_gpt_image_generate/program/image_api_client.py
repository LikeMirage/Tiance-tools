from __future__ import annotations

import base64
import binascii
import http.client
import json
from typing import Any
from urllib.parse import urlparse

from errors import ToolError
from settings import BASE_URL, MODEL, Options


GENERATIONS_ENDPOINT = "/images/generations"
MAX_RESPONSE_BYTES = 128 * 1024 * 1024


def generate_image(options: Options, api_key: str) -> tuple[bytes, dict[str, Any]]:
    response_payload = _post_generation(build_request_payload(options), api_key, options.timeout_seconds)
    image_base64 = extract_image_base64(response_payload)
    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ToolError("INVALID_IMAGE_BASE64", "本机服务返回的图片数据不是有效 Base64。") from exc
    if not image_bytes:
        raise ToolError("EMPTY_IMAGE", "本机服务返回的图片内容为空。")
    metadata = {
        "response_id": response_payload.get("id") or response_payload.get("request_id"),
        "created_at": response_payload.get("created"),
        "usage": response_payload.get("usage") if isinstance(response_payload.get("usage"), dict) else None,
        "model": MODEL,
    }
    return image_bytes, metadata


def build_request_payload(options: Options) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": MODEL,
        "prompt": options.prompt,
        "n": 1,
        "size": options.size,
        "quality": options.quality,
        "background": options.background,
        "output_format": options.output_format,
    }
    if options.output_compression is not None:
        payload["output_compression"] = options.output_compression
    return payload


def extract_image_base64(payload: dict[str, Any]) -> str:
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise ToolError("INVALID_RESPONSE", "本机服务响应缺少 data 图片数组。", response_shape(payload))
    first = data[0]
    if not isinstance(first, dict):
        raise ToolError("INVALID_RESPONSE", "本机服务返回的第一项图片结果不是对象。", response_shape(payload))
    result = first.get("b64_json")
    if isinstance(result, str) and result.strip():
        return result.strip()
    raise ToolError("IMAGE_RESULT_MISSING", "本机服务没有返回 data[0].b64_json 图片结果。", response_shape(payload))


def _post_generation(body_payload: dict[str, Any], api_key: str, timeout_seconds: int) -> dict[str, Any]:
    parsed = urlparse(f"{BASE_URL.rstrip('/')}{GENERATIONS_ENDPOINT}")
    connection = http.client.HTTPConnection(parsed.netloc, timeout=timeout_seconds)
    body = json.dumps(body_payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Tiance-Local-Image-Tool/1.0",
    }
    try:
        connection.request("POST", parsed.path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        status = response.status
    except (OSError, http.client.HTTPException) as exc:
        raise ToolError(
            "LOCAL_SERVICE_UNAVAILABLE",
            "无法连接本机图片服务。",
            {"base_url": BASE_URL, "reason": str(exc)[:300]},
        ) from exc
    finally:
        connection.close()
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ToolError("RESPONSE_TOO_LARGE", "本机服务响应超过 128 MiB 安全上限。")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ToolError("INVALID_JSON", "本机服务返回了无效 JSON。", {"status_code": status}) from exc
    if not isinstance(payload, dict):
        raise ToolError("INVALID_RESPONSE", "本机服务返回的 JSON 根节点不是对象。", {"status_code": status})
    if status >= 400:
        upstream_message = redact_secret(extract_error_message(payload), api_key)
        raise ToolError(
            "LOCAL_SERVICE_HTTP_ERROR",
            f"本机图片服务请求失败，HTTP {status}：{upstream_message}",
            {"status_code": status, "response_id": payload.get("id")},
        )
    return payload


def extract_error_message(payload: dict[str, Any]) -> str:
    error = payload.get("error")
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])[:500]
    if isinstance(error, str) and error.strip():
        return error.strip()[:500]
    if payload.get("message"):
        return str(payload["message"])[:500]
    return "未提供错误说明"


def redact_secret(message: str, secret: str) -> str:
    if not secret:
        return message
    return message.replace(secret, "[REDACTED]")


def response_shape(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    item_keys: list[str] = []
    if isinstance(data, list) and data and isinstance(data[0], dict):
        item_keys = [str(key) for key in data[0].keys() if str(key) != "b64_json"]
    return {
        "response_id": payload.get("id") or payload.get("request_id"),
        "has_data_array": isinstance(data, list),
        "first_item_keys": item_keys[:20],
    }
