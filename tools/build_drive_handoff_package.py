#!/usr/bin/env python3
"""Build a text-only Google Drive handoff package for the REAPER automix project."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "drive_handoff"
ATTACHMENT_BRIEF = Path(
    "/Users/hantaeheuk/.codex/attachments/"
    "bfc21f5c-87f9-497d-8d5c-95fe01d4c5a8/pasted-text.txt"
)

TARGET_DRIVE_FOLDER_ID = "1AmOhts2f73Y2RcxvnrgyEU4ei747bY5t"
TARGET_DRIVE_FOLDER_URL = (
    "https://drive.google.com/drive/folders/" + TARGET_DRIVE_FOLDER_ID
)

TEXT_EXTENSIONS = {
    ".ass",
    ".c",
    ".cfg",
    ".cmake",
    ".csv",
    ".h",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".lua",
    ".mjs",
    ".md",
    ".py",
    ".rst",
    ".sh",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}

EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "drive_handoff",
    "node_modules",
    "venv",
    ".venv",
    "tools/bin",
}

EXCLUDED_PREFIXES = (
    "audio_work/",
    "hwp_extract/",
    "ql_",
)

BINARY_OR_MEDIA_EXTENSIONS = {
    ".aif",
    ".aiff",
    ".aup3",
    ".doc",
    ".docx",
    ".flac",
    ".gif",
    ".heic",
    ".hwp",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".odp",
    ".ods",
    ".odt",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".rpp",
    ".rpp-bak",
    ".rtf",
    ".tif",
    ".tiff",
    ".wav",
    ".webp",
    ".xls",
    ".xlsx",
    ".zip",
}

SECRET_NAME_RE = re.compile(
    r"(?i)(^|[._/-])(secret|credential|credentials|token|api[_-]?key|"
    r"private[_-]?key|password|passwd|oauth|client[_-]?secret|\.env)([._/-]|$)"
)

SECRET_CONTENT_RES = [
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |DSA |EC |)?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:OPENAI_API_KEY|GOOGLE_API_KEY|ANTHROPIC_API_KEY)\s*=\s*[^\s]+"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
]

MAX_SINGLE_FILE_BYTES = 2_000_000
SNAPSHOT_CHUNK_BYTES = 1_600_000


@dataclass
class IncludedFile:
    path: str
    size: int
    sha256: str


@dataclass
class ExcludedFile:
    path: str
    reason: str
    size: int | None = None


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError:
        return "git not available\n"
    return result.stdout


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_under_excluded_dir(path: Path) -> str | None:
    parts = rel(path).split("/")
    for name in EXCLUDED_DIR_NAMES:
        name_parts = name.split("/")
        for index in range(0, len(parts) - len(name_parts) + 1):
            if parts[index : index + len(name_parts)] == name_parts:
                return f"excluded directory: {name}"
    relative = rel(path)
    for prefix in EXCLUDED_PREFIXES:
        if relative.startswith(prefix):
            return f"excluded prefix: {prefix}"
    return None


def looks_like_text(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    if path.name in {"CMakeLists.txt", ".gitignore"}:
        return True
    return False


def file_secret_reason(path: Path) -> str | None:
    relative = rel(path)
    if SECRET_NAME_RE.search(relative):
        return "secret-like filename"
    try:
        sample = path.read_bytes()[:256_000].decode("utf-8", errors="ignore")
    except OSError:
        return "unreadable during secret scan"
    for pattern in SECRET_CONTENT_RES:
        if pattern.search(sample):
            return "secret-like content pattern"
    return None


def should_include(path: Path) -> tuple[bool, str | None]:
    excluded_dir = is_under_excluded_dir(path)
    if excluded_dir:
        return False, excluded_dir
    suffix = path.suffix.lower()
    if suffix in BINARY_OR_MEDIA_EXTENSIONS:
        return False, f"binary/media/project extension: {suffix}"
    if not looks_like_text(path):
        return False, "non-text or unknown extension"
    try:
        size = path.stat().st_size
    except OSError:
        return False, "unreadable stat"
    if size > MAX_SINGLE_FILE_BYTES:
        return False, f"large text file over {MAX_SINGLE_FILE_BYTES} bytes"
    secret_reason = file_secret_reason(path)
    if secret_reason:
        return False, secret_reason
    return True, None


def iter_project_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.is_file():
            files.append(path)
    return sorted(files, key=lambda item: rel(item))


def copy_included_files(
    package_dir: Path, included: list[IncludedFile]
) -> Path:
    source_tree = package_dir / "source_tree"
    for item in included:
        src = ROOT / item.path
        dst = source_tree / item.path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    if ATTACHMENT_BRIEF.exists():
        dst = source_tree / "external_context" / "initial_pasted_project_brief.txt"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ATTACHMENT_BRIEF, dst)

    return source_tree


def write_git_state(package_dir: Path) -> None:
    git_dir = package_dir / "git_state"
    git_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "GIT_HEAD.txt": [
            "branch:\n",
            run_git(["branch", "--show-current"]),
            "\nhead:\n",
            run_git(["rev-parse", "HEAD"]),
            "\nlast_commit:\n",
            run_git(["log", "-1", "--oneline", "--decorate"]),
            "\nremotes:\n",
            run_git(["remote", "-v"]),
        ],
        "GIT_STATUS_SHORT.txt": [run_git(["status", "--short"])],
        "GIT_DIFF_STAT.txt": [run_git(["diff", "--stat"])],
        "GIT_DELETED_FILES.txt": [run_git(["ls-files", "--deleted"])],
        "GIT_UNTRACKED_FILES.txt": [
            run_git(["ls-files", "--others", "--exclude-standard"])
        ],
    }
    for name, chunks in files.items():
        (git_dir / name).write_text("".join(chunks), encoding="utf-8")


def write_source_snapshots(
    package_dir: Path, included: list[IncludedFile]
) -> list[Path]:
    snapshot_paths: list[Path] = []
    current_index = 1
    current_bytes = 0
    current_chunks: list[str] = []

    def flush() -> None:
        nonlocal current_index, current_bytes, current_chunks
        if not current_chunks:
            return
        path = package_dir / f"SOURCE_SNAPSHOT_{current_index:03d}.txt"
        path.write_text("".join(current_chunks), encoding="utf-8")
        snapshot_paths.append(path)
        current_index += 1
        current_bytes = 0
        current_chunks = []

    for item in included:
        src = ROOT / item.path
        text = src.read_text(encoding="utf-8", errors="replace")
        block = (
            f"\n\n===== FILE: {item.path} =====\n"
            f"size_bytes: {item.size}\n"
            f"sha256: {item.sha256}\n\n"
            f"{text}"
        )
        block_bytes = len(block.encode("utf-8"))
        if current_bytes and current_bytes + block_bytes > SNAPSHOT_CHUNK_BYTES:
            flush()
        current_chunks.append(block)
        current_bytes += block_bytes

    if ATTACHMENT_BRIEF.exists():
        text = ATTACHMENT_BRIEF.read_text(encoding="utf-8", errors="replace")
        digest = sha256_file(ATTACHMENT_BRIEF)
        block = (
            "\n\n===== FILE: external_context/initial_pasted_project_brief.txt =====\n"
            f"size_bytes: {ATTACHMENT_BRIEF.stat().st_size}\n"
            f"sha256: {digest}\n\n"
            f"{text}"
        )
        if current_bytes and current_bytes + len(block.encode("utf-8")) > SNAPSHOT_CHUNK_BYTES:
            flush()
        current_chunks.append(block)
    flush()
    return snapshot_paths


def write_manifest_files(
    package_dir: Path,
    included: list[IncludedFile],
    excluded: list[ExcludedFile],
    snapshot_paths: list[Path],
    package_zip: Path,
) -> None:
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(ROOT),
        "target_drive_folder_id": TARGET_DRIVE_FOLDER_ID,
        "target_drive_folder_url": TARGET_DRIVE_FOLDER_URL,
        "included_file_count": len(included),
        "excluded_file_count": len(excluded),
        "snapshot_chunks": [path.name for path in snapshot_paths],
        "source_tree_zip": "REAPER_AUTOMIX_SOURCE_TREE_TEXT_ONLY.zip",
        "package_zip": package_zip.name,
        "attachment_brief_included": ATTACHMENT_BRIEF.exists(),
        "guardrails": [
            "Raw audio, stems, renders, reference media, DAW project files, credentials, and secret-like files are excluded.",
            "This package is intended for code/docs/test/report development handoff, not audio delivery.",
            "Any listening-quality, loudness, or plugin-runtime claims must be revalidated on the next machine.",
        ],
        "included_files": [item.__dict__ for item in included],
        "excluded_files": [item.__dict__ for item in excluded],
    }
    (package_dir / "FILE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    by_reason: dict[str, int] = {}
    for item in excluded:
        by_reason[item.reason] = by_reason.get(item.reason, 0) + 1

    manifest_md = [
        "# REAPER AutoMix Drive Handoff Manifest\n\n",
        f"- Created UTC: {manifest['created_at_utc']}\n",
        f"- Workspace root: `{ROOT}`\n",
        f"- Target Drive folder: {TARGET_DRIVE_FOLDER_URL}\n",
        f"- Included files: {len(included)}\n",
        f"- Excluded files: {len(excluded)}\n",
        f"- Snapshot chunks: {len(snapshot_paths)}\n",
        f"- Source tree zip: `REAPER_AUTOMIX_SOURCE_TREE_TEXT_ONLY.zip`\n",
        f"- Whole package zip: `{package_zip.name}`\n\n",
        "## Exclusion Summary\n\n",
    ]
    for reason, count in sorted(by_reason.items(), key=lambda item: (-item[1], item[0])):
        manifest_md.append(f"- {reason}: {count}\n")
    manifest_md.append("\n## Included Files\n\n")
    for item in included:
        manifest_md.append(f"- `{item.path}` ({item.size} bytes, sha256 {item.sha256})\n")
    (package_dir / "FILE_MANIFEST.md").write_text(
        "".join(manifest_md), encoding="utf-8"
    )

    excluded_md = [
        "# Excluded Paths\n\n",
        "These files were not copied into the Drive handoff package.\n",
        "Most exclusions are intentional: raw audio, renders, DAW project files, binary office/media files, generated caches, local tooling binaries, unrelated admin docs, or secret-like paths.\n\n",
    ]
    for reason, count in sorted(by_reason.items(), key=lambda item: (-item[1], item[0])):
        excluded_md.append(f"## {reason} ({count})\n\n")
        examples = [item for item in excluded if item.reason == reason][:200]
        for item in examples:
            size = "" if item.size is None else f" ({item.size} bytes)"
            excluded_md.append(f"- `{item.path}`{size}\n")
        if count > len(examples):
            excluded_md.append(f"- ... {count - len(examples)} more\n")
        excluded_md.append("\n")
    (package_dir / "EXCLUDED_PATHS.md").write_text(
        "".join(excluded_md), encoding="utf-8"
    )


def write_readme(package_dir: Path, snapshot_paths: list[Path]) -> None:
    readme = f"""# REAPER AutoMix Drive Handoff

Created for the Google Drive folder:
{TARGET_DRIVE_FOLDER_URL}

This is a development handoff for the REAPER automix / mastering assistant in
`{ROOT}`. It captures the current code, docs, tests, text reports, git state,
and the original pasted project brief in a Drive-friendly, text-only package.

## Start Here

1. Download or sync this whole handoff folder from Drive.
2. Unzip `REAPER_AUTOMIX_SOURCE_TREE_TEXT_ONLY.zip`, or use the `source_tree/`
   folder if Drive sync preserves folders.
3. Copy the contents of `source_tree/` into a new local workspace.
4. Read these files first:
   - `README.md`
   - `QUICKSTART.md`
   - `TESTING_AND_HARNESS.md`
   - `PLUGIN_FALLBACKS.md`
   - `REAPER_REFERENCE_MIX_PIPELINE.md`
   - `docs/plugin_intelligence_and_adapter_safety.md`
   - `external_context/initial_pasted_project_brief.txt`
5. Run the focused current check:
   `python3 -m pytest tests/test_prompt81_plugin_semantic_validation_runtime_report_authoring_gate.py -q`

## Current State

- Prompt81 plugin semantic validation runtime report authoring gate is present.
- Focused Prompt81 test run on 2026-06-03 KST: `6 passed`.
- Last known Prompt80 package state before this handoff: requirements traceability
  complete, 15/15 requirements, professional readiness still `review_required`,
  open risk count dominated by plugin validation readiness, and no live REAPER
  plugin-runtime listening claim.
- The worktree is very dirty. `git_state/` records the exact short status,
  deleted file list, untracked file list, head, remotes, and diff stat.
- This handoff captures present text/code/report files as they exist on disk.

## What Is Included

- Python, Lua, JS, JSON, Markdown, CSV/TSV, shell, config, and ASS text files.
- Source-preserving copy under `source_tree/`.
- Concatenated source snapshots split into {len(snapshot_paths)} chunk(s):
  {", ".join(path.name for path in snapshot_paths)}.
- File hashes and sizes in `FILE_MANIFEST.json`.
- Exclusion reasoning in `EXCLUDED_PATHS.md`.
- Git state in `git_state/`.

## What Is Not Included

Raw audio, stems, rendered media, REAPER project files, reference media, binary
office/media files, local binary tools, caches, unrelated admin document folders,
and secret-like filenames/content were excluded on purpose.

Do not treat this as a final audio delivery package. Treat it as a developer
handoff that is safe to sync through Drive.

## Next Development Notes

- Continue plugin semantic validation work from Prompt81.
- Re-run broader tests before claiming readiness.
- Revalidate any REAPER/plugin/runtime behavior on the target machine.
- Keep reports precise: no unsupported listening, loudness, plugin availability,
  or commercial-readiness claims without fresh evidence.
"""
    (package_dir / "REAPER_AUTOMIX_DRIVE_HANDOFF_README.md").write_text(
        readme, encoding="utf-8"
    )


def zip_directory(source_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path == zip_path:
                continue
            if path.is_file():
                archive.write(path, path.relative_to(source_dir.parent))


def build_package() -> dict[str, object]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_dir = OUT_ROOT / f"reaper_automix_handoff_{timestamp}"
    package_dir.mkdir(parents=True, exist_ok=False)

    included: list[IncludedFile] = []
    excluded: list[ExcludedFile] = []

    for path in iter_project_files():
        try:
            size = path.stat().st_size
        except OSError:
            size = None
        ok, reason = should_include(path)
        if ok:
            included.append(
                IncludedFile(path=rel(path), size=size or 0, sha256=sha256_file(path))
            )
        else:
            excluded.append(ExcludedFile(path=rel(path), reason=reason or "excluded", size=size))

    write_git_state(package_dir)
    source_tree = copy_included_files(package_dir, included)
    snapshot_paths = write_source_snapshots(package_dir, included)

    source_tree_zip = package_dir / "REAPER_AUTOMIX_SOURCE_TREE_TEXT_ONLY.zip"
    zip_directory(source_tree, source_tree_zip)

    package_zip = OUT_ROOT / f"{package_dir.name}.zip"
    write_manifest_files(package_dir, included, excluded, snapshot_paths, package_zip)
    write_readme(package_dir, snapshot_paths)
    zip_directory(package_dir, package_zip)

    return {
        "package_dir": str(package_dir),
        "package_zip": str(package_zip),
        "source_tree_zip": str(source_tree_zip),
        "included_file_count": len(included),
        "excluded_file_count": len(excluded),
        "snapshot_chunk_count": len(snapshot_paths),
        "target_drive_folder_url": TARGET_DRIVE_FOLDER_URL,
    }


def main() -> int:
    result = build_package()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
