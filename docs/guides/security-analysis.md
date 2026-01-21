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
# Output: Total: 12 issues (2 critical, 4 high, 3 medium, 3 low)

# List critical and high issues
for issue in security.critical() + security.high():
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

# Combined
urgent = security.by_severity(["critical", "high"])
```

### By Type

```python
# Single type
secrets = security.by_type("HARDCODED_SECRET")

# Multiple types
injection = security.by_types([
    "SQL_INJECTION",
    "COMMAND_INJECTION",
    "SHELL_INJECTION"
])

# All secret-related
all_secrets = security.by_types([
    "HARDCODED_SECRET",
    "HARDCODED_API_KEY",
    "HARDCODED_PASSWORD",
    "HARDCODED_TOKEN",
    "HARDCODED_CRYPTO_KEY"
])
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
secrets = scanner.find_all()

for secret in secrets:
    print(f"Found {secret.type} at {secret.file_path}:{secret.line_number}")
    print(f"  Pattern: {secret.pattern_name}")
    print(f"  Confidence: {secret.confidence}")
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

### Custom Secret Patterns

```python
scanner = SecretsScanner(rj)

# Add custom patterns
scanner.add_pattern(
    name="internal_api_key",
    pattern=r"INTERNAL_[A-Z]+_KEY\s*=\s*['\"][^'\"]+['\"]",
    severity="high",
)

scanner.add_pattern(
    name="slack_webhook",
    pattern=r"https://hooks\.slack\.com/services/[A-Z0-9]+/[A-Z0-9]+/[a-zA-Z0-9]+",
    severity="high",
)

secrets = scanner.find_all()
```

## Vulnerability Detection

### Find SQL Injection

```python
from rejig import VulnerabilityScanner

scanner = VulnerabilityScanner(rj)

# Find SQL injection patterns
sql_issues = scanner.find_sql_injection()

for issue in sql_issues:
    print(f"SQL Injection risk: {issue.file_path}:{issue.line_number}")
    print(f"  Code: {issue.code_snippet}")
    print(f"  Suggestion: Use parameterized queries")
```

### Examples of Detected Patterns

```python
# SQL Injection - DETECTED
query = "SELECT * FROM users WHERE id = " + user_id
cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")

# Safe alternatives - NOT flagged
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
User.objects.filter(id=user_id)  # Django ORM
```

### Find Command Injection

```python
cmd_issues = scanner.find_command_injection()

for issue in cmd_issues:
    print(f"Command Injection: {issue.file_path}:{issue.line_number}")
```

### Examples of Detected Patterns

```python
# Command Injection - DETECTED
os.system("ls " + user_input)
subprocess.call(f"echo {message}", shell=True)
subprocess.Popen(command, shell=True)

# Safe alternatives - NOT flagged
subprocess.run(["ls", directory], shell=False)
subprocess.run(["echo", message])
```

### Find Unsafe Operations

```python
# Find all unsafe operations
unsafe = scanner.find_unsafe_operations()

# Or specific types
yaml_issues = scanner.find_unsafe_yaml()
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
    print(f"\n{issue_type}: {len(issues)} occurrences")
    for issue in issues[:3]:  # Show first 3
        print(f"  {issue.file_path}:{issue.line_number}")
```

### Statistics

```python
# Count by type
type_counts = security.count_by_type()
print(type_counts)
# {"HARDCODED_SECRET": 5, "SQL_INJECTION": 2, ...}

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

    # Read surrounding context
    print(file_target.get_lines(
        issue.line_number - 2,
        issue.line_number + 2
    ))
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

```python
from rejig import SecurityReporter

reporter = SecurityReporter(security)

# Text report
print(reporter.to_text())

# JSON report
json_report = reporter.to_json()

# Markdown report
md_report = reporter.to_markdown()

# HTML report with code snippets
html_report = reporter.to_html(
    include_code=True,
    syntax_highlight=True,
)
```

### SARIF Output

```python
# SARIF format for GitHub Code Scanning
sarif_report = reporter.to_sarif()

with open("security.sarif", "w") as f:
    f.write(sarif_report)
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
critical_high = security.critical() + security.high()

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
          from rejig import Rejig, SecurityReporter
          rj = Rejig('src/')
          security = rj.find_security_issues()
          reporter = SecurityReporter(security)
          with open('security.sarif', 'w') as f:
              f.write(reporter.to_sarif())
          if security.critical() or security.high():
              exit(1)
          "

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: security.sarif
```

## Configuration

### Ignore Patterns

```python
from rejig import SecurityConfig

config = SecurityConfig(
    # Ignore specific files
    ignore_files=["**/test_*.py", "**/conftest.py"],

    # Ignore specific patterns
    ignore_patterns=[
        r"EXAMPLE_.*",  # Example values
        r"TEST_.*",     # Test values
    ],

    # Ignore specific line patterns
    ignore_line_patterns=[
        r"# nosec",           # Bandit-style ignore
        r"# security: ignore",
    ],

    # Minimum severity to report
    min_severity="medium",
)

security = rj.find_security_issues(config=config)
```

### Custom Severity Mappings

```python
config = SecurityConfig(
    severity_overrides={
        "DEBUG_CODE": "low",          # Downgrade
        "HARDCODED_TOKEN": "critical", # Upgrade
    }
)
```

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
for type_name, count in sorted(by_type.items(), key=lambda x: -x[1]):
    print(f"  {type_name}: {count}")
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
    print(f"{issue.type}: {issue.message}")
    if issue.type in REMEDIATION:
        print(f"  Fix: {REMEDIATION[issue.type]}")
```
