from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.parse import quote

from errors import ToolError
from settings import FORMAT_SUFFIXES, Options, ensure_inside_workspace


MIME_TYPES = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}


def save_image(image_bytes: bytes, options: Options) -> tuple[dict[str, Any], list[str]]:
    actual_format = detect_format(image_bytes)
    warnings: list[str] = []
    output_path = options.output_path
    if actual_format != options.output_format:
        output_path = output_path.with_suffix(FORMAT_SUFFIXES[actual_format])
        ensure_inside_workspace(output_path, options.workspace_root)
        warnings.append(
            f"本机服务返回 {actual_format}，与请求的 {options.output_format} 不同；已按实际格式保存。"
        )
    if output_path.exists() and not options.overwrite:
        raise ToolError("OUTPUT_EXISTS", "输出文件已存在；请更换路径或设置 overwrite=true。", {"output_path": str(output_path)})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(output_path, image_bytes)
    relative_path = output_path.relative_to(options.workspace_root).as_posix()
    metadata = {
        "output_path": relative_path,
        "absolute_output_path": str(output_path),
        "output_format": actual_format,
        "requested_output_format": options.output_format,
        "mime_type": MIME_TYPES[actual_format],
        "size_bytes": len(image_bytes),
        "sha256": hashlib.sha256(image_bytes).hexdigest(),
        "size": options.size,
        "quality": options.quality,
        "background": options.background,
    }
    return metadata, warnings


def build_resource(metadata: dict[str, Any]) -> dict[str, Any]:
    relative_path = str(metadata["output_path"])
    return {
        "type": "resource_link",
        "uri": f"tiance-project:///{quote(relative_path, safe='/')}",
        "name": Path(relative_path).name,
        "mimeType": metadata["mime_type"],
        "size": metadata["size_bytes"],
        "annotations": {
            "audience": ["assistant"],
            "priority": 1.0,
        },
    }


def detect_format(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    raise ToolError("UNSUPPORTED_IMAGE_DATA", "本机服务返回的数据不是 PNG、JPEG 或 WebP 图片。")


def atomic_write(path: Path, data: bytes) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            temporary_path = Path(stream.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink(missing_ok=True)
