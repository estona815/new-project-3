from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from paths import PROJECT_ROOT


LOGIC_APP_PATH = Path("/Applications/Logic Pro.app")
WORKING_WAV = PROJECT_ROOT / "04_PROCESSED_AUDIO" / "working_input.wav"
LOGIC_PROJECT = PROJECT_ROOT / "03_LOGIC_PROJECT" / "suno_humanized_project.logicx"
STATUS_PATH = PROJECT_ROOT / "03_LOGIC_PROJECT" / "logic_automation_status.md"
SCRIPT_DIR = PROJECT_ROOT / "scripts"


@dataclass(frozen=True)
class LogicStatus:
    status: str
    message: str
    is_macos: bool
    logic_app_exists: bool
    osascript_available: bool
    working_wav_exists: bool
    project_path: str
    project_exists: bool
    attempted_commands: tuple[str, ...]
    timestamp: str


def run_command(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)


def is_macos() -> bool:
    return platform.system() == "Darwin"


def osascript_available() -> bool:
    return shutil.which("osascript") is not None


def logic_available() -> bool:
    return is_macos() and LOGIC_APP_PATH.exists() and osascript_available()


def status_markdown(status: LogicStatus) -> str:
    commands = "\n".join(f"- `{command}`" for command in status.attempted_commands) or "- none"
    manual_steps = "\n".join(
        [
            "1. Open Logic Pro manually.",
            "2. Create a new empty project.",
            "3. Set the project sample rate to match the selected export format.",
            "4. Import `04_PROCESSED_AUDIO/working_input.wav`.",
            "5. Follow `02_EDIT_PLAN/edit_plan.md` for arrangement, crossfades, mix balance, vocal-like texture suppression, and automation.",
            "6. Save the project as `03_LOGIC_PROJECT/suno_humanized_project.logicx`.",
            "7. Export WAV and verify the final file in the later export/QC stage.",
        ]
    )
    return (
        "# Logic Automation Status\n\n"
        f"- status: {status.status}\n"
        f"- message: {status.message}\n"
        f"- timestamp: {status.timestamp}\n"
        f"- macOS detected: {str(status.is_macos).lower()}\n"
        f"- Logic Pro app exists: {str(status.logic_app_exists).lower()}\n"
        f"- osascript available: {str(status.osascript_available).lower()}\n"
        f"- working_input.wav exists: {str(status.working_wav_exists).lower()}\n"
        f"- project path: `{status.project_path}`\n"
        f"- project/package exists: {str(status.project_exists).lower()}\n\n"
        "## Attempted Commands\n\n"
        f"{commands}\n\n"
        "## Manual Logic Instructions\n\n"
        "Automation may be unavailable or partial. Use these exact manual steps when status is not `success`:\n\n"
        f"{manual_steps}\n\n"
        "## Important Limitation\n\n"
        "This status file does not claim that Logic performed a humanized mix. Full arrangement, plugin moves, EQ curves, automation, and export verification still require manual work or later pipeline stages.\n"
    )


def write_status(status: LogicStatus, status_path: Path | None = None) -> Path:
    resolved_path = status_path or STATUS_PATH
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(status_markdown(status), encoding="utf-8")
    return resolved_path


def build_status(status: str, message: str, attempted: list[str] | None = None) -> LogicStatus:
    return LogicStatus(
        status=status,
        message=message,
        is_macos=is_macos(),
        logic_app_exists=LOGIC_APP_PATH.exists(),
        osascript_available=osascript_available(),
        working_wav_exists=WORKING_WAV.exists(),
        project_path=str(LOGIC_PROJECT),
        project_exists=LOGIC_PROJECT.exists(),
        attempted_commands=tuple(attempted or []),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def check_logic_availability() -> LogicStatus:
    if not is_macos():
        return build_status("unavailable", "Not running on macOS; Logic automation skipped and fallback processing is required.")
    if not LOGIC_APP_PATH.exists():
        return build_status("unavailable", "Logic Pro was not found at /Applications/Logic Pro.app; fallback processing is required.")
    if not osascript_available():
        return build_status("unavailable", "osascript is unavailable; Logic AppleScript automation cannot run.")
    return build_status("partial_success", "Logic Pro and osascript are available, but project automation has not been attempted yet.")


def attempt_logic_project() -> LogicStatus:
    attempted: list[str] = []
    availability = check_logic_availability()
    if availability.status == "unavailable":
        write_status(availability)
        return availability
    if not WORKING_WAV.exists():
        status = build_status("failed", "working_input.wav is missing; cannot import audio into Logic.", attempted)
        write_status(status)
        return status

    LOGIC_PROJECT.parent.mkdir(parents=True, exist_ok=True)
    create_script = SCRIPT_DIR / "logic_create_project.scpt"
    import_script = SCRIPT_DIR / "logic_import_audio.scpt"
    save_script = SCRIPT_DIR / "logic_save_project.scpt"
    script_calls = [
        ["osascript", str(create_script)],
        ["osascript", str(import_script), str(WORKING_WAV)],
        ["osascript", str(save_script), str(LOGIC_PROJECT)],
    ]

    errors: list[str] = []
    for command in script_calls:
        attempted.append(" ".join(command))
        try:
            result = run_command(command)
        except (subprocess.SubprocessError, OSError) as error:
            errors.append(str(error))
            break
        if result.returncode != 0:
            errors.append(result.stderr.strip() or result.stdout.strip() or f"Command failed: {' '.join(command)}")
            break

    project_exists = LOGIC_PROJECT.exists()
    if project_exists:
        status_value = "success" if not errors else "partial_success"
        message = "Logic project exists after automation attempt."
        if errors:
            message += f" Automation reported limitations: {'; '.join(errors)}"
    elif errors:
        status_value = "failed"
        message = "Logic automation failed and no .logicx project/package was verified. " + "; ".join(errors)
    else:
        status_value = "partial_success"
        message = "Logic automation commands returned without verified .logicx output; manual save is required."

    status = build_status(status_value, message, attempted)
    write_status(status)
    return status


def write_availability_status() -> LogicStatus:
    status = check_logic_availability()
    write_status(status)
    return status
