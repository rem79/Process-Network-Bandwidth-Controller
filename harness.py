#!/usr/bin/env python3
"""
Antigravity Universal Quality Harness Engine (v1.0.0)
Auto-detects project runtime, executes 5-tier gates, and outputs standard diagnostic reports.
"""

import sys
import os
import json
import subprocess
import re
from pathlib import Path

DEFAULT_SECRET_PATTERNS = [
    r'(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)\s*[:=]\s*["\'][A-Za-z0-9_\-]{16,}["\']',
    r'-----BEGIN (RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----',
    r'(?i)(password|passwd|pwd)\s*[:=]\s*["\'][^"\']{8,}["\']'
]

EDR_RISKY_PATTERNS = [
    (r'(?i)-EncodedCommand\b', 'PowerShell EncodedCommand detected (high EDR trigger risk)'),
    (r'(?i)\b(VirtualAllocEx|WriteProcessMemory|CreateRemoteThread)\b', 'Direct Win32 Memory Injection API detected'),
    (r'(?i)(Invoke-Expression|iex)\s*\(?(irm|curl|iwr)', 'Remote script download and direct execution detected'),
    (r'(?i)\b(CurrentVersion\\Run|CurrentVersion\\RunOnce)\b', 'Registry persistence key manipulation detected'),
    (r'(?i)\b(lsass\.exe|sam\.save|sekurlsa)\b', 'Credential dumping target detected')
]

def detect_runtime(root: Path):
    """Detect runtime ecosystem and return default gate commands."""
    commands = {
        "tier0": "",
        "tier1": "",
        "tier2": "",
        "tier3": "",
        "tier4": "internal_security_scan"
    }

    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or any(root.glob("*.py")):
        commands["tier0"] = f"{sys.executable} -m py_compile " + " ".join([f'"{f}"' for f in root.glob("*.py")])
        if (root / "pytest.ini").exists() or (root / "tests").exists() or any(root.glob("test_*.py")):
            commands["tier2"] = f"{sys.executable} -m unittest discover -s . -p \"*test*.py\""
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

def scan_security_and_edr(root: Path):
    """Tier 4 fallback: basic secret & EDR trigger risk scanning."""
    violations = []
    ignored_dirs = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.antigravity', '.agents'}
    text_exts = {'.py', '.js', '.ts', '.json', '.yaml', '.yml', '.env', '.sh', '.ps1', '.bat'}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]
        for f in filenames:
            path = Path(dirpath) / f
            if path.name == "harness.py":
                continue
            if path.suffix in text_exts or path.name.startswith('.env'):

                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                        for idx, line in enumerate(fp, 1):
                            # Secret scan
                            for pattern in DEFAULT_SECRET_PATTERNS:
                                if re.search(pattern, line):
                                    violations.append({
                                        "category": "SecretLeakage",
                                        "file": str(path.relative_to(root)),
                                        "line": idx,
                                        "snippet": line.strip()[:60],
                                        "reason": "Hardcoded secret/credential"
                                    })
                            # EDR risk scan
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
                "recommendation": "Remove hardcoded secrets or EDR-triggering patterns (e.g. EncodedCommand, memory injection, credential access) and adopt standard APIs."
            }
        return True, None


    try:
        res = subprocess.run(cmd, cwd=root, shell=True, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            return False, {
                "command": cmd,
                "exit_code": res.returncode,
                "error_category": "CommandFailure",
                "stdout": res.stdout[-1000:] if res.stdout else "",
                "stderr": res.stderr[-1000:] if res.stderr else "",
                "recommendation": f"Resolve errors reported by '{cmd}' before proceeding."
            }
        return True, None
    except subprocess.TimeoutExpired:
        return False, {
            "command": cmd,
            "exit_code": -1,
            "error_category": "Timeout",
            "stderr": "Command timed out after 120 seconds.",
            "recommendation": "Check for infinite loops or long-running tasks."
        }
    except Exception as e:
        return False, {
            "command": cmd,
            "exit_code": -1,
            "error_category": "ExecutionError",
            "stderr": str(e),
            "recommendation": "Verify command configuration and runtime environment."
        }

def main():
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
    for k in ["tier0", "tier1", "tier2", "tier3", "tier4"]:
        if not tiers.get(k):
            tiers[k] = detected.get(k, "")

    tier_labels = {
        "tier0": "Tier 0 (Syntax & Static Analysis)",
        "tier1": "Tier 1 (Build & Packaging)",
        "tier2": "Tier 2 (Regression & Unit Test)",
        "tier3": "Tier 3 (Runtime Smoke & Healthcheck)",
        "tier4": "Tier 4 (Secret & Security Audit)"
    }

    report = {
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
            sys.exit(1)
        else:
            report["evaluated_tiers"][label] = "PASSED"

    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(0)

if __name__ == "__main__":
    main()
