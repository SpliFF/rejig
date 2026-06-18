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
| `name` | `str \| None` | Name of the pattern matched |
| `message` | `str` | Human-readable description |
| `severity` | `str` | "critical", "high", "medium", or "low" |
| `code_snippet` | `str \| None` | The problematic code |
| `context` | `dict` | Additional context |
| `recommendation` | `str \| None` | Suggested remediation |

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
| `at_least(min_severity)` | `SecurityTargetList` | Findings at or above `min_severity` |

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

Scan for hardcoded secrets. Constructed with a `Rejig` instance.

```python
from rejig import Rejig, SecretsScanner

rj = Rejig("src/")
scanner = SecretsScanner(rj)

# Find all hardcoded secrets (SecurityTargetList)
secrets = scanner.find_hardcoded_secrets()
```

### VulnerabilityScanner

Scan for vulnerability patterns. Each method returns a `SecurityTargetList`.

```python
from rejig import Rejig, VulnerabilityScanner

rj = Rejig("src/")
scanner = VulnerabilityScanner(rj)

# Find specific vulnerability types
sql = scanner.find_sql_injection_risks()
shell = scanner.find_shell_injection_risks()
yaml_load = scanner.find_unsafe_yaml_load()
pickle = scanner.find_unsafe_pickle()
deserialize = scanner.find_unsafe_deserialization()
eval_exec = scanner.find_unsafe_eval()
path_traversal = scanner.find_path_traversal_risks()
insecure_random = scanner.find_insecure_random()
weak_crypto = scanner.find_weak_crypto()
insecure_ssl = scanner.find_insecure_ssl()

# Find every vulnerability type at once
unsafe = scanner.find_all_vulnerabilities()
```

## Running a Scan

Use `Rejig.find_security_issues()` to combine all scanners and return a single
`SecurityTargetList`. It takes no arguments.

```python
from rejig import Rejig

rj = Rejig("src/")
security = rj.find_security_issues()
critical = security.critical()
```

Related convenience methods on `Rejig`:

| Method | Returns | Description |
|--------|---------|-------------|
| `find_security_issues()` | `SecurityTargetList` | All findings combined |
| `quick_security_scan()` | `SecurityTargetList` | Critical + high findings only |
| `analyze_security()` | `SecurityReport` | Full report object |
| `generate_security_report(output_path=None, format="json")` | `Result` | Write a report ("json", "markdown", or "sarif") |

## SecurityReporter

Generate security reports. The reporter is constructed with a `Rejig` instance
(it runs the scanners itself).

```python
from rejig import Rejig, SecurityReporter

rj = Rejig("src/")
reporter = SecurityReporter(rj)

# Full SecurityReport object (same as rj.analyze_security())
report = reporter.generate_full_report()
print(f"Total: {report.total_findings}")
print(f"Critical: {report.critical_count}")

# Quick scan (critical + high findings)
critical = reporter.quick_scan()

# Write a report to disk in a chosen format
reporter.generate_security_report("reports/security.json", format="json")
reporter.generate_security_report("reports/security.md", format="markdown")
reporter.generate_security_report("reports/security.sarif", format="sarif")
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
