#!/usr/bin/env python3
"""
Antigravity Universal Quality Harness & Lifecycle Hook Engine (v2.0.0)
- Auto-detects project runtime and local virtualenv (.venv / venv)
- Executes 5-Tier Quality Gates (Syntax/Lint, Build, Unit Tests, Runtime Smoke, Security/EDR Audit)
- Provides native Antigravity 2.0 Lifecycle Hook handlers (--hook-pre-tool, --hook-session-start)
"""

import sys
import os
import json
import subprocess
import re
from pathlib import Path
from datetime import datetime, timezone

HARNESS_VERSION = "2.0.0"

DEFAULT_SECRET_PATTERNS = [
    r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)\s*[:=]\s*["\'][A-Za-z0-9_\-]{16,}["\']',
    r'-----BEGIN (RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----',
    r'(?i)(password|passwd|pwd)\s*[:=]\s*["\'][^"\']{8,}["\']'
]

EDR_RISKY_PATTERNS = [
    (r'(?i)-EncodedCommand\b', 'PowerShell EncodedCommand detected (high EDR trigger risk)'),
    (r'(?i)\b(VirtualAllocEx|WriteProcessMemory|CreateRemoteThread)\b', 'Direct Win32 Memory Injection API detected'),
    (r'(?i)(Invoke-Expression|\biex\b)\s*\(?\s*(irm|curl|iwr|Invoke-RestMethod|Invoke-WebRequest)', 'Remote script download and direct execution detected'),
    (r'(?i)\b(CurrentVersion\\Run|CurrentVersion\\RunOnce)\b', 'Registry persistence key manipulation detected'),
    (r'(?i)\b(lsass\.exe|sam\.save|sekurlsa)\b', 'Credential dumping target detected')
]


def resolve_python_executable(root: Path) -> str:
    """Prefer project-local virtualenv Python over global interpreter."""
    candidates = [
        root / ".venv" / "Scripts" / "python.exe",
        root / "venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
        root / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return f'"{candidate}"'
    return f'"{sys.executable}"'


def detect_runtime(root: Path) -> dict:
    """Detect runtime ecosystem and return default 5-tier gate commands."""
    commands = {
        "tier0": "",
        "tier1": "",
        "tier2": "",
        "tier3": "",
        "tier4": "internal_security_scan"
    }

    py_files = [
        f for f in root.glob("*.py")
        if f.name != "harness.py"
    ]
    src_py_files = list((root / "src").rglob("*.py")) if (root / "src").exists() else []
    all_target_py = py_files + src_py_files

    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or all_target_py or (root / "harness.py").exists():
        py_bin = resolve_python_executable(root)
        compile_targets = all_target_py if all_target_py else list(root.glob("*.py"))
        if compile_targets:
            quoted_files = " ".join([f'"{f.relative_to(root)}"' for f in compile_targets])
            commands["tier0"] = f"{py_bin} -m py_compile {quoted_files}"

        has_tests = (
            (root / "pytest.ini").exists()
            or (root / "tests").exists()
            or any(root.glob("test_*.py"))
            or any(root.glob("*_test.py"))
        )
        if has_tests:
            commands["tier2"] = f'{py_bin} -m unittest discover -s . -p "*test*.py"'
    elif (root / "package.json").exists():
        commands["tier0"] = "npm run lint --if-present"
        commands["tier1"] = "npm run build --if-present"
        commands["tier2"] = "npm test --if-present"
        commands["tier4"] = "npm audit --audit-level=high"
    elif (root / "Cargo.toml").exists():
        commands["tier0"] = "cargo check"
        commands["tier1"] = "cargo build"
        commands["tier2"] = "cargo test"
    elif (root / "go.mod").exists():
        commands["tier0"] = "go vet ./..."
        commands["tier1"] = "go build ./..."
        commands["tier2"] = "go test ./..."

    return commands


def scan_security_and_edr(root: Path) -> list:
    """Tier 4 static audit: hardcoded secrets and EDR trigger risk patterns."""
    violations = []
    ignored_dirs = {
        '.git', '.venv', 'venv', 'node_modules', '__pycache__',
        '.antigravity', '.agents', 'build', 'dist', '.pytest_cache', '.mypy_cache'
    }
    text_exts = {'.py', '.js', '.ts', '.json', '.yaml', '.yml', '.env', '.sh', '.ps1', '.bat', '.cmd'}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]
        for fname in filenames:
            path = Path(dirpath) / fname
            if path.name == "harness.py":
                continue
            if path.suffix.lower() in text_exts or path.name.startswith('.env'):
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                        for idx, line in enumerate(fp, 1):
                            for pattern in DEFAULT_SECRET_PATTERNS:
                                if re.search(pattern, line):
                                    violations.append({
                                        "category": "SecretLeakage",
                                        "file": str(path.relative_to(root)),
                                        "line": idx,
                                        "snippet": line.strip()[:60],
                                        "reason": "Hardcoded secret or credential pattern detected"
                                    })
                            for pattern, desc in EDR_RISKY_PATTERNS:
                                if re.search(pattern, line):
                                    violations.append({
                                        "category": "EDR_HighRisk_Pattern",
                                        "file": str(path.relative_to(root)),
                                        "line": idx,
                                        "snippet": line.strip()[:60],
                                        "reason": desc
                                    })
                except Exception:
                    pass
    return violations


def run_tier(name: str, cmd: str, root: Path):
    """Execute a single gate command and return (status, diagnostic)."""
    if not cmd:
        return True, None

    if cmd in ("internal_secret_scan", "internal_security_scan"):
        violations = scan_security_and_edr(root)
        if violations:
            return False, {
                "command": "internal_security_scan",
                "exit_code": 1,
                "error_category": "SecurityAndEDRRiskAuditFailed",
                "details": violations,
                "recommendation": (
                    "Remove hardcoded secrets or EDR-triggering patterns "
                    "(e.g. -EncodedCommand, memory injection APIs, remote pipe execution) "
                    "and use environment variables or standard file-based execution."
                )
            }
        return True, None

    try:
        res = subprocess.run(
            cmd,
            cwd=root,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        if res.returncode != 0:
            return False, {
                "command": cmd,
                "exit_code": res.returncode,
                "error_category": "CommandFailure",
                "stdout": res.stdout[-1200:] if res.stdout else "",
                "stderr": res.stderr[-1200:] if res.stderr else "",
                "recommendation": f"Resolve errors reported by '{cmd}' and re-run harness.py."
            }
        return True, None
    except subprocess.TimeoutExpired:
        return False, {
            "command": cmd,
            "exit_code": -1,
            "error_category": "Timeout",
            "stderr": "Command timed out after 120 seconds.",
            "recommendation": "Check for blocking GUI mainloops, infinite loops, or interactive prompts in tests."
        }
    except Exception as exc:
        return False, {
            "command": cmd,
            "exit_code": -1,
            "error_category": "ExecutionError",
            "stderr": str(exc),
            "recommendation": "Verify command configuration in harness.json and local runtime environment."
        }


def handle_pre_tool_hook() -> int:
    """
    Antigravity 2.0 PreToolUse hook handler.
    Reads JSON payload from stdin and blocks EDR-risky shell commands before execution.
    """
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return 0

        payload = json.loads(raw_input)
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {}) or {}

        if tool_name == "run_command":
            cmd_line = str(args.get("CommandLine", ""))
            for pattern, desc in EDR_RISKY_PATTERNS:
                if re.search(pattern, cmd_line):
                    print(json.dumps({
                        "decision": "deny",
                        "reason": f"[Antigravity EDR Guard] Blocked high-risk command pattern: {desc}"
                    }))
                    return 0

        print(json.dumps({"decision": "allow"}))
        return 0
    except Exception:
        print(json.dumps({"decision": "allow"}))
        return 0


def handle_session_start_hook() -> int:
    """
    Antigravity 2.0 SessionStart hook handler.
    Checks PROJECT_CONTEXT.md and injects a concise startup reminder if needed.
    """
    try:
        raw_input = sys.stdin.read()
        payload = json.loads(raw_input) if raw_input.strip() else {}
        workspaces = payload.get("workspacePaths", [])
        root = Path(workspaces[0]) if workspaces else Path.cwd().parent
        context_file = root / "PROJECT_CONTEXT.md"

        if not context_file.exists():
            msg = (
                "[Antigravity Harness v2.0] PROJECT_CONTEXT.md is missing in the workspace root. "
                "When starting development tasks, initialize PROJECT_CONTEXT.md from template."
            )
        else:
            msg = (
                "[Antigravity Harness v2.0] Active workspace rules and 5-Tier Quality Gate (harness.py) are online. "
                "Ensure PROJECT_CONTEXT.md is consulted and kept in sync."
            )

        print(json.dumps({
            "injectSteps": [
                {
                    "ephemeralMessage": msg
                }
            ]
        }))
        return 0
    except Exception:
        print(json.dumps({}))
        return 0


def run_quality_gates() -> int:
    """Execute the 5-Tier Quality Gate suite and print JSON report."""
    root = Path.cwd()
    config_file = root / "harness.json"

    tiers = {}
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                raw_tiers = cfg.get("tiers", {})
                tiers["tier0"] = raw_tiers.get("tier0_lint", {}).get("command", "")
                tiers["tier1"] = raw_tiers.get("tier1_build", {}).get("command", "")
                tiers["tier2"] = raw_tiers.get("tier2_test", {}).get("command", "")
                tiers["tier3"] = raw_tiers.get("tier3_smoke", {}).get("command", "")
                tiers["tier4"] = raw_tiers.get("tier4_security", {}).get("command", "")
        except Exception:
            pass

    detected = detect_runtime(root)
    for key in ["tier0", "tier1", "tier2", "tier3", "tier4"]:
        if not tiers.get(key):
            tiers[key] = detected.get(key, "")

    tier_labels = {
        "tier0": "Tier 0 (Syntax & Static Analysis)",
        "tier1": "Tier 1 (Build & Packaging)",
        "tier2": "Tier 2 (Regression & Unit Test)",
        "tier3": "Tier 3 (Runtime Smoke & Healthcheck)",
        "tier4": "Tier 4 (Secret & EDR Security Audit)"
    }

    report = {
        "harness_version": HARNESS_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "PASSED",
        "evaluated_tiers": {},
        "diagnostics": None
    }

    for key in ["tier0", "tier1", "tier2", "tier3", "tier4"]:
        label = tier_labels[key]
        cmd = tiers[key]
        if not cmd:
            report["evaluated_tiers"][label] = "SKIPPED (No command bound)"
            continue

        success, diag = run_tier(key, cmd, root)
        if not success:
            report["status"] = "FAILED"
            report["evaluated_tier"] = label
            report["diagnostics"] = diag
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 1
        else:
            report["evaluated_tiers"][label] = "PASSED"

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def main():
    if "--hook-pre-tool" in sys.argv:
        sys.exit(handle_pre_tool_hook())
    if "--hook-session-start" in sys.argv:
        sys.exit(handle_session_start_hook())
    sys.exit(run_quality_gates())


if __name__ == "__main__":
    main()
