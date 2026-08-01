from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


TOOL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
CALL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$"
)
REQUIRED_FILES = {
    "manifest.json",
    ".tool/tool.json",
    ".tool/input.schema.json",
    ".tool/output.schema.json",
    ".tool/examples.json",
}
FORBIDDEN_PARTS = {".tiance", "dependencies", "__pycache__", ".git"}
MAX_FILES = 2_000
MAX_SINGLE_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024


class MarketBuildError(RuntimeError):
    pass


def load_and_validate_tool_package(
    tool_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    tool_id = tool_root.name
    require(TOOL_ID_PATTERN.fullmatch(tool_id) is not None, f"非法工具目录名：{tool_id}")
    _validate_package_tree(tool_root)
    manifest = _read_object(tool_root / "manifest.json")
    tool = _read_object(tool_root / ".tool" / "tool.json")
    _validate_manifest(tool_id, manifest)
    _validate_tool(tool_id, tool, tool_root)
    return tool, manifest


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MarketBuildError(message)


def _validate_package_tree(tool_root: Path) -> None:
    files = [path for path in tool_root.rglob("*") if path.is_file()]
    actual = {path.relative_to(tool_root).as_posix() for path in files}
    missing = REQUIRED_FILES - actual
    require(not missing, f"{tool_root.name} 缺少文件：{', '.join(sorted(missing))}")
    require(0 < len(files) <= MAX_FILES, f"{tool_root.name} 文件数量超出限制。")

    total_size = 0
    for path in tool_root.rglob("*"):
        require(not path.is_symlink(), f"{tool_root.name} 不允许符号链接：{path.name}")
        relative = path.relative_to(tool_root)
        lowered_parts = {part.casefold() for part in relative.parts}
        require(not (lowered_parts & FORBIDDEN_PARTS), f"{tool_root.name} 包含本地状态：{relative}")
        if not path.is_file():
            continue
        require(path.suffix.casefold() != ".pyc", f"{tool_root.name} 包含 Python 缓存：{relative}")
        size = path.stat().st_size
        require(size <= MAX_SINGLE_FILE_BYTES, f"{tool_root.name} 文件过大：{relative}")
        total_size += size
    require(total_size <= MAX_TOTAL_BYTES, f"{tool_root.name} 解压大小超出限制。")


def _validate_manifest(tool_id: str, manifest: dict[str, Any]) -> None:
    expected_keys = {
        "schemaVersion", "kind", "id", "version", "author", "license", "compatibility"
    }
    require(set(manifest) == expected_keys, f"{tool_id} 的 manifest 字段不完整或存在多余字段。")
    require(manifest["schemaVersion"] == 1, f"{tool_id} 只支持 manifest schemaVersion 1。")
    require(manifest["kind"] == "tiance-tool-package", f"{tool_id} 的 kind 非法。")
    require(manifest["id"] == tool_id, f"{tool_id} 的 manifest id 与目录名不一致。")
    require(SEMVER_PATTERN.fullmatch(str(manifest["version"])) is not None, f"{tool_id} 的版本号非法。")
    author = manifest["author"]
    require(isinstance(author, dict) and set(author) == {"name"}, f"{tool_id} 的 author 非法。")
    require(isinstance(author["name"], str) and author["name"].strip(), f"{tool_id} 缺少作者。")
    require(isinstance(manifest["license"], str) and manifest["license"].strip(), f"{tool_id} 缺少许可证。")
    compatibility = manifest["compatibility"]
    require(
        isinstance(compatibility, dict)
        and set(compatibility) == {"minTianceVersion", "platforms"},
        f"{tool_id} 的兼容信息非法。",
    )
    require(
        SEMVER_PATTERN.fullmatch(str(compatibility["minTianceVersion"])) is not None,
        f"{tool_id} 的最低天策版本非法。",
    )
    platforms = compatibility["platforms"]
    require(
        isinstance(platforms, list)
        and bool(platforms)
        and all(isinstance(item, str) and item.strip() for item in platforms),
        f"{tool_id} 的平台列表非法。",
    )


def _validate_tool(tool_id: str, tool: dict[str, Any], tool_root: Path) -> None:
    call_name = tool.get("name")
    require(isinstance(call_name, str) and CALL_NAME_PATTERN.fullmatch(call_name), f"{tool_id} 的调用名称非法。")
    require(isinstance(tool.get("display_name"), str) and tool["display_name"].strip(), f"{tool_id} 缺少展示名称。")
    require(isinstance(tool.get("description"), str) and tool["description"].strip(), f"{tool_id} 缺少用途说明。")
    runtime = tool.get("runtime")
    require(isinstance(runtime, dict), f"{tool_id} 缺少运行定义。")
    runtime_type = runtime.get("type")
    require(isinstance(runtime_type, str) and runtime_type.strip(), f"{tool_id} 缺少运行类型。")
    if runtime_type == "python":
        entry = runtime.get("entry")
        require(isinstance(entry, str) and _is_safe_relative_path(entry), f"{tool_id} 的入口路径非法。")
        require((tool_root / entry).is_file(), f"{tool_id} 的入口文件不存在：{entry}")


def _read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MarketBuildError(f"无法读取 JSON：{path}") from exc
    require(isinstance(payload, dict), f"JSON 顶层必须是对象：{path}")
    return payload


def _is_safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value.replace("\\", "/"))
    return bool(value) and not path.is_absolute() and ".." not in path.parts

