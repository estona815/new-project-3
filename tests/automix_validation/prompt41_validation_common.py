from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATION_ROOT = ROOT / "tests" / "automix_validation"
FIXTURES = VALIDATION_ROOT / "fixtures"
AUDIO = FIXTURES / "audio"
ANALYSIS_JSON = FIXTURES / "analysis_json"
MOCK_PROJECTS = FIXTURES / "mock_projects"
_FIXTURE_CACHE: dict | None = None


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def ensure_prompt41_fixtures() -> dict:
    global _FIXTURE_CACHE
    if _FIXTURE_CACHE is not None:
        return _FIXTURE_CACHE
    audio_gen = load_module(VALIDATION_ROOT / "scripts" / "generate_synthetic_audio_fixtures.py", "prompt41_audio_gen")
    analysis_gen = load_module(VALIDATION_ROOT / "scripts" / "generate_mock_analysis_fixtures.py", "prompt41_analysis_gen")
    project_gen = load_module(VALIDATION_ROOT / "scripts" / "create_minimal_reaper_test_project.py", "prompt41_project_gen")
    audio_manifest = audio_gen.generate()
    analysis_manifest = analysis_gen.generate()
    project_manifest = project_gen.generate()
    _FIXTURE_CACHE = {
        "audio": audio_manifest,
        "analysis": analysis_manifest,
        "projects": project_manifest,
    }
    return _FIXTURE_CACHE


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def output_dir(tmp_path: Path) -> Path:
    path = tmp_path / "automix"
    path.mkdir(parents=True, exist_ok=True)
    return path
