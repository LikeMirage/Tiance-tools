from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
from typing import Any

from errors import ToolError


BASE_URL = "http://127.0.0.1:8317/v1"
MODEL = "gpt-image-2"
DEFAULT_OUTPUT_DIR = "generated/images"
OUTPUT_FORMATS = {"png", "jpeg", "webp"}
QUALITY_VALUES = {"auto", "low", "medium", "high"}
BACKGROUND_VALUES = {"auto", "opaque"}
SIZE_PATTERN = re.compile(r"^(\d+)x(\d+)$")
FORMAT_SUFFIXES = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}


@dataclass(frozen=True)
class Options:
    prompt: str
    output_path: Path
    overwrite: bool
    size: str
    quality: str
    background: str
    output_format: str
    output_compression: int | None
    timeout_seconds: int
    workspace_root: Path


def parse_options(payload: dict[str, Any]) -> Options:
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise ToolError("INVALID_ARGUMENT", "prompt 必须是非空字符串。")
    if len(prompt) > 32000:
        raise ToolError("INVALID_ARGUMENT", "prompt 不能超过 32000 个字符。")

    output_format = str(payload.get("output_format") or "png").strip().lower()
    if output_format not in OUTPUT_FORMATS:
        raise ToolError("INVALID_ARGUMENT", "output_format 只支持 png、jpeg、webp。")
    quality = str(payload.get("quality") or "auto").strip().lower()
    if quality not in QUALITY_VALUES:
        raise ToolError("INVALID_ARGUMENT", "quality 只支持 auto、low、medium、high。")
    background = str(payload.get("background") or "auto").strip().lower()
    if background not in BACKGROUND_VALUES:
        raise ToolError("INVALID_ARGUMENT", "background 只支持 auto、opaque。")
    size = validate_size(str(payload.get("size") or "auto").strip().lower())

    compression_value = payload.get("output_compression")
    output_compression = None
    if compression_value is not None:
        output_compression = read_integer(compression_value, "output_compression", 0, 100)
        if output_format == "png":
            raise ToolError("INVALID_ARGUMENT", "output_compression 只适用于 jpeg 或 webp。")

    root = workspace_root()
    output_path = resolve_output_path(payload.get("output_path"), root, output_format)
    overwrite = bool(payload.get("overwrite", False))
    if output_path.exists() and not overwrite:
        raise ToolError("OUTPUT_EXISTS", "输出文件已存在；请更换路径或设置 overwrite=true。", {"output_path": str(output_path)})

    return Options(
        prompt=prompt,
        output_path=output_path,
        overwrite=overwrite,
        size=size,
        quality=quality,
        background=background,
        output_format=output_format,
        output_compression=output_compression,
        timeout_seconds=read_integer(payload.get("timeout_seconds", 600), "timeout_seconds", 30, 600),
        workspace_root=root,
    )


def workspace_root() -> Path:
    raw = os.environ.get("TIANCE_WORKSPACE_ROOT") or os.environ.get("WORKSPACE_ROOT") or os.getcwd()
    return Path(raw).expanduser().resolve(strict=False)


def resolve_output_path(value: Any, root: Path, output_format: str) -> Path:
    raw = str(value or "").strip()
    if raw:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        candidate = root / DEFAULT_OUTPUT_DIR / f"gpt_image_{stamp}{FORMAT_SUFFIXES[output_format]}"
    resolved = candidate.resolve(strict=False)
    ensure_inside_workspace(resolved, root)
    expected_suffix = FORMAT_SUFFIXES[output_format]
    if resolved.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        resolved = resolved.with_suffix(expected_suffix)
    elif output_format == "jpeg" and resolved.suffix.lower() in {".jpg", ".jpeg"}:
        pass
    elif resolved.suffix.lower() != expected_suffix:
        resolved = resolved.with_suffix(expected_suffix)
    return resolved


def ensure_inside_workspace(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ToolError(
            "OUTPUT_OUTSIDE_WORKSPACE",
            "输出图片路径必须位于当前项目内。",
            {"output_path": str(path), "workspace_root": str(root)},
        ) from exc


def validate_size(value: str) -> str:
    if value == "auto":
        return value
    match = SIZE_PATTERN.fullmatch(value)
    if not match:
        raise ToolError("INVALID_ARGUMENT", "size 必须是 auto 或 WIDTHxHEIGHT。")
    width, height = int(match.group(1)), int(match.group(2))
    short_edge, long_edge = sorted((width, height))
    pixels = width * height
    if width % 16 or height % 16:
        raise ToolError("INVALID_ARGUMENT", "size 的宽和高必须是 16 的倍数。")
    if long_edge > 3840:
        raise ToolError("INVALID_ARGUMENT", "size 的最长边不能超过 3840。")
    if short_edge <= 0 or long_edge / short_edge > 3:
        raise ToolError("INVALID_ARGUMENT", "size 的长短边比例不能超过 3:1。")
    if not 655360 <= pixels <= 8294400:
        raise ToolError("INVALID_ARGUMENT", "size 总像素必须在 655360 到 8294400 之间。")
    return value


def read_integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise ToolError("INVALID_ARGUMENT", f"{name} 必须是整数。")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ToolError("INVALID_ARGUMENT", f"{name} 必须是整数。") from exc
    if not minimum <= parsed <= maximum:
        raise ToolError("INVALID_ARGUMENT", f"{name} 必须在 {minimum} 到 {maximum} 之间。")
    return parsed
