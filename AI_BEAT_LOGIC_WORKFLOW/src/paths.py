from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DIRECTORIES = (
    "00_INPUT_SUNO",
    "01_ANALYSIS",
    "02_EDIT_PLAN",
    "03_LOGIC_PROJECT",
    "04_PROCESSED_AUDIO",
    "05_FINAL_WAV",
    "06_QC_REPORT",
    "tools",
    "scripts",
    "src",
    "tests",
)


def project_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)


def ensure_folder_structure(project_root: Path = PROJECT_ROOT) -> list[Path]:
    folders: list[Path] = []
    for relative_path in REQUIRED_DIRECTORIES:
        folder = project_root / relative_path
        folder.mkdir(parents=True, exist_ok=True)
        folders.append(folder)
    return folders

