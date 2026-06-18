# Security Analysis

Rejig provides security scanning capabilities to detect hardcoded secrets, vulnerability patterns, and other security issues in your Python code.

## Quick Start

```python
from rejig import Rejig

rj = Rejig("src/")

# Find all security issues
security = rj.find_security_issues()

# Print summary
print(security.summary())
# Output (multi-line):
#   Total: 12 security findings
#     CRITICAL: 2
#     HIGH: 4
#     MEDIUM: 3
#     LOW: 3
#   ...per-type counts...

# List critical and high issues
for issue in security.at_least("high"):
    print(f"{issue.severity}: {issue.message}")
    print(f"  {issue.file_path}:{issue.line_number}")
    print(f"  Code: {issue.code_snippet}")
```

## Security Issue Types

### Hardcoded Secrets

| Type | Description |
|------|-------------|
| `HARDCODED_SECRET` | Generic secret detection |
| `HARDCODED_API_KEY` | API keys (AWS, Google, etc.) |
| `HARDCODED_PASSWORD` | Password strings in code |
| `HARDCODED_TOKEN` | Auth tokens, JWT secrets |
| `HARDCODED_CRYPTO_KEY` | Encryption keys |

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
| `UNSAFE_PICKLE` | pickle.load on untrusted data |
| `UNSAFE_EVAL` | eval() on user input |
| `UNSAFE_EXEC` | exec() on dynamic code |
| `UNSAFE_DESERIALIZE` | Insecure deserialization |

### Path and File Issues

| Type | Description |
|------|-------------|
| `PATH_TRAVERSAL` | Unsanitized path construction |
| `INSECURE_FILE_PERMISSIONS` | chmod with overly permissive mode |

### Cryptography Issues

| Type | Description |
|------|-------------|
| `INSECURE_RANDOM` | random module for security |
| `WEAK_CRYPTO` | MD5, SHA1, DES, etc. |

### Network Issues

| Type | Description |
|------|-------------|
| `INSECURE_SSL` | SSL verification disabled |
| `DISABLED_CERT_VERIFICATION` | verify=False in requests |

### Other Issues

| Type | Description |
|------|-------------|
| `DEBUG_CODE` | Debug statements in production |
| `SENSITIVE_DATA_EXPOSURE` | Logging sensitive data |

## Filtering Issues

### By Severity

```python
security = rj.find_security_issues()

# Severity-specific filters
critical = security.critical()
high = security.high()
medium = security.medium()
low = security.low()

# Findings at or above a severity level (critical + high)
urgent = security.at_least("high")
```

### By Type

Type filters take `SecurityType` enum members:

```python
from rejig import SecurityType

# Single type
secrets = security.by_type(SecurityType.HARDCODED_SECRET)

# Multiple types (variadic)
injection = security.by_types(
    SecurityType.SQL_INJECTION,
    SecurityType.SHELL_INJECTION,
    SecurityType.COMMAND_INJECTION,
)

# All secret-related (or use the secrets() shortcut)
all_secrets = security.by_types(
    SecurityType.HARDCODED_SECRET,
    SecurityType.HARDCODED_API_KEY,
    SecurityType.HARDCODED_PASSWORD,
    SecurityType.HARDCODED_TOKEN,
    SecurityType.HARDCODED_CRYPTO_KEY,
)

# Category shortcuts
all_secrets = security.secrets()
all_injection = security.injection_risks()
unsafe = security.unsafe_operations()
crypto = security.crypto_issues()
```

### By Location

```python
# Issues in a specific file
file_issues = security.in_file("src/config.py")

# Issues in a directory
api_issues = security.in_directory("src/api/")
```

## Secret Detection

### Find Hardcoded Secrets

```python
from rejig import SecretsScanner

scanner = SecretsScanner(rj)

# Find all secrets
secrets = scanner.find_hardcoded_secrets()

for secret in secrets:
    print(f"Found {secret.type.name} at {secret.file_path}:{secret.line_number}")
    print(f"  Name: {secret.name}")
    print(f"  Code: {secret.code_snippet}")

# Or filter to specific kinds
api_keys = scanner.find_api_keys()
passwords = scanner.find_passwords()
tokens = scanner.find_tokens()
```

### Supported Secret Patterns

```python
# AWS keys
AWS_ACCESS_KEY_ID = "AKIA..."          # Detected
AWS_SECRET_ACCESS_KEY = "..."           # Detected

# API keys
GOOGLE_API_KEY = "AIza..."             # Detected
STRIPE_SECRET_KEY = "sk_live_..."      # Detected
GITHUB_TOKEN = "ghp_..."               # Detected

# Database URLs
DATABASE_URL = "postgresql://user:pass@host/db"  # Detected

# Private keys
PRIVATE_KEY = "-----BEGIN RSA PRIVATE KEY-----"  # Detected

# Generic patterns
SECRET_KEY = "my-super-secret-key"     # Detected
password = "admin123"                  # Detected
api_key = "abc123def456"               # Detected
```

## Vulnerability Detection

### Find SQL Injection

```python
from rejig import VulnerabilityScanner

scanner = VulnerabilityScanner(rj)

# Find SQL injection patterns
sql_issues = scanner.find_sql_injection_risks()

for issue in sql_issues:
    print(f"SQL Injection risk: {issue.file_path}:{issue.line_number}")
    print(f"  Code: {issue.code_snippet}")
    print(f"  Suggestion: Use parameterized queries")
```

You can also call these directly on the Rejig instance, e.g.
`rj.find_sql_injection_risks()`.

### Examples of Detected Patterns

```python
# SQL Injection - DETECTED
query = "SELECT * FROM users WHERE id = " + user_id
cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")

# Safe alternatives - NOT flagged
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
User.objects.filter(id=user_id)  # Django ORM
```

### Find Shell/Command Injection

```python
cmd_issues = scanner.find_shell_injection_risks()

for issue in cmd_issues:
    print(f"Shell Injection: {issue.file_path}:{issue.line_number}")
```

### Examples of Detected Patterns

```python
# Shell Injection - DETECTED
os.system("ls " + user_input)
subprocess.call(f"echo {message}", shell=True)
subprocess.Popen(command, shell=True)

# Safe alternatives - NOT flagged
subprocess.run(["ls", directory], shell=False)
subprocess.run(["echo", message])
```

### Find Unsafe Operations

```python
# Find all unsafe deserialization operations
unsafe = scanner.find_unsafe_deserialization()

# Or specific types
yaml_issues = scanner.find_unsafe_yaml_load()
pickle_issues = scanner.find_unsafe_pickle()
eval_issues = scanner.find_unsafe_eval()
```

### Examples of Detected Patterns

```python
# Unsafe YAML - DETECTED
data = yaml.load(file)  # Uses unsafe Loader
yaml.load(content, Loader=yaml.Loader)

# Safe alternative - NOT flagged
data = yaml.safe_load(file)
yaml.load(content, Loader=yaml.SafeLoader)

# Unsafe Pickle - DETECTED
data = pickle.load(untrusted_file)

# Unsafe Eval - DETECTED
result = eval(user_input)
exec(dynamic_code)
```

## Grouping and Aggregation

### Group by File

```python
by_file = security.group_by_file()

for file_path, issues in by_file.items():
    print(f"\n{file_path}:")
    for issue in issues:
        print(f"  [{issue.severity}] {issue.type}: {issue.message}")
```

### Group by Type

```python
by_type = security.group_by_type()

for issue_type, issues in by_type.items():
    print(f"\n{issue_type.name}: {len(issues)} occurrences")
    for issue in issues.to_list()[:3]:  # Show first 3
        print(f"  {issue.file_path}:{issue.line_number}")
```

### Statistics

```python
# Count by type (keys are SecurityType enum members)
type_counts = security.count_by_type()
print(type_counts)
# {<SecurityType.HARDCODED_SECRET>: 5, <SecurityType.SQL_INJECTION>: 2, ...}

# Count by severity
severity_counts = security.count_by_severity()
print(severity_counts)
# {"critical": 2, "high": 4, "medium": 3, "low": 3}
```

## Working with Findings

### Navigate to Code

```python
for issue in security:
    # Get file target
    file_target = issue.to_file_target()

    # Get line target for direct manipulation
    line_target = issue.to_line_target()

    # Read surrounding context (get_content() returns a Result; text is in .data)
    context = file_target.lines(
        issue.line_number - 2,
        issue.line_number + 2,
    ).get_content()
    print(context.data)
```

### Export Findings

```python
# Export as list of dictionaries
findings_list = security.to_list_of_dicts()

# Export as JSON
import json
with open("security-report.json", "w") as f:
    json.dump(findings_list, f, indent=2, default=str)
```

## Generating Reports

### Security Reporter

The simplest way to produce a report is `rj.generate_security_report()`, which
writes a file (or returns the data) in JSON, Markdown, or SARIF format:

```python
# Write reports to files
rj.generate_security_report("reports/security.json", format="json")
rj.generate_security_report("reports/security.md", format="markdown")

# Or get the data back in the Result instead of writing a file
result = rj.generate_security_report(format="json")
report_data = result.data
```

For more control, construct a `SecurityReporter` directly (it takes the Rejig
instance) and build a `SecurityReport` object:

```python
from rejig import SecurityReporter

reporter = SecurityReporter(rj)

# A SecurityReport object with summary properties
report = reporter.generate_full_report()
print(report)                     # human-readable summary
print(report.total_findings)
print(report.critical_count)

# Write a report file in a chosen format
reporter.generate_security_report("reports/security.md", format="markdown")

# Quick scan: only critical and high severity findings
urgent = reporter.quick_scan()
```

The same `SecurityReport` object is also available via `rj.analyze_security()`.

### SARIF Output

```python
# SARIF format for GitHub Code Scanning
rj.generate_security_report("security.sarif", format="sarif")
```

## CI Integration

### Pre-commit Hook

```python
#!/usr/bin/env python
"""Pre-commit hook for security scanning."""
import sys
from rejig import Rejig

rj = Rejig("src/")
security = rj.find_security_issues()

# Fail on critical or high severity
critical_high = security.at_least("high")

if critical_high:
    print("Security issues found!")
    for issue in critical_high:
        print(f"  [{issue.severity}] {issue.file_path}:{issue.line_number}")
        print(f"    {issue.message}")
    sys.exit(1)

# Warn on medium
medium = security.medium()
if medium:
    print(f"Warning: {len(medium)} medium severity security issues")

sys.exit(0)
```

### GitHub Actions

```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install rejig

      - name: Run security scan
        run: |
          python -c "
          from rejig import Rejig
          rj = Rejig('src/')
          rj.generate_security_report('security.sarif', format='sarif')
          security = rj.find_security_issues()
          if security.critical() or security.high():
              exit(1)
          "

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: security.sarif
```

## Filtering Results

`find_security_issues()` takes no configuration arguments. Instead, filter the
returned `SecurityTargetList` after scanning:

```python
security = rj.find_security_issues()

# Only report medium severity and above
reportable = security.at_least("medium")

# Exclude findings in test files
reportable = security.filter(
    lambda issue: "test" not in issue.file_path.name
)
```

The secret and vulnerability scanners also apply built-in false-positive
filtering automatically. For secrets, this skips:

- Test, example, sample, mock, and fixture files (by filename)
- Findings inside comments
- Obvious placeholders (e.g. `your_`, `example`, `placeholder`, `changeme`)

## Common Patterns

### Audit Before Deployment

```python
from rejig import Rejig

rj = Rejig("src/")
security = rj.find_security_issues()

# Block deployment on critical issues
if security.critical():
    print("CRITICAL SECURITY ISSUES - DEPLOYMENT BLOCKED")
    for issue in security.critical():
        print(f"  {issue.file_path}:{issue.line_number}: {issue.message}")
    exit(1)

# Require review for high issues
if security.high():
    print("HIGH SEVERITY ISSUES - MANUAL REVIEW REQUIRED")
    # Create review ticket, send alert, etc.
```

### Track Security Debt

```python
# Generate a security debt report
security = rj.find_security_issues()

by_severity = security.count_by_severity()
by_type = security.count_by_type()

print("Security Debt Summary")
print("=" * 40)
print(f"Critical: {by_severity.get('critical', 0)}")
print(f"High:     {by_severity.get('high', 0)}")
print(f"Medium:   {by_severity.get('medium', 0)}")
print(f"Low:      {by_severity.get('low', 0)}")
print()
print("By Type:")
for issue_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
    print(f"  {issue_type.name}: {count}")
```

### Remediation Guidance

```python
REMEDIATION = {
    "SQL_INJECTION": "Use parameterized queries or ORM methods",
    "COMMAND_INJECTION": "Use subprocess with shell=False and list arguments",
    "HARDCODED_SECRET": "Move to environment variables or secrets manager",
    "UNSAFE_YAML_LOAD": "Use yaml.safe_load() instead",
    "UNSAFE_PICKLE": "Use JSON or other safe serialization formats",
    "INSECURE_RANDOM": "Use secrets module for security-sensitive randomness",
}

for issue in security:
    print(f"{issue.type.name}: {issue.message}")
    if issue.type.name in REMEDIATION:
        print(f"  Fix: {REMEDIATION[issue.type.name]}")
```
