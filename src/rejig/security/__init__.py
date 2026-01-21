"""Security analysis module for detecting vulnerabilities and secrets.

This module provides tools for security analysis:
- Hardcoded secrets detection (API keys, passwords, tokens)
- Vulnerability scanning (SQL injection, command injection, etc.)
- Security report generation

Example
-------
>>> from rejig import Rejig
>>> rj = Rejig("src/")
>>>
>>> # Find all security issues
>>> issues = rj.find_security_issues()
>>> for issue in issues.critical():
...     print(f"{issue.location}: {issue.message}")
>>>
>>> # Generate a security report
>>> rj.generate_security_report("reports/security.json")
"""
from rejig.security.reporter import (
    SecurityReport,
    SecurityReporter,
)
from rejig.security.secrets import (
    SecretsScanner,
)
from rejig.security.targets import (
    SecurityFinding,
    SecurityTarget,
    SecurityTargetList,
    SecurityType,
)
from rejig.security.vulnerabilities import (
    VulnerabilityScanner,
)

__all__ = [
    # Targets
    "SecurityTarget",
    "SecurityTargetList",
    "SecurityType",
    "SecurityFinding",
    # Scanners
    "SecretsScanner",
    "VulnerabilityScanner",
    # Reporting
    "SecurityReport",
    "SecurityReporter",
]
