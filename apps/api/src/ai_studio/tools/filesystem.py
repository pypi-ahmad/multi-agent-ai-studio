from __future__ import annotations

import shutil
from os import getenv
from pathlib import Path

from fastapi import HTTPException


def _allowed_root() -> Path:
    configured = Path(getenv("AI_STUDIO_ALLOWED_ROOT", "/home/ahmad/AI")).expanduser().resolve()
    if configured.exists():
        return configured
    fallback = Path("/app").resolve()
    if fallback.exists():
        return fallback
    return configured


ALLOWED_ROOT = _allowed_root()


def _resolve_allowed(path: str) -> Path:
    target = Path(path).expanduser().resolve()
    if not str(target).startswith(str(ALLOWED_ROOT)):
        raise HTTPException(status_code=403, detail="Path outside allowed root")
    return target


def read_text(path: str) -> str:
    target = _resolve_allowed(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return target.read_text(encoding="utf-8", errors="ignore")


def write_text(path: str, content: str, overwrite: bool = True) -> None:
    target = _resolve_allowed(path)
    if target.exists() and not overwrite:
        raise HTTPException(status_code=409, detail="File already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def move_path(source: str, destination: str) -> None:
    src = _resolve_allowed(source)
    dst = _resolve_allowed(destination)
    if not src.exists():
        raise HTTPException(status_code=404, detail="Source path not found")
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)


def copy_path(source: str, destination: str, recursive: bool = False) -> None:
    src = _resolve_allowed(source)
    dst = _resolve_allowed(destination)
    if not src.exists():
        raise HTTPException(status_code=404, detail="Source path not found")

    if src.is_dir():
        if not recursive:
            raise HTTPException(status_code=400, detail="Source is directory. Set recursive=true")
        if dst.exists():
            raise HTTPException(status_code=409, detail="Destination already exists")
        shutil.copytree(src, dst)
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def delete_path(path: str, recursive: bool = False) -> None:
    target = _resolve_allowed(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if target.is_dir():
        if not recursive:
            raise HTTPException(status_code=400, detail="Path is directory. Set recursive=true")
        shutil.rmtree(target)
        return

    target.unlink()


def list_directory(path: str) -> list[dict[str, object]]:
    target = _resolve_allowed(path)
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    items: list[dict[str, object]] = []
    for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        stat = item.stat()
        items.append(
            {
                "name": item.name,
                "path": str(item),
                "is_dir": item.is_dir(),
                "size_bytes": stat.st_size,
            }
        )
    return items


def search_text(root: str, pattern: str, file_glob: str = "**/*", max_results: int = 200) -> list[dict[str, object]]:
    base = _resolve_allowed(root)
    if not base.exists() or not base.is_dir():
        raise HTTPException(status_code=404, detail="Search root not found")

    needle = pattern.strip()
    if not needle:
        raise HTTPException(status_code=400, detail="Pattern cannot be empty")

    results: list[dict[str, object]] = []
    for file_path in base.glob(file_glob):
        if len(results) >= max_results:
            break
        if not file_path.is_file():
            continue
        if file_path.stat().st_size > 2_000_000:
            continue

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if needle.lower() in line.lower():
                results.append(
                    {
                        "path": str(file_path),
                        "line": line_number,
                        "snippet": line.strip()[:300],
                    }
                )
                if len(results) >= max_results:
                    break

    return results
