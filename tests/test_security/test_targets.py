"""
Tests for rejig.security.targets module.

This module tests security target classes:
- SecurityType enum
- SecurityFinding dataclass
- SecurityTarget class
- SecurityTargetList class
"""
from __future__ import annotations

from pathlib import Path

import pytest

from rejig import Rejig
from rejig.security.targets import (
    SecurityFinding,
    SecurityTarget,
    SecurityTargetList,
    SecurityType,
)


# =============================================================================
# SecurityType Enum Tests
# =============================================================================

class TestSecurityType:
    """Tests for SecurityType enum."""

    def test_has_secret_types(self):
        """Should have secret-related types."""
        assert SecurityType.HARDCODED_SECRET
        assert SecurityType.HARDCODED_API_KEY
        assert SecurityType.HARDCODED_PASSWORD
        assert SecurityType.HARDCODED_TOKEN

    def test_has_injection_types(self):
        """Should have injection-related types."""
        assert SecurityType.SQL_INJECTION
        assert SecurityType.SHELL_INJECTION
        assert SecurityType.COMMAND_INJECTION
        assert SecurityType.CODE_INJECTION

    def test_has_unsafe_operation_types(self):
        """Should have unsafe operation types."""
        assert SecurityType.UNSAFE_YAML_LOAD
        assert SecurityType.UNSAFE_PICKLE
        assert SecurityType.UNSAFE_EVAL
        assert SecurityType.UNSAFE_EXEC
        assert SecurityType.UNSAFE_DESERIALIZE

    def test_has_crypto_types(self):
        """Should have cryptography-related types."""
        assert SecurityType.INSECURE_RANDOM
        assert SecurityType.WEAK_CRYPTO
        assert SecurityType.HARDCODED_CRYPTO_KEY

    def test_has_network_types(self):
        """Should have network security types."""
        assert SecurityType.INSECURE_SSL
        assert SecurityType.DISABLED_CERT_VERIFICATION


# =============================================================================
# SecurityFinding Dataclass Tests
# =============================================================================

class TestSecurityFinding:
    """Tests for SecurityFinding dataclass."""

    def test_create_basic_finding(self):
        """Should create a basic finding."""
        finding = SecurityFinding(
            type=SecurityType.HARDCODED_SECRET,
            file_path=Path("/test/file.py"),
            line_number=10,
        )
        assert finding.type == SecurityType.HARDCODED_SECRET
        assert finding.file_path == Path("/test/file.py")
        assert finding.line_number == 10

    def test_finding_with_all_fields(self):
        """Should create finding with all fields."""
        finding = SecurityFinding(
            type=SecurityType.SQL_INJECTION,
            file_path=Path("/app/models.py"),
            line_number=42,
            name="execute_query",
            message="Potential SQL injection via string formatting",
            severity="critical",
            code_snippet="cursor.execute(f'SELECT * FROM {table}')",
            recommendation="Use parameterized queries",
        )
        assert finding.name == "execute_query"
        assert finding.message == "Potential SQL injection via string formatting"
        assert finding.severity == "critical"
        assert finding.code_snippet == "cursor.execute(f'SELECT * FROM {table}')"
        assert finding.recommendation == "Use parameterized queries"

    def test_finding_defaults(self):
        """Should have reasonable defaults."""
        finding = SecurityFinding(
            type=SecurityType.HARDCODED_SECRET,
            file_path=Path("/test.py"),
            line_number=1,
        )
        assert finding.name is None
        assert finding.message == ""
        assert finding.severity == "medium"
        assert finding.code_snippet is None
        assert finding.context == {}
        assert finding.recommendation is None

    def test_location_property(self):
        """Should return formatted location string."""
        finding = SecurityFinding(
            type=SecurityType.HARDCODED_SECRET,
            file_path=Path("/app/config.py"),
            line_number=25,
        )
        assert finding.location == "/app/config.py:25"


# =============================================================================
# SecurityTarget Tests
# =============================================================================

class TestSecurityTarget:
    """Tests for SecurityTarget class."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def sample_finding(self, tmp_path: Path) -> SecurityFinding:
        """Create a sample finding."""
        file_path = tmp_path / "test.py"
        file_path.write_text("password = 'secret123'")
        return SecurityFinding(
            type=SecurityType.HARDCODED_PASSWORD,
            file_path=file_path,
            line_number=1,
            name="password",
            message="Hardcoded password found",
            severity="high",
            code_snippet="password = 'secret123'",
        )

    def test_create_security_target(self, rejig: Rejig, sample_finding: SecurityFinding):
        """Should create SecurityTarget from finding."""
        target = SecurityTarget(rejig, sample_finding)
        assert target.finding == sample_finding

    def test_target_properties(self, rejig: Rejig, sample_finding: SecurityFinding):
        """Should expose finding properties."""
        target = SecurityTarget(rejig, sample_finding)
        assert target.file_path == sample_finding.file_path
        assert target.line_number == sample_finding.line_number
        assert target.name == sample_finding.name
        assert target.type == sample_finding.type
        assert target.message == sample_finding.message
        assert target.severity == sample_finding.severity
        assert target.code_snippet == sample_finding.code_snippet

    def test_exists(self, rejig: Rejig, sample_finding: SecurityFinding):
        """Should check if file exists."""
        target = SecurityTarget(rejig, sample_finding)
        assert target.exists() is True

    def test_exists_missing_file(self, rejig: Rejig, tmp_path: Path):
        """Should return False for missing file."""
        finding = SecurityFinding(
            type=SecurityType.HARDCODED_SECRET,
            file_path=tmp_path / "missing.py",
            line_number=1,
        )
        target = SecurityTarget(rejig, finding)
        assert target.exists() is False

    def test_location(self, rejig: Rejig, sample_finding: SecurityFinding):
        """Should return location string."""
        target = SecurityTarget(rejig, sample_finding)
        assert target.location == sample_finding.location

    def test_repr(self, rejig: Rejig, sample_finding: SecurityFinding):
        """Should have useful repr."""
        target = SecurityTarget(rejig, sample_finding)
        repr_str = repr(target)
        assert "SecurityTarget" in repr_str
        assert "HARDCODED_PASSWORD" in repr_str


# =============================================================================
# SecurityTargetList Tests
# =============================================================================

class TestSecurityTargetList:
    """Tests for SecurityTargetList class."""

    @pytest.fixture
    def rejig(self, tmp_path: Path) -> Rejig:
        """Create a Rejig instance."""
        return Rejig(str(tmp_path))

    @pytest.fixture
    def sample_targets(self, rejig: Rejig, tmp_path: Path) -> SecurityTargetList:
        """Create sample targets."""
        file1 = tmp_path / "config.py"
        file1.write_text("")
        file2 = tmp_path / "views.py"
        file2.write_text("")

        findings = [
            SecurityFinding(
                type=SecurityType.HARDCODED_PASSWORD,
                file_path=file1,
                line_number=1,
                severity="critical",
            ),
            SecurityFinding(
                type=SecurityType.HARDCODED_API_KEY,
                file_path=file1,
                line_number=5,
                severity="high",
            ),
            SecurityFinding(
                type=SecurityType.SQL_INJECTION,
                file_path=file2,
                line_number=10,
                severity="critical",
            ),
            SecurityFinding(
                type=SecurityType.INSECURE_RANDOM,
                file_path=file2,
                line_number=15,
                severity="medium",
            ),
        ]
        targets = [SecurityTarget(rejig, f) for f in findings]
        return SecurityTargetList(rejig, targets)

    def test_create_empty_list(self, rejig: Rejig):
        """Should create empty list."""
        target_list = SecurityTargetList(rejig)
        assert len(target_list) == 0

    def test_create_with_targets(self, sample_targets: SecurityTargetList):
        """Should create list with targets."""
        assert len(sample_targets) == 4

    def test_by_type(self, sample_targets: SecurityTargetList):
        """Should filter by type."""
        passwords = sample_targets.by_type(SecurityType.HARDCODED_PASSWORD)
        assert len(passwords) == 1

    def test_by_types(self, sample_targets: SecurityTargetList):
        """Should filter by multiple types."""
        secrets = sample_targets.by_types(
            SecurityType.HARDCODED_PASSWORD,
            SecurityType.HARDCODED_API_KEY,
        )
        assert len(secrets) == 2

    def test_by_severity(self, sample_targets: SecurityTargetList):
        """Should filter by severity."""
        critical = sample_targets.by_severity("critical")
        assert len(critical) == 2

    def test_critical(self, sample_targets: SecurityTargetList):
        """Should filter to critical findings."""
        critical = sample_targets.critical()
        assert len(critical) == 2
        for t in critical:
            assert t.severity == "critical"

    def test_high(self, sample_targets: SecurityTargetList):
        """Should filter to high findings."""
        high = sample_targets.high()
        assert len(high) == 1

    def test_medium(self, sample_targets: SecurityTargetList):
        """Should filter to medium findings."""
        medium = sample_targets.medium()
        assert len(medium) == 1

    def test_at_least(self, sample_targets: SecurityTargetList):
        """Should filter to at least severity."""
        at_least_high = sample_targets.at_least("high")
        assert len(at_least_high) == 3  # 2 critical + 1 high

    def test_in_file(self, sample_targets: SecurityTargetList, tmp_path: Path):
        """Should filter to specific file."""
        config_findings = sample_targets.in_file(tmp_path / "config.py")
        assert len(config_findings) == 2

    def test_in_directory(self, sample_targets: SecurityTargetList, tmp_path: Path):
        """Should filter to directory."""
        all_findings = sample_targets.in_directory(tmp_path)
        assert len(all_findings) == 4

    def test_secrets_shortcut(self, sample_targets: SecurityTargetList):
        """Should filter to secret types."""
        secrets = sample_targets.secrets()
        assert len(secrets) == 2

    def test_injection_risks_shortcut(self, sample_targets: SecurityTargetList):
        """Should filter to injection types."""
        injections = sample_targets.injection_risks()
        assert len(injections) == 1

    def test_group_by_file(self, sample_targets: SecurityTargetList, tmp_path: Path):
        """Should group by file."""
        by_file = sample_targets.group_by_file()
        assert len(by_file) == 2
        assert tmp_path / "config.py" in by_file
        assert tmp_path / "views.py" in by_file

    def test_group_by_type(self, sample_targets: SecurityTargetList):
        """Should group by type."""
        by_type = sample_targets.group_by_type()
        assert len(by_type) == 4

    def test_group_by_severity(self, sample_targets: SecurityTargetList):
        """Should group by severity."""
        by_severity = sample_targets.group_by_severity()
        assert "critical" in by_severity
        assert "high" in by_severity
        assert "medium" in by_severity

    def test_count_by_type(self, sample_targets: SecurityTargetList):
        """Should count by type."""
        counts = sample_targets.count_by_type()
        assert counts[SecurityType.HARDCODED_PASSWORD] == 1
        assert counts[SecurityType.SQL_INJECTION] == 1

    def test_count_by_severity(self, sample_targets: SecurityTargetList):
        """Should count by severity."""
        counts = sample_targets.count_by_severity()
        assert counts["critical"] == 2
        assert counts["high"] == 1
        assert counts["medium"] == 1

    def test_sorted_by_severity(self, sample_targets: SecurityTargetList):
        """Should sort by severity."""
        sorted_list = sample_targets.sorted_by_severity()
        assert len(sorted_list) == 4
        # Critical should be first
        assert sorted_list[0].severity == "critical"
        assert sorted_list[1].severity == "critical"

    def test_sorted_by_location(self, sample_targets: SecurityTargetList):
        """Should sort by location."""
        sorted_list = sample_targets.sorted_by_location()
        assert len(sorted_list) == 4

    def test_to_list_of_dicts(self, sample_targets: SecurityTargetList):
        """Should convert to list of dicts."""
        dicts = sample_targets.to_list_of_dicts()
        assert len(dicts) == 4
        assert "type" in dicts[0]
        assert "file" in dicts[0]
        assert "severity" in dicts[0]

    def test_summary(self, sample_targets: SecurityTargetList):
        """Should generate summary."""
        summary = sample_targets.summary()
        assert "4 security findings" in summary
        assert "CRITICAL" in summary

    def test_summary_empty_list(self, rejig: Rejig):
        """Should handle empty list summary."""
        target_list = SecurityTargetList(rejig)
        summary = target_list.summary()
        assert "No security findings" in summary

    def test_repr(self, sample_targets: SecurityTargetList):
        """Should have useful repr."""
        repr_str = repr(sample_targets)
        assert "SecurityTargetList" in repr_str
        assert "4" in repr_str
