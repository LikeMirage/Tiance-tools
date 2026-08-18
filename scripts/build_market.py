from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

from tool_package import load_and_validate_tool_package, require


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPOSITORY_ROOT / "tools"
DIST_ROOT = REPOSITORY_ROOT / "dist"


def main() -> None:
    tool_roots = sorted(path for path in TOOLS_ROOT.iterdir() if path.is_dir())
    require(bool(tool_roots), "tools 目录中没有可发布工具。")
    _reset_dist()
    entries = [_build_tool(tool_root) for tool_root in tool_roots]
    _write_json(
        DIST_ROOT / "index.json",
        {
            "schemaVersion": 1,
            "kind": "tiance-tool-market",
            "name": "Tiance Tools",
            "updatedAt": datetime.now(UTC).isoformat(),
            "tools": entries,
        },
    )
    print(f"市场构建完成：{len(entries)} 个工具。")


def _build_tool(tool_root: Path) -> dict[str, object]:
    tool, manifest = load_and_validate_tool_package(tool_root)
    tool_id = tool_root.name
    version = str(manifest["version"])
    package_name = f"{tool_id}-{version}.zip"
    package_target = DIST_ROOT / "packages" / package_name
    package_target.parent.mkdir(parents=True, exist_ok=True)
    _write_package(tool_root, package_target)

    runtime = tool["runtime"]
    return {
        "id": tool_id,
        "version": version,
        "author": str(manifest["author"]["name"]),
        "license": str(manifest["license"]),
        "callName": str(tool["name"]),
        "displayName": str(tool["registration_name"]),
        "summary": str(tool["description"]),
        "runtime": str(runtime["type"]),
        "packageUrl": f"packages/{package_name}",
        "sha256": _sha256(package_target),
        "size": package_target.stat().st_size,
        "compatibility": manifest["compatibility"],
    }


def _write_package(tool_root: Path, target: Path) -> None:
    with ZipFile(target, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in tool_root.rglob("*") if item.is_file()):
            relative = path.relative_to(tool_root)
            archive.write(
                path,
                (PurePosixPath(tool_root.name) / PurePosixPath(relative.as_posix())).as_posix(),
            )


def _reset_dist() -> None:
    resolved = DIST_ROOT.resolve()
    require(resolved.parent == REPOSITORY_ROOT.resolve(), "dist 目录越界。")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    main()

