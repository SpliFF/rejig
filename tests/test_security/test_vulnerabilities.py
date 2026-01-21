"""
Tests for rejig.security.vulnerabilities module.

This module tests vulnerability detection:
- VulnerabilityPattern dataclass
- SQL/Shell injection patterns
- Unsafe deserialization patterns
- VulnerabilityScanner class
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from rejig import Rejig
from rejig.security.vulnerabilities import (
    EVAL_EXEC_PATTERNS,
    INSECURE_RANDOM_PATTERNS,
    PATH_TRAVERSAL_PATTERNS,
    SHELL_INJECTION_PATTERNS,
    SQL_INJECTION_PATTERNS,
    SSL_PATTERNS,
    UNSAFE_DESERIALIZATION_PATTERNS,
    WEAK_CRYPTO_PATTERNS,
    VulnerabilityPattern,
    VulnerabilityScanner,
)
from rejig.security.targets import SecurityType


# =============================================================================
# VulnerabilityPattern Tests
# =============================================================================

class TestVulnerabilityPattern:
    """Tests for VulnerabilityPattern dataclass."""

    def test_create_pattern(self):
        """Should create vulnerability pattern."""
        import re
        pattern = VulnerabilityPattern(
            name="Test Pattern",
            pattern=re.compile(r"test"),
            security_type=SecurityType.SQL_INJECTION,
            severity="critical",
            message="Test vulnerability",
            recommendation="Fix it",
        )
        assert pattern.name == "Test Pattern"
        assert pattern.severity == "critical"


# =============================================================================
# Pattern Constants Tests
# =============================================================================

class TestPatternConstants:
    """Tests for pattern constants."""

    def test_sql_injection_patterns_exist(self):
        """Should have SQL injection patterns."""
        assert len(SQL_INJECTION_PATTERNS) > 0
        for p in SQL_INJECTION_PATTERNS:
            assert p.security_type == SecurityType.SQL_INJECTION

    def test_shell_injection_patterns_exist(self):
        """Should have shell injection patterns."""
        assert len(SHELL_INJECTION_PATTERNS) > 0
        for p in SHELL_INJECTION_PATTERNS:
            assert p.security_type == SecurityType.SHELL_INJECTION

    def test_unsafe_deserialization_patterns_exist(self):
        """Should have unsafe deserialization patterns."""
        assert len(UNSAFE_DESERIALIZATION_PATTERNS) > 0

    def test_eval_exec_patterns_exist(self):
        """Should have eval/exec patterns."""
        assert len(EVAL_EXEC_PATTERNS) > 0

    def test_path_traversal_patterns_exist(self):
        """Should have path traversal patterns."""
        assert len(PATH_TRAVERSAL_PATTERNS) > 0

    def test_insecure_random_patterns_exist(self):
        """Should have insecure random patterns."""
        assert len(INSECURE_RANDOM_PATTERNS) > 0

    def test_weak_crypto_patterns_exist(self):
        """Should have weak crypto patterns."""
        assert len(WEAK_CRYPTO_PATTERNS) > 0

    def test_ssl_patterns_exist(self):
        """Should have SSL patterns."""
        assert len(SSL_PATTERNS) > 0


# =============================================================================
# VulnerabilityScanner Tests
# =============================================================================

class TestVulnerabilityScanner:
    """Tests for VulnerabilityScanner class."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_init(self, rejig: Rejig):
        """Should initialize with rejig instance."""
        scanner = VulnerabilityScanner(rejig)
        assert scanner._rejig is rejig

    # -------------------------------------------------------------------------
    # SQL Injection Detection
    # -------------------------------------------------------------------------

    def test_find_sql_injection_format(self, rejig: Rejig, tmp_path: Path):
        """Should find SQL injection via string format."""
        file_path = tmp_path / "db.py"
        file_path.write_text('cursor.execute("SELECT * FROM users WHERE id = %s" % (user_id,))')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_sql_injection_risks()

        assert len(findings) >= 1

    def test_find_sql_injection_fstring(self, rejig: Rejig, tmp_path: Path):
        """Should find SQL injection via f-string."""
        file_path = tmp_path / "db.py"
        file_path.write_text('cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_sql_injection_risks()

        assert len(findings) >= 1

    def test_find_sql_injection_concat(self, rejig: Rejig, tmp_path: Path):
        """Should find SQL injection via concatenation."""
        file_path = tmp_path / "db.py"
        file_path.write_text('cursor.execute("SELECT * FROM users WHERE id = " + user_id)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_sql_injection_risks()

        assert len(findings) >= 1

    def test_no_sql_injection_parameterized(self, rejig: Rejig, tmp_path: Path):
        """Should not flag parameterized queries."""
        file_path = tmp_path / "db.py"
        file_path.write_text('cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_sql_injection_risks()

        # Should not find injection in properly parameterized query
        assert len(findings) == 0

    # -------------------------------------------------------------------------
    # Shell Injection Detection
    # -------------------------------------------------------------------------

    def test_find_shell_injection_os_system(self, rejig: Rejig, tmp_path: Path):
        """Should find shell injection via os.system."""
        file_path = tmp_path / "cmd.py"
        file_path.write_text('os.system("ls -la " + user_input)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_shell_injection_risks()

        assert len(findings) >= 1

    def test_find_shell_injection_subprocess_shell(self, rejig: Rejig, tmp_path: Path):
        """Should find shell injection via subprocess with shell=True."""
        file_path = tmp_path / "cmd.py"
        file_path.write_text('subprocess.run(cmd, shell=True)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_shell_injection_risks()

        assert len(findings) >= 1

    def test_find_os_popen(self, rejig: Rejig, tmp_path: Path):
        """Should find os.popen usage."""
        file_path = tmp_path / "cmd.py"
        file_path.write_text('os.popen(command)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_shell_injection_risks()

        assert len(findings) >= 1

    # -------------------------------------------------------------------------
    # Unsafe Deserialization Detection
    # -------------------------------------------------------------------------

    def test_find_pickle_load(self, rejig: Rejig, tmp_path: Path):
        """Should find pickle.load usage."""
        file_path = tmp_path / "data.py"
        file_path.write_text('data = pickle.load(file)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_unsafe_pickle()

        assert len(findings) >= 1

    def test_find_pickle_loads(self, rejig: Rejig, tmp_path: Path):
        """Should find pickle.loads usage."""
        file_path = tmp_path / "data.py"
        file_path.write_text('data = pickle.loads(raw_data)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_unsafe_pickle()

        assert len(findings) >= 1

    def test_find_yaml_load_unsafe(self, rejig: Rejig, tmp_path: Path):
        """Should find unsafe yaml.load usage."""
        file_path = tmp_path / "config.py"
        file_path.write_text('config = yaml.load(data)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_unsafe_yaml_load()

        assert len(findings) >= 1

    def test_no_yaml_safe_load(self, rejig: Rejig, tmp_path: Path):
        """Should not flag yaml.safe_load."""
        file_path = tmp_path / "config.py"
        file_path.write_text('config = yaml.safe_load(data)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_unsafe_yaml_load()

        # safe_load should not be flagged
        assert len(findings) == 0

    # -------------------------------------------------------------------------
    # Eval/Exec Detection
    # -------------------------------------------------------------------------

    def test_find_eval_with_variable(self, rejig: Rejig, tmp_path: Path):
        """Should find eval with variable input."""
        file_path = tmp_path / "eval.py"
        file_path.write_text('result = eval(user_input)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_unsafe_eval()

        assert len(findings) >= 1

    def test_find_exec_with_variable(self, rejig: Rejig, tmp_path: Path):
        """Should find exec with variable input."""
        file_path = tmp_path / "exec.py"
        file_path.write_text('exec(code_string)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_unsafe_eval()

        assert len(findings) >= 1

    # -------------------------------------------------------------------------
    # Path Traversal Detection
    # -------------------------------------------------------------------------

    def test_find_open_fstring(self, rejig: Rejig, tmp_path: Path):
        """Should find open with f-string path."""
        file_path = tmp_path / "files.py"
        file_path.write_text('f = open(f"/data/{filename}")')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_path_traversal_risks()

        assert len(findings) >= 1

    def test_find_open_concat(self, rejig: Rejig, tmp_path: Path):
        """Should find open with path concatenation."""
        file_path = tmp_path / "files.py"
        file_path.write_text('f = open("/data/" + filename)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_path_traversal_risks()

        assert len(findings) >= 1

    # -------------------------------------------------------------------------
    # Insecure Random Detection
    # -------------------------------------------------------------------------

    def test_find_random_usage(self, rejig: Rejig, tmp_path: Path):
        """Should find random module usage."""
        file_path = tmp_path / "auth.py"
        file_path.write_text('token = random.random()')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_insecure_random()

        assert len(findings) >= 1

    def test_find_random_randint(self, rejig: Rejig, tmp_path: Path):
        """Should find random.randint usage."""
        file_path = tmp_path / "auth.py"
        file_path.write_text('code = random.randint(1000, 9999)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_insecure_random()

        assert len(findings) >= 1

    # -------------------------------------------------------------------------
    # Weak Crypto Detection
    # -------------------------------------------------------------------------

    def test_find_md5_usage(self, rejig: Rejig, tmp_path: Path):
        """Should find MD5 usage."""
        file_path = tmp_path / "crypto.py"
        file_path.write_text('h = hashlib.md5(data)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_weak_crypto()

        assert len(findings) >= 1

    def test_find_sha1_usage(self, rejig: Rejig, tmp_path: Path):
        """Should find SHA1 usage."""
        file_path = tmp_path / "crypto.py"
        file_path.write_text('h = hashlib.sha1(data)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_weak_crypto()

        assert len(findings) >= 1

    # -------------------------------------------------------------------------
    # SSL/TLS Detection
    # -------------------------------------------------------------------------

    def test_find_verify_false(self, rejig: Rejig, tmp_path: Path):
        """Should find verify=False."""
        file_path = tmp_path / "http.py"
        file_path.write_text('requests.get(url, verify=False)')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_insecure_ssl()

        assert len(findings) >= 1

    def test_find_cert_none(self, rejig: Rejig, tmp_path: Path):
        """Should find ssl.CERT_NONE."""
        file_path = tmp_path / "ssl_config.py"
        file_path.write_text('ctx.verify_mode = ssl.CERT_NONE')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_insecure_ssl()

        assert len(findings) >= 1

    # -------------------------------------------------------------------------
    # Find All Vulnerabilities
    # -------------------------------------------------------------------------

    def test_find_all_vulnerabilities(self, rejig: Rejig, tmp_path: Path):
        """Should find all vulnerability types."""
        file_path = tmp_path / "vulnerable.py"
        file_path.write_text(textwrap.dedent('''
            import os
            import pickle
            import hashlib

            cursor.execute(f"SELECT * FROM {table}")
            os.system("ls " + path)
            data = pickle.load(file)
            h = hashlib.md5(data)
        '''))

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_all_vulnerabilities()

        # Should find multiple vulnerability types
        assert len(findings) >= 3

    def test_empty_project(self, rejig: Rejig, tmp_path: Path):
        """Should handle empty project."""
        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_all_vulnerabilities()

        assert len(findings) == 0

    def test_skip_comments(self, rejig: Rejig, tmp_path: Path):
        """Should skip patterns in comments."""
        file_path = tmp_path / "code.py"
        file_path.write_text('# cursor.execute(f"SELECT * FROM {table}")')

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_sql_injection_risks()

        assert len(findings) == 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for vulnerabilities module."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    def test_scan_real_web_app(self, rejig: Rejig, tmp_path: Path):
        """Should scan realistic web app code."""
        # Create project structure
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "views.py").write_text(textwrap.dedent('''
            def get_user(request):
                user_id = request.GET.get("id")
                cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
                return cursor.fetchone()
        '''))
        (tmp_path / "app" / "utils.py").write_text(textwrap.dedent('''
            def run_command(cmd):
                return os.system(cmd)
        '''))

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_all_vulnerabilities()

        # Should find multiple vulnerabilities
        assert len(findings) >= 1

    def test_severity_filtering(self, rejig: Rejig, tmp_path: Path):
        """Should properly set severity levels."""
        file_path = tmp_path / "code.py"
        file_path.write_text(textwrap.dedent('''
            cursor.execute(f"SELECT * FROM {table}")
            data = pickle.load(file)
        '''))

        scanner = VulnerabilityScanner(rejig)
        findings = scanner.find_all_vulnerabilities()

        # Check severity is set
        for finding in findings:
            assert finding.severity in ["low", "medium", "high", "critical"]
