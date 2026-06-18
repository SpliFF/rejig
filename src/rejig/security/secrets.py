"""Hardcoded secrets detection.

Detects hardcoded credentials and sensitive information:
- API keys (AWS, Google, GitHub, etc.)
- Passwords and authentication tokens
- Private keys and certificates
- Database connection strings
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
class SecretPattern:
    """Pattern for detecting a specific type of secret.

    Attributes
    ----------
    name : str
        Name of the secret type.
    pattern : re.Pattern
        Compiled regex pattern.
    security_type : SecurityType
        Type of security finding.
    severity : str
        Severity level.
    recommendation : str
        Suggested fix.
    """

    name: str
    pattern: re.Pattern
    security_type: SecurityType
    severity: str
    recommendation: str


# Common secret patterns
SECRET_PATTERNS = [
    # AWS
    SecretPattern(
        name="AWS Access Key ID",
        pattern=re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),
        security_type=SecurityType.HARDCODED_API_KEY,
        severity="critical",
        recommendation="Use environment variables or AWS IAM roles instead of hardcoded credentials.",
    ),
    SecretPattern(
        name="AWS Secret Access Key",
        pattern=re.compile(r"['\"][0-9a-zA-Z/+]{40}['\"]"),
        security_type=SecurityType.HARDCODED_SECRET,
        severity="critical",
        recommendation="Store AWS credentials in environment variables or use IAM roles.",
    ),
    # Google Cloud
    SecretPattern(
        name="Google API Key",
        pattern=re.compile(r"AIza[0-9A-Za-z_-]{35}"),
        security_type=SecurityType.HARDCODED_API_KEY,
        severity="high",
        recommendation="Use environment variables or Google Cloud Secret Manager.",
    ),
    SecretPattern(
        name="Google OAuth Token",
        pattern=re.compile(r"ya29\.[0-9A-Za-z_-]+"),
        security_type=SecurityType.HARDCODED_TOKEN,
        severity="high",
        recommendation="Never hardcode OAuth tokens. Use proper OAuth flow.",
    ),
    # GitHub
    SecretPattern(
        name="GitHub Token",
        pattern=re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}"),
        security_type=SecurityType.HARDCODED_TOKEN,
        severity="critical",
        recommendation="Use environment variables or GitHub Secrets for tokens.",
    ),
    SecretPattern(
        name="GitHub OAuth",
        pattern=re.compile(r"gho_[A-Za-z0-9_]{36,}"),
        security_type=SecurityType.HARDCODED_TOKEN,
        severity="critical",
        recommendation="Never hardcode GitHub OAuth tokens.",
    ),
    # Slack
    SecretPattern(
        name="Slack Token",
        pattern=re.compile(r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*"),
        security_type=SecurityType.HARDCODED_TOKEN,
        severity="high",
        recommendation="Use environment variables for Slack tokens.",
    ),
    SecretPattern(
        name="Slack Webhook",
        pattern=re.compile(r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+"),
        security_type=SecurityType.HARDCODED_SECRET,
        severity="high",
        recommendation="Store webhook URLs in environment variables.",
    ),
    # Stripe
    SecretPattern(
        name="Stripe API Key",
        pattern=re.compile(r"sk_live_[0-9a-zA-Z]{24,}"),
        security_type=SecurityType.HARDCODED_API_KEY,
        severity="critical",
        recommendation="Use environment variables for Stripe API keys.",
    ),
    SecretPattern(
        name="Stripe Test Key",
        pattern=re.compile(r"sk_test_[0-9a-zA-Z]{24,}"),
        security_type=SecurityType.HARDCODED_API_KEY,
        severity="medium",
        recommendation="Even test keys should be in environment variables.",
    ),
    # Generic patterns
    SecretPattern(
        name="Private Key",
        pattern=re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
        security_type=SecurityType.HARDCODED_SECRET,
        severity="critical",
        recommendation="Store private keys in secure key management systems, not in code.",
    ),
    SecretPattern(
        name="Generic API Key",
        pattern=re.compile(r"['\"][a-zA-Z0-9]{32,}['\"]"),
        security_type=SecurityType.HARDCODED_API_KEY,
        severity="medium",
        recommendation="Move API keys to environment variables.",
    ),
    SecretPattern(
        name="JWT Token",
        pattern=re.compile(r"eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+"),
        security_type=SecurityType.HARDCODED_TOKEN,
        severity="high",
        recommendation="Never hardcode JWT tokens. Generate them dynamically.",
    ),
    # Password patterns
    SecretPattern(
        name="Password Assignment",
        pattern=re.compile(r"password\s*=\s*['\"][^'\"]{4,}['\"]", re.IGNORECASE),
        security_type=SecurityType.HARDCODED_PASSWORD,
        severity="high",
        recommendation="Use environment variables or secure vaults for passwords.",
    ),
    SecretPattern(
        name="Secret Key Assignment",
        pattern=re.compile(r"secret[_-]?key\s*=\s*['\"][^'\"]{8,}['\"]", re.IGNORECASE),
        security_type=SecurityType.HARDCODED_SECRET,
        severity="high",
        recommendation="Store secret keys in environment variables.",
    ),
    # Database URLs
    SecretPattern(
        name="Database URL with Password",
        pattern=re.compile(r"(postgres|mysql|mongodb)://[^:]+:[^@]+@[^/]+"),
        security_type=SecurityType.HARDCODED_PASSWORD,
        severity="critical",
        recommendation="Use environment variables for database connection strings.",
    ),
    # Heroku
    SecretPattern(
        name="Heroku API Key",
        pattern=re.compile(r"[hH]eroku.*['\"][0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}['\"]"),
        security_type=SecurityType.HARDCODED_API_KEY,
        severity="high",
        recommendation="Use environment variables for Heroku API keys.",
    ),
    # SendGrid
    SecretPattern(
        name="SendGrid API Key",
        pattern=re.compile(r"SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}"),
        security_type=SecurityType.HARDCODED_API_KEY,
        severity="high",
        recommendation="Store SendGrid API keys in environment variables.",
    ),
    # Twilio
    SecretPattern(
        name="Twilio API Key",
        pattern=re.compile(r"SK[0-9a-fA-F]{32}"),
        security_type=SecurityType.HARDCODED_API_KEY,
        severity="high",
        recommendation="Use environment variables for Twilio credentials.",
    ),
    # Discord
    SecretPattern(
        name="Discord Token",
        pattern=re.compile(r"[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27}"),
        security_type=SecurityType.HARDCODED_TOKEN,
        severity="high",
        recommendation="Store Discord tokens securely, not in code.",
    ),
]

# Variable names that suggest secrets
SECRET_VAR_NAMES = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "secret_key",
    "secretkey",
    "api_key",
    "apikey",
    "api_secret",
    "apisecret",
    "auth_token",
    "authtoken",
    "access_token",
    "accesstoken",
    "private_key",
    "privatekey",
    "db_password",
    "database_password",
    "encryption_key",
    "encryptionkey",
    "signing_key",
    "signingkey",
    "client_secret",
    "clientsecret",
    "bearer_token",
    "bearertoken",
}

# Files that typically contain secrets (should be ignored or checked carefully)
SENSITIVE_FILE_PATTERNS = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "secrets.json",
    "config.json",
    ".credentials",
}


class SecretAssignmentCollector(cst.CSTVisitor):
    """Collect suspicious secret assignments from code."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._findings: list[tuple[str, str, int, str]] = []  # (var_name, value, line, context)
        self._in_class = False
        self._class_name: str | None = None

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        self._in_class = True
        self._class_name = node.name.value
        return True

    def leave_ClassDef(self, node: cst.ClassDef) -> None:
        self._in_class = False
        self._class_name = None

    def visit_Assign(self, node: cst.Assign) -> bool:
        # Get variable name(s)
        for target in node.targets:
            if isinstance(target.target, cst.Name):
                var_name = target.target.value.lower()
                self._check_assignment(var_name, node.value, "assign")
            elif isinstance(target.target, cst.Attribute):
                # Handle self.password = "..."
                attr = target.target
                if isinstance(attr.value, cst.Name) and attr.value.value == "self":
                    var_name = attr.attr.value.lower()
                    self._check_assignment(var_name, node.value, "attribute")
        return False

    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:
        if node.value and isinstance(node.target, cst.Name):
            var_name = node.target.value.lower()
            self._check_assignment(var_name, node.value, "ann_assign")
        return False

    def _check_assignment(self, var_name: str, value: cst.BaseExpression, context: str) -> None:
        """Check if an assignment looks like a hardcoded secret."""
        # Check if variable name suggests a secret
        is_secret_name = any(
            secret_name in var_name for secret_name in SECRET_VAR_NAMES
        )

        if not is_secret_name:
            return

        # Get the string value if it's a string literal
        if isinstance(value, cst.SimpleString):
            string_val = value.value
            # Strip quotes
            if string_val.startswith(('"""', "'''")):
                content = string_val[3:-3]
            else:
                content = string_val[1:-1]

            # Skip empty strings and placeholders
            if not content or content in ("", "None", "null", "undefined"):
                return
            if content.startswith(("$", "{", "ENV[")):
                return  # Likely environment variable reference
            if len(content) < 4:
                return  # Too short to be a real secret

            self._findings.append((var_name, content, 0, context))

    @property
    def findings(self) -> list[tuple[str, str, int, str]]:
        return self._findings


class SecretsScanner:
    """Scan for hardcoded secrets and credentials.

    Detects various types of hardcoded sensitive information
    using pattern matching and heuristics.
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def find_hardcoded_secrets(self) -> SecurityTargetList:
        """Find all hardcoded secrets in the codebase.

        Returns
        -------
        SecurityTargetList
            All hardcoded secrets found.
        """
        findings: list[SecurityTarget] = []

        for file_path in self._rejig.files:
            try:
                content = file_path.read_text()
                lines = content.splitlines()

                # Check each pattern against the file content
                for pattern_def in SECRET_PATTERNS:
                    for match in pattern_def.pattern.finditer(content):
                        # Find line number
                        line_start = content[:match.start()].count("\n") + 1
                        line_content = lines[line_start - 1] if line_start <= len(lines) else ""

                        # Skip if this looks like a false positive
                        if self._is_false_positive(match.group(), line_content, file_path):
                            continue

                        finding = SecurityFinding(
                            type=pattern_def.security_type,
                            file_path=file_path,
                            line_number=line_start,
                            name=pattern_def.name,
                            message=f"Potential {pattern_def.name} found",
                            severity=pattern_def.severity,
                            code_snippet=line_content.strip()[:100],
                            recommendation=pattern_def.recommendation,
                        )
                        findings.append(SecurityTarget(self._rejig, finding))

                # Also check for suspicious variable assignments
                findings.extend(self._scan_variable_assignments(file_path, content, lines))

            except Exception:
                continue

        return SecurityTargetList(self._rejig, findings)

    def _scan_variable_assignments(
        self, file_path: Path, content: str, lines: list[str]
    ) -> list[SecurityTarget]:
        """Scan for suspicious secret variable assignments."""
        findings: list[SecurityTarget] = []

        try:
            tree = cst.parse_module(content)
            wrapper = cst.MetadataWrapper(tree)
            collector = SecretAssignmentCollector(file_path)
            wrapper.visit(collector)

            for var_name, value, _, context in collector.findings:
                # Find the line number
                search_pattern = f"{var_name}"
                line_num = 1
                for i, line in enumerate(lines, 1):
                    if search_pattern in line.lower() and ("=" in line or ":" in line):
                        line_num = i
                        break

                line_content = lines[line_num - 1] if line_num <= len(lines) else ""

                # Skip false positives
                if self._is_false_positive(value, line_content, file_path):
                    continue

                finding = SecurityFinding(
                    type=SecurityType.HARDCODED_SECRET,
                    file_path=file_path,
                    line_number=line_num,
                    name=var_name,
                    message=f"Potential hardcoded secret in variable '{var_name}'",
                    severity="high",
                    code_snippet=lines[line_num - 1].strip()[:100] if line_num <= len(lines) else "",
                    recommendation="Move secrets to environment variables or a secure vault.",
                )
                findings.append(SecurityTarget(self._rejig, finding))

        except Exception:
            pass

        return findings

    def _is_false_positive(self, match: str, line: str, file_path: Path) -> bool:
        """Check if a match is likely a false positive."""
        # Skip test files (check filename, not full path)
        filename = file_path.name.lower()
        if filename.startswith("test_") or filename.endswith("_test.py") or filename == "conftest.py":
            return True

        # Skip example/sample files (check filename, not full path)
        if any(x in filename for x in ["example", "sample", "mock", "fixture"]):
            return True

        # Skip if it's in a comment
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            return True

        # Skip obviously fake values
        fake_values = [
            "xxx", "yyy", "zzz", "aaa", "bbb",
            "your_", "my_", "test_", "fake_",
            "example", "placeholder", "changeme",
            "todo", "fixme", "replace_",
        ]
        match_lower = match.lower()
        if any(fake in match_lower for fake in fake_values):
            return True

        return False

    def find_api_keys(self) -> SecurityTargetList:
        """Find hardcoded API keys specifically.

        Returns
        -------
        SecurityTargetList
            API key findings.
        """
        all_findings = self.find_hardcoded_secrets()
        return all_findings.by_type(SecurityType.HARDCODED_API_KEY)

    def find_passwords(self) -> SecurityTargetList:
        """Find hardcoded passwords specifically.

        Returns
        -------
        SecurityTargetList
            Password findings.
        """
        all_findings = self.find_hardcoded_secrets()
        return all_findings.by_type(SecurityType.HARDCODED_PASSWORD)

    def find_tokens(self) -> SecurityTargetList:
        """Find hardcoded tokens specifically.

        Returns
        -------
        SecurityTargetList
            Token findings.
        """
        all_findings = self.find_hardcoded_secrets()
        return all_findings.by_type(SecurityType.HARDCODED_TOKEN)
