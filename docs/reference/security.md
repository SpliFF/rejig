# Security Reference

Reference for security scanning types and findings.

## SecurityType Enum

Types of security issues detected.

### Hardcoded Secrets

| Type | Description |
|------|-------------|
| `HARDCODED_SECRET` | Generic secret detection |
| `HARDCODED_API_KEY` | API keys (AWS, Google, Stripe, etc.) |
| `HARDCODED_PASSWORD` | Password strings in code |
| `HARDCODED_TOKEN` | Auth tokens, JWT secrets, bearer tokens |
| `HARDCODED_CRYPTO_KEY` | Encryption/decryption keys |

### Injection Vulnerabilities

| Type | Description |
|------|-------------|
| `SQL_INJECTION` | SQL query string concatenation |
| `COMMAND_INJECTION` | Shell command string building |
| `SHELL_INJECTION` | subprocess with shell=True |
| `CODE_INJECTION` | Dynamic code execution risks |

### Unsafe Operations

| Type | Description |
|------|-------------|
| `UNSAFE_YAML_LOAD` | yaml.load without safe loader |
| `UNSAFE_PICKLE` | pickle.load on potentially untrusted data |
| `UNSAFE_EVAL` | eval() on user input or dynamic strings |
| `UNSAFE_EXEC` | exec() on dynamic code |
| `UNSAFE_DESERIALIZE` | Other insecure deserialization |

### Path and File Issues

| Type | Description |
|------|-------------|
| `PATH_TRAVERSAL` | Unsanitized path construction |
| `INSECURE_FILE_PERMISSIONS` | chmod with overly permissive mode |

### Cryptography Issues

| Type | Description |
|------|-------------|
| `INSECURE_RANDOM` | random module for security purposes |
| `WEAK_CRYPTO` | MD5, SHA1, DES, or other weak algorithms |

### Network Issues

| Type | Description |
|------|-------------|
| `INSECURE_SSL` | SSL verification disabled |
| `DISABLED_CERT_VERIFICATION` | verify=False in requests |

### Other Issues

| Type | Description |
|------|-------------|
| `DEBUG_CODE` | Debug statements in production code |
| `SENSITIVE_DATA_EXPOSURE` | Logging sensitive data |

## SecurityFinding

Dataclass representing a security finding.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `type` | `SecurityType` | Type of issue |
| `file_path` | `Path` | File containing the issue |
| `line_number` | `int` | Line number (1-indexed) |
| `name` | `str` | Name of the pattern matched |
| `message` | `str` | Human-readable description |
| `severity` | `str` | "critical", "high", "medium", or "low" |
| `code_snippet` | `str` | The problematic code |
| `context` | `dict` | Additional context |

## SecurityTarget

Target wrapping a security finding.

### Properties

All properties from `SecurityFinding` plus:

| Property | Type | Description |
|----------|------|-------------|
| `finding` | `SecurityFinding` | The underlying finding |

### Navigation Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `to_file_target()` | `FileTarget` | Get file containing issue |
| `to_line_target()` | `LineTarget` | Get line with issue |

## SecurityTargetList

List of security findings with filtering and aggregation.

### Severity Shortcuts

| Method | Returns | Description |
|--------|---------|-------------|
| `critical()` | `SecurityTargetList` | Critical severity only |
| `high()` | `SecurityTargetList` | High severity only |
| `medium()` | `SecurityTargetList` | Medium severity only |
| `low()` | `SecurityTargetList` | Low severity only |

### Filtering

| Method | Description |
|--------|-------------|
| `by_type(type)` | Filter by single type |
| `by_types(types)` | Filter by multiple types |
| `by_severity(severity)` | Filter by severity level |
| `in_file(path)` | Filter by file path |
| `in_directory(path)` | Filter by directory |

### Aggregation

| Method | Returns | Description |
|--------|---------|-------------|
| `group_by_file()` | `dict[Path, list]` | Group by file |
| `group_by_type()` | `dict[str, list]` | Group by type |
| `count_by_type()` | `dict[str, int]` | Count per type |
| `count_by_severity()` | `dict[str, int]` | Count per severity |

### Output

| Method | Returns | Description |
|--------|---------|-------------|
| `summary()` | `str` | Summary string |
| `to_list_of_dicts()` | `list[dict]` | Export as dicts |

## Scanners

### SecretsScanner

Scan for hardcoded secrets.

```python
from rejig import Rejig, SecretsScanner

rj = Rejig("src/")
scanner = SecretsScanner(rj)

# Find all secrets
secrets = scanner.find_all()

# Add custom pattern
scanner.add_pattern(
    name="internal_key",
    pattern=r"INTERNAL_[A-Z]+_KEY\s*=\s*['\"][^'\"]+['\"]",
    severity="high",
)

# Scan again
secrets = scanner.find_all()
```

### VulnerabilityScanner

Scan for vulnerability patterns.

```python
from rejig import Rejig, VulnerabilityScanner

rj = Rejig("src/")
scanner = VulnerabilityScanner(rj)

# Find specific vulnerability types
sql = scanner.find_sql_injection()
cmd = scanner.find_command_injection()
yaml = scanner.find_unsafe_yaml()
pickle = scanner.find_unsafe_pickle()
eval_exec = scanner.find_unsafe_eval()

# Find all unsafe operations
unsafe = scanner.find_unsafe_operations()
```

## SecurityConfig

Configuration for security scanning.

### Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `ignore_files` | `list[str]` | `[]` | Glob patterns to ignore |
| `ignore_patterns` | `list[str]` | `[]` | Regex patterns to ignore |
| `ignore_line_patterns` | `list[str]` | `["# nosec"]` | Line-level ignores |
| `min_severity` | `str` | `"low"` | Minimum severity to report |
| `severity_overrides` | `dict` | `{}` | Override default severities |

### Usage

```python
from rejig import Rejig, SecurityConfig

config = SecurityConfig(
    ignore_files=["**/test_*.py", "**/conftest.py"],
    ignore_patterns=[r"EXAMPLE_.*", r"TEST_.*"],
    min_severity="medium",
    severity_overrides={
        "DEBUG_CODE": "low",
        "HARDCODED_TOKEN": "critical",
    },
)

rj = Rejig("src/")
security = rj.find_security_issues(config=config)
```

## SecurityReporter

Generate security reports.

```python
from rejig import Rejig, SecurityReporter

rj = Rejig("src/")
security = rj.find_security_issues()
reporter = SecurityReporter(security)

# Text report
print(reporter.to_text())

# JSON report
json_report = reporter.to_json()

# Markdown report
md_report = reporter.to_markdown()

# HTML report
html_report = reporter.to_html(include_code=True)

# SARIF format (for GitHub Code Scanning)
sarif_report = reporter.to_sarif()
```

## Severity Levels

| Level | Description | Examples |
|-------|-------------|----------|
| `critical` | Immediate action required | Hardcoded production secrets |
| `high` | Serious vulnerability | SQL injection, command injection |
| `medium` | Potential vulnerability | Unsafe YAML, insecure random |
| `low` | Minor issue | Debug code, weak crypto |

## Default Severity Mappings

| Type | Default Severity |
|------|------------------|
| `HARDCODED_SECRET` | high |
| `HARDCODED_API_KEY` | high |
| `HARDCODED_PASSWORD` | high |
| `HARDCODED_TOKEN` | high |
| `SQL_INJECTION` | high |
| `COMMAND_INJECTION` | high |
| `UNSAFE_EVAL` | high |
| `UNSAFE_PICKLE` | medium |
| `UNSAFE_YAML_LOAD` | medium |
| `INSECURE_RANDOM` | medium |
| `DEBUG_CODE` | low |
