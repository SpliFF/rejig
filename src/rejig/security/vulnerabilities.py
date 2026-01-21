"""Vulnerability detection for common security issues.

Detects common vulnerability patterns:
- SQL injection risks
- Command/shell injection risks
- Path traversal vulnerabilities
- Unsafe deserialization (pickle, yaml, etc.)
- Insecure random number generation
- Dangerous eval/exec usage
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

from rejig.security.targets import (
    SecurityFinding,
    SecurityTarget,
    SecurityTargetList,
    SecurityType,
)

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig


@dataclass
class VulnerabilityPattern:
    """Pattern for detecting a specific vulnerability type.

    Attributes
    ----------
    name : str
        Name of the vulnerability pattern.
    pattern : re.Pattern
        Compiled regex pattern.
    security_type : SecurityType
        Type of security finding.
    severity : str
        Severity level.
    message : str
        Description of the vulnerability.
    recommendation : str
        Suggested fix.
    """

    name: str
    pattern: re.Pattern
    security_type: SecurityType
    severity: str
    message: str
    recommendation: str


# SQL Injection patterns
SQL_INJECTION_PATTERNS = [
    VulnerabilityPattern(
        name="String format in SQL",
        pattern=re.compile(r'(execute|raw|query)\s*\([^)]*%\s*\(', re.IGNORECASE),
        security_type=SecurityType.SQL_INJECTION,
        severity="critical",
        message="Potential SQL injection via string formatting",
        recommendation="Use parameterized queries instead of string formatting.",
    ),
    VulnerabilityPattern(
        name="f-string in SQL",
        pattern=re.compile(r'(execute|raw|query)\s*\(\s*f["\']', re.IGNORECASE),
        security_type=SecurityType.SQL_INJECTION,
        severity="critical",
        message="Potential SQL injection via f-string",
        recommendation="Use parameterized queries instead of f-strings.",
    ),
    VulnerabilityPattern(
        name="String concatenation in SQL",
        pattern=re.compile(r'(execute|raw|query)\s*\([^)]*\+\s*[a-zA-Z_]', re.IGNORECASE),
        security_type=SecurityType.SQL_INJECTION,
        severity="critical",
        message="Potential SQL injection via string concatenation",
        recommendation="Use parameterized queries instead of string concatenation.",
    ),
    VulnerabilityPattern(
        name=".format() in SQL",
        pattern=re.compile(r'(execute|raw|query)\s*\([^)]*\.format\s*\(', re.IGNORECASE),
        security_type=SecurityType.SQL_INJECTION,
        severity="critical",
        message="Potential SQL injection via .format()",
        recommendation="Use parameterized queries instead of .format().",
    ),
]

# Shell/Command injection patterns
SHELL_INJECTION_PATTERNS = [
    VulnerabilityPattern(
        name="os.system with variable",
        pattern=re.compile(r'os\.system\s*\([^)]*[+%]|os\.system\s*\(\s*f["\']'),
        security_type=SecurityType.SHELL_INJECTION,
        severity="critical",
        message="Potential shell injection via os.system()",
        recommendation="Use subprocess with shell=False and pass arguments as a list.",
    ),
    VulnerabilityPattern(
        name="subprocess with shell=True",
        pattern=re.compile(r'subprocess\.(run|call|Popen|check_output|check_call)\s*\([^)]*shell\s*=\s*True'),
        security_type=SecurityType.SHELL_INJECTION,
        severity="high",
        message="Subprocess with shell=True can be dangerous",
        recommendation="Avoid shell=True. Pass command as a list instead.",
    ),
    VulnerabilityPattern(
        name="os.popen",
        pattern=re.compile(r'os\.popen\s*\('),
        security_type=SecurityType.SHELL_INJECTION,
        severity="high",
        message="os.popen is deprecated and can be vulnerable to injection",
        recommendation="Use subprocess module with shell=False instead.",
    ),
    VulnerabilityPattern(
        name="commands module",
        pattern=re.compile(r'commands\.(getoutput|getstatusoutput)\s*\('),
        security_type=SecurityType.SHELL_INJECTION,
        severity="high",
        message="commands module is vulnerable to shell injection",
        recommendation="Use subprocess module with shell=False instead.",
    ),
]

# Unsafe deserialization patterns
UNSAFE_DESERIALIZATION_PATTERNS = [
    VulnerabilityPattern(
        name="pickle.load",
        pattern=re.compile(r'pickle\.(load|loads)\s*\('),
        security_type=SecurityType.UNSAFE_PICKLE,
        severity="high",
        message="Pickle deserialization can execute arbitrary code",
        recommendation="Avoid pickle for untrusted data. Use JSON or other safe formats.",
    ),
    VulnerabilityPattern(
        name="cPickle.load",
        pattern=re.compile(r'cPickle\.(load|loads)\s*\('),
        security_type=SecurityType.UNSAFE_PICKLE,
        severity="high",
        message="cPickle deserialization can execute arbitrary code",
        recommendation="Avoid pickle for untrusted data. Use JSON or other safe formats.",
    ),
    VulnerabilityPattern(
        name="yaml.load without Loader",
        pattern=re.compile(r'yaml\.load\s*\([^)]*\)(?!.*Loader)'),
        security_type=SecurityType.UNSAFE_YAML_LOAD,
        severity="critical",
        message="yaml.load without Loader can execute arbitrary code",
        recommendation="Use yaml.safe_load() or specify Loader=yaml.SafeLoader.",
    ),
    VulnerabilityPattern(
        name="yaml.unsafe_load",
        pattern=re.compile(r'yaml\.unsafe_load\s*\('),
        security_type=SecurityType.UNSAFE_YAML_LOAD,
        severity="critical",
        message="yaml.unsafe_load can execute arbitrary code",
        recommendation="Use yaml.safe_load() instead.",
    ),
    VulnerabilityPattern(
        name="shelve.open",
        pattern=re.compile(r'shelve\.open\s*\('),
        security_type=SecurityType.UNSAFE_DESERIALIZE,
        severity="medium",
        message="shelve uses pickle internally, which can be unsafe",
        recommendation="Avoid shelve for untrusted data. Use safer alternatives.",
    ),
    VulnerabilityPattern(
        name="marshal.load",
        pattern=re.compile(r'marshal\.(load|loads)\s*\('),
        security_type=SecurityType.UNSAFE_DESERIALIZE,
        severity="medium",
        message="marshal deserialization can be unsafe",
        recommendation="Use JSON or other safe formats for untrusted data.",
    ),
]

# Dangerous eval/exec patterns
EVAL_EXEC_PATTERNS = [
    VulnerabilityPattern(
        name="eval with variable",
        pattern=re.compile(r'eval\s*\(\s*[a-zA-Z_][a-zA-Z0-9_]*\s*[,\)]'),
        security_type=SecurityType.UNSAFE_EVAL,
        severity="critical",
        message="eval() with variable input can execute arbitrary code",
        recommendation="Avoid eval(). Use ast.literal_eval() for safe evaluation.",
    ),
    VulnerabilityPattern(
        name="exec with variable",
        pattern=re.compile(r'exec\s*\(\s*[a-zA-Z_][a-zA-Z0-9_]*\s*[,\)]'),
        security_type=SecurityType.UNSAFE_EXEC,
        severity="critical",
        message="exec() with variable input can execute arbitrary code",
        recommendation="Avoid exec() with untrusted input entirely.",
    ),
    VulnerabilityPattern(
        name="compile with exec",
        pattern=re.compile(r"compile\s*\([^)]*['\"]exec['\"]"),
        security_type=SecurityType.UNSAFE_EXEC,
        severity="high",
        message="compile() with exec mode can be dangerous",
        recommendation="Ensure input to compile() is trusted.",
    ),
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    VulnerabilityPattern(
        name="open with user input",
        pattern=re.compile(r'open\s*\([^)]*\+\s*[a-zA-Z_]|open\s*\(\s*f["\']'),
        security_type=SecurityType.PATH_TRAVERSAL,
        severity="high",
        message="Potential path traversal via string concatenation/f-string",
        recommendation="Validate and sanitize file paths. Use pathlib for path manipulation.",
    ),
    VulnerabilityPattern(
        name="os.path.join with user input",
        pattern=re.compile(r'os\.path\.join\s*\([^)]*request\.|os\.path\.join\s*\([^)]*user'),
        security_type=SecurityType.PATH_TRAVERSAL,
        severity="medium",
        message="os.path.join doesn't prevent path traversal",
        recommendation="Validate paths don't contain .. and are within allowed directories.",
    ),
]

# Insecure random patterns
INSECURE_RANDOM_PATTERNS = [
    VulnerabilityPattern(
        name="random for security",
        pattern=re.compile(r'random\.(random|randint|choice|shuffle|sample)\s*\('),
        security_type=SecurityType.INSECURE_RANDOM,
        severity="medium",
        message="random module is not cryptographically secure",
        recommendation="Use secrets module for security-sensitive random values.",
    ),
]

# Weak cryptography patterns
WEAK_CRYPTO_PATTERNS = [
    VulnerabilityPattern(
        name="MD5 hash",
        pattern=re.compile(r'(hashlib\.md5|MD5\.new)\s*\('),
        security_type=SecurityType.WEAK_CRYPTO,
        severity="medium",
        message="MD5 is cryptographically broken",
        recommendation="Use SHA-256 or better for cryptographic purposes.",
    ),
    VulnerabilityPattern(
        name="SHA1 hash",
        pattern=re.compile(r'(hashlib\.sha1|SHA\.new)\s*\('),
        security_type=SecurityType.WEAK_CRYPTO,
        severity="medium",
        message="SHA-1 is deprecated for cryptographic use",
        recommendation="Use SHA-256 or better for cryptographic purposes.",
    ),
    VulnerabilityPattern(
        name="DES encryption",
        pattern=re.compile(r'(DES\.new|DES3\.new)\s*\('),
        security_type=SecurityType.WEAK_CRYPTO,
        severity="high",
        message="DES/3DES are deprecated encryption algorithms",
        recommendation="Use AES encryption instead.",
    ),
]

# SSL/TLS security patterns
SSL_PATTERNS = [
    VulnerabilityPattern(
        name="SSL verification disabled",
        pattern=re.compile(r'verify\s*=\s*False'),
        security_type=SecurityType.DISABLED_CERT_VERIFICATION,
        severity="high",
        message="SSL certificate verification is disabled",
        recommendation="Enable SSL certificate verification in production.",
    ),
    VulnerabilityPattern(
        name="Insecure SSL context",
        pattern=re.compile(r'ssl\.CERT_NONE'),
        security_type=SecurityType.INSECURE_SSL,
        severity="high",
        message="SSL certificate validation is disabled",
        recommendation="Use ssl.CERT_REQUIRED for proper certificate validation.",
    ),
    VulnerabilityPattern(
        name="SSLv2/SSLv3",
        pattern=re.compile(r'ssl\.(PROTOCOL_SSLv2|PROTOCOL_SSLv3)'),
        security_type=SecurityType.INSECURE_SSL,
        severity="critical",
        message="SSLv2/SSLv3 are deprecated and insecure",
        recommendation="Use TLS 1.2 or higher.",
    ),
]


class VulnerabilityCallCollector(cst.CSTVisitor):
    """Collect potentially vulnerable function calls using CST analysis."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._findings: list[SecurityFinding] = []

    def visit_Call(self, node: cst.Call) -> bool:
        """Check function calls for vulnerabilities."""
        # Get the function being called
        func_name = self._get_call_name(node)
        if not func_name:
            return True

        # Check for specific dangerous patterns
        self._check_eval_exec(node, func_name)
        self._check_subprocess(node, func_name)
        self._check_open(node, func_name)

        return True

    def _get_call_name(self, node: cst.Call) -> str | None:
        """Extract the full name of a function call."""
        if isinstance(node.func, cst.Name):
            return node.func.value
        elif isinstance(node.func, cst.Attribute):
            # Handle module.function pattern
            parts = []
            current = node.func
            while isinstance(current, cst.Attribute):
                parts.append(current.attr.value)
                current = current.value
            if isinstance(current, cst.Name):
                parts.append(current.value)
            return ".".join(reversed(parts))
        return None

    def _check_eval_exec(self, node: cst.Call, func_name: str) -> None:
        """Check for dangerous eval/exec usage."""
        if func_name not in ("eval", "exec"):
            return

        # Check if first argument is a variable (not a literal)
        if node.args:
            first_arg = node.args[0].value
            if isinstance(first_arg, cst.Name):
                self._findings.append(
                    SecurityFinding(
                        type=SecurityType.UNSAFE_EVAL if func_name == "eval" else SecurityType.UNSAFE_EXEC,
                        file_path=self._file_path,
                        line_number=0,  # Will be filled in later
                        name=func_name,
                        message=f"{func_name}() with variable input is dangerous",
                        severity="critical",
                        recommendation=f"Avoid {func_name}() with untrusted input.",
                    )
                )

    def _check_subprocess(self, node: cst.Call, func_name: str) -> None:
        """Check for dangerous subprocess usage."""
        if not func_name.startswith("subprocess."):
            return

        # Check for shell=True
        for arg in node.args:
            if arg.keyword and arg.keyword.value == "shell":
                if isinstance(arg.value, cst.Name) and arg.value.value == "True":
                    self._findings.append(
                        SecurityFinding(
                            type=SecurityType.SHELL_INJECTION,
                            file_path=self._file_path,
                            line_number=0,
                            name=func_name,
                            message="subprocess with shell=True is vulnerable to injection",
                            severity="high",
                            recommendation="Use shell=False and pass arguments as a list.",
                        )
                    )

    def _check_open(self, node: cst.Call, func_name: str) -> None:
        """Check for path traversal in file operations."""
        if func_name != "open":
            return

        # Check if first argument involves concatenation or formatting
        if node.args:
            first_arg = node.args[0].value
            if isinstance(first_arg, (cst.BinaryOperation, cst.FormattedString)):
                self._findings.append(
                    SecurityFinding(
                        type=SecurityType.PATH_TRAVERSAL,
                        file_path=self._file_path,
                        line_number=0,
                        name="open",
                        message="File path constructed dynamically may be vulnerable",
                        severity="medium",
                        recommendation="Validate file paths before opening.",
                    )
                )

    @property
    def findings(self) -> list[SecurityFinding]:
        return self._findings


class VulnerabilityScanner:
    """Scan for common security vulnerabilities.

    Detects SQL injection, command injection, unsafe deserialization,
    and other common vulnerability patterns.
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def _scan_patterns(
        self, patterns: list[VulnerabilityPattern]
    ) -> SecurityTargetList:
        """Scan files for patterns and return findings."""
        findings: list[SecurityTarget] = []

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                lines = content.splitlines()

                for pattern_def in patterns:
                    for match in pattern_def.pattern.finditer(content):
                        line_num = content[:match.start()].count("\n") + 1
                        line_content = lines[line_num - 1] if line_num <= len(lines) else ""

                        # Skip comments
                        stripped = line_content.strip()
                        if stripped.startswith("#"):
                            continue

                        finding = SecurityFinding(
                            type=pattern_def.security_type,
                            file_path=file_path,
                            line_number=line_num,
                            name=pattern_def.name,
                            message=pattern_def.message,
                            severity=pattern_def.severity,
                            code_snippet=line_content.strip()[:100],
                            recommendation=pattern_def.recommendation,
                        )
                        findings.append(SecurityTarget(self._rejig, finding))

            except Exception:
                continue

        return SecurityTargetList(self._rejig, findings)

    def find_sql_injection_risks(self) -> SecurityTargetList:
        """Find potential SQL injection vulnerabilities.

        Returns
        -------
        SecurityTargetList
            SQL injection risk findings.
        """
        return self._scan_patterns(SQL_INJECTION_PATTERNS)

    def find_shell_injection_risks(self) -> SecurityTargetList:
        """Find potential shell/command injection vulnerabilities.

        Returns
        -------
        SecurityTargetList
            Shell injection risk findings.
        """
        return self._scan_patterns(SHELL_INJECTION_PATTERNS)

    def find_unsafe_yaml_load(self) -> SecurityTargetList:
        """Find unsafe YAML loading.

        Returns
        -------
        SecurityTargetList
            Unsafe YAML load findings.
        """
        patterns = [p for p in UNSAFE_DESERIALIZATION_PATTERNS if "yaml" in p.name.lower()]
        return self._scan_patterns(patterns)

    def find_unsafe_pickle(self) -> SecurityTargetList:
        """Find unsafe pickle usage.

        Returns
        -------
        SecurityTargetList
            Unsafe pickle findings.
        """
        patterns = [p for p in UNSAFE_DESERIALIZATION_PATTERNS if "pickle" in p.name.lower()]
        return self._scan_patterns(patterns)

    def find_unsafe_deserialization(self) -> SecurityTargetList:
        """Find all unsafe deserialization patterns.

        Returns
        -------
        SecurityTargetList
            All unsafe deserialization findings.
        """
        return self._scan_patterns(UNSAFE_DESERIALIZATION_PATTERNS)

    def find_unsafe_eval(self) -> SecurityTargetList:
        """Find dangerous eval/exec usage.

        Returns
        -------
        SecurityTargetList
            Unsafe eval/exec findings.
        """
        return self._scan_patterns(EVAL_EXEC_PATTERNS)

    def find_path_traversal_risks(self) -> SecurityTargetList:
        """Find potential path traversal vulnerabilities.

        Returns
        -------
        SecurityTargetList
            Path traversal risk findings.
        """
        return self._scan_patterns(PATH_TRAVERSAL_PATTERNS)

    def find_insecure_random(self) -> SecurityTargetList:
        """Find insecure random number generation.

        Returns
        -------
        SecurityTargetList
            Insecure random findings.
        """
        return self._scan_patterns(INSECURE_RANDOM_PATTERNS)

    def find_weak_crypto(self) -> SecurityTargetList:
        """Find weak cryptography usage.

        Returns
        -------
        SecurityTargetList
            Weak cryptography findings.
        """
        return self._scan_patterns(WEAK_CRYPTO_PATTERNS)

    def find_insecure_ssl(self) -> SecurityTargetList:
        """Find insecure SSL/TLS configuration.

        Returns
        -------
        SecurityTargetList
            Insecure SSL findings.
        """
        return self._scan_patterns(SSL_PATTERNS)

    def find_all_vulnerabilities(self) -> SecurityTargetList:
        """Find all vulnerability patterns.

        Returns
        -------
        SecurityTargetList
            All vulnerability findings combined.
        """
        all_patterns = (
            SQL_INJECTION_PATTERNS
            + SHELL_INJECTION_PATTERNS
            + UNSAFE_DESERIALIZATION_PATTERNS
            + EVAL_EXEC_PATTERNS
            + PATH_TRAVERSAL_PATTERNS
            + INSECURE_RANDOM_PATTERNS
            + WEAK_CRYPTO_PATTERNS
            + SSL_PATTERNS
        )
        return self._scan_patterns(all_patterns)
