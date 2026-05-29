from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


SEVERITIES = ("PASS", "INFO", "WARN", "FAIL", "BLOCKER")
SEVERITY_RANK = {name: index for index, name in enumerate(SEVERITIES)}
WARN_PLUS = {"WARN", "FAIL", "BLOCKER"}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    evidence: str
    recommendation: str
    affected_file: str = ""
    failed_assumption: str = ""
    command_to_rerun: str = ""
    human_listening_required: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_severity(severity: str) -> str:
    normalized = str(severity).strip().upper()
    if normalized not in SEVERITY_RANK:
        raise ValueError(f"Unknown severity: {severity!r}")
    return normalized


def add_finding(
    severity: str,
    code: str,
    message: str,
    evidence: str,
    recommendation: str,
    findings: list[Finding] | None = None,
    *,
    affected_file: str = "",
    failed_assumption: str = "",
    command_to_rerun: str = "",
    human_listening_required: bool = False,
) -> Finding:
    finding = Finding(
        severity=normalize_severity(severity),
        code=str(code),
        message=str(message),
        evidence=str(evidence),
        recommendation=str(recommendation),
        affected_file=str(affected_file),
        failed_assumption=str(failed_assumption),
        command_to_rerun=str(command_to_rerun),
        human_listening_required=bool(human_listening_required),
    )
    if findings is not None:
        findings.append(finding)
    return finding


def max_severity(findings: Iterable[Finding | dict]) -> str:
    highest = "PASS"
    for finding in findings:
        severity = finding["severity"] if isinstance(finding, dict) else finding.severity
        severity = normalize_severity(severity)
        if SEVERITY_RANK[severity] > SEVERITY_RANK[highest]:
            highest = severity
    return highest


def has_warn_plus(findings: Iterable[Finding | dict]) -> bool:
    return SEVERITY_RANK[max_severity(findings)] >= SEVERITY_RANK["WARN"]


def status_from_findings(findings: Iterable[Finding | dict]) -> str:
    highest = max_severity(findings)
    if highest == "BLOCKER":
        return "blocked"
    if highest == "FAIL":
        return "failed"
    if highest == "WARN":
        return "not_final_warn"
    return "pass"


def findings_to_dicts(findings: Iterable[Finding]) -> list[dict]:
    return [finding.to_dict() for finding in findings]


def warn_plus_findings(findings: Iterable[Finding]) -> list[Finding]:
    return [finding for finding in findings if finding.severity in WARN_PLUS]


def findings_to_markdown(findings: Iterable[Finding]) -> str:
    rows = []
    for finding in findings:
        rows.append(
            "| {severity} | {code} | {file} | {assumption} | {evidence} | {next_patch} | {command} | {listen} |".format(
                severity=finding.severity,
                code=finding.code,
                file=finding.affected_file or "-",
                assumption=finding.failed_assumption or "-",
                evidence=finding.evidence.replace("\n", " "),
                next_patch=finding.recommendation.replace("\n", " "),
                command=finding.command_to_rerun or "-",
                listen="yes" if finding.human_listening_required else "no",
            )
        )
    if not rows:
        rows.append("| PASS | NO_FINDINGS | - | - | No validation findings. | Keep reports attached to the render. | - | no |")
    return "\n".join(
        [
            "| Severity | Code | Affected file | Failed assumption | Evidence | Exact next patch | Exact command to rerun | Human listening |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            *rows,
        ]
    )

