# Security Recipes

Ready-to-use scripts for security scanning and remediation.

## Quick Security Scan

```python
#!/usr/bin/env python
"""Quick security scan of codebase."""
from rejig import Rejig

def security_scan(path: str = "src/") -> int:
    rj = Rejig(path)
    security = rj.find_security_issues()

    print("SECURITY SCAN RESULTS")
    print("=" * 60)
    print()

    if not security:
        print("No security issues found!")
        return 0

    print(security.summary())
    print()

    # Critical issues
    critical = security.critical()
    if critical:
        print("CRITICAL ISSUES:")
        print("-" * 40)
        for issue in critical:
            print(f"  {issue.file_path}:{issue.line_number}")
            print(f"    Type: {issue.type}")
            print(f"    {issue.message}")
            if issue.code_snippet:
                print(f"    Code: {issue.code_snippet[:60]}...")
            print()

    # High issues
    high = security.high()
    if high:
        print("HIGH SEVERITY ISSUES:")
        print("-" * 40)
        for issue in high:
            print(f"  {issue.file_path}:{issue.line_number}")
            print(f"    Type: {issue.type}")
            print(f"    {issue.message}")
            print()

    # Return exit code
    if critical or high:
        return 1
    return 0

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    sys.exit(security_scan(path))
```

## Secrets Scanner

```python
#!/usr/bin/env python
"""Scan for hardcoded secrets."""
from rejig import Rejig, SecretsScanner

def scan_secrets(path: str = "src/") -> None:
    rj = Rejig(path)
    scanner = SecretsScanner(rj)

    secrets = scanner.find_hardcoded_secrets()

    print("SECRETS SCAN")
    print("=" * 60)
    print()

    if not secrets:
        print("No hardcoded secrets detected!")
        return

    print(f"Found {len(secrets)} potential secrets:\n")

    # Group by type (SecurityType enum)
    by_type = {}
    for secret in secrets:
        by_type.setdefault(secret.type, []).append(secret)

    for secret_type, items in sorted(by_type.items(), key=lambda x: x[0].name):
        print(f"{secret_type.name} ({len(items)}):")
        for item in items[:5]:
            print(f"  {item.file_path}:{item.line_number}")
            print(f"    Severity: {item.severity}")
            # Don't print the actual secret value!
            print(f"    Pattern matched: {item.name}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")
        print()

    print("\nRecommendations:")
    print("  1. Move secrets to environment variables")
    print("  2. Use a secrets manager (AWS Secrets Manager, HashiCorp Vault)")
    print("  3. Add detected files to .gitignore if they contain real secrets")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    scan_secrets(path)
```

## SQL Injection Finder

```python
#!/usr/bin/env python
"""Find potential SQL injection vulnerabilities."""
from rejig import Rejig, VulnerabilityScanner

def find_sql_injection(path: str = "src/") -> None:
    rj = Rejig(path)
    scanner = VulnerabilityScanner(rj)

    issues = scanner.find_sql_injection_risks()

    print("SQL INJECTION SCAN")
    print("=" * 60)
    print()

    if not issues:
        print("No SQL injection patterns detected!")
        return

    print(f"Found {len(issues)} potential SQL injection points:\n")

    for issue in issues:
        print(f"{issue.file_path}:{issue.line_number}")
        print(f"  Code: {issue.code_snippet}")
        print(f"  Risk: {issue.severity}")
        print()

    print("Remediation:")
    print("  - Use parameterized queries")
    print("  - Use ORM methods instead of raw SQL")
    print("  - Validate and sanitize all user input")
    print()
    print("Example fix:")
    print("  UNSAFE: cursor.execute(f\"SELECT * FROM users WHERE id = {user_id}\")")
    print("  SAFE:   cursor.execute(\"SELECT * FROM users WHERE id = %s\", (user_id,))")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    find_sql_injection(path)
```

## Command Injection Finder

```python
#!/usr/bin/env python
"""Find potential command injection vulnerabilities."""
from rejig import Rejig, VulnerabilityScanner

def find_command_injection(path: str = "src/") -> None:
    rj = Rejig(path)
    scanner = VulnerabilityScanner(rj)

    issues = scanner.find_shell_injection_risks()

    print("COMMAND INJECTION SCAN")
    print("=" * 60)
    print()

    if not issues:
        print("No command injection patterns detected!")
        return

    print(f"Found {len(issues)} potential command injection points:\n")

    for issue in issues:
        print(f"{issue.file_path}:{issue.line_number}")
        print(f"  Code: {issue.code_snippet}")
        print(f"  Risk: {issue.severity}")
        print()

    print("Remediation:")
    print("  - Use subprocess with shell=False")
    print("  - Pass arguments as a list, not a string")
    print("  - Avoid os.system(), use subprocess instead")
    print()
    print("Example fix:")
    print("  UNSAFE: os.system(f'ls {user_dir}')")
    print("  SAFE:   subprocess.run(['ls', user_dir], shell=False)")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    find_command_injection(path)
```

## Unsafe Deserialization Finder

```python
#!/usr/bin/env python
"""Find unsafe pickle/yaml usage."""
from rejig import Rejig, VulnerabilityScanner

def find_unsafe_deserialize(path: str = "src/") -> None:
    rj = Rejig(path)
    scanner = VulnerabilityScanner(rj)

    yaml_issues = scanner.find_unsafe_yaml_load()
    pickle_issues = scanner.find_unsafe_pickle()

    print("UNSAFE DESERIALIZATION SCAN")
    print("=" * 60)
    print()

    if not yaml_issues and not pickle_issues:
        print("No unsafe deserialization patterns detected!")
        return

    if yaml_issues:
        print(f"Unsafe YAML usage ({len(yaml_issues)}):")
        print("-" * 40)
        for issue in yaml_issues:
            print(f"  {issue.file_path}:{issue.line_number}")
            print(f"    {issue.code_snippet}")
        print()
        print("  Fix: Use yaml.safe_load() instead of yaml.load()")
        print()

    if pickle_issues:
        print(f"Unsafe Pickle usage ({len(pickle_issues)}):")
        print("-" * 40)
        for issue in pickle_issues:
            print(f"  {issue.file_path}:{issue.line_number}")
            print(f"    {issue.code_snippet}")
        print()
        print("  Fix: Use JSON or other safe serialization formats")
        print("       Never unpickle data from untrusted sources")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    find_unsafe_deserialize(path)
```

## Security Report Generator

```python
#!/usr/bin/env python
"""Generate comprehensive security report."""
from rejig import Rejig

def generate_security_report(
    path: str = "src/",
    output_format: str = "json",
    output_file: str = "security-report",
) -> None:
    rj = Rejig(path)

    print("Generating security report...")

    # Supported formats: "json", "markdown", "sarif"
    extensions = {"json": "json", "markdown": "md", "sarif": "sarif"}
    ext = extensions.get(output_format, "json")
    filename = f"{output_file}.{ext}"

    result = rj.generate_security_report(filename, format=output_format)
    if result.success:
        print(f"Report saved to: {filename}")
    else:
        print(f"Failed: {result.message}")

    # Print summary
    print()
    print("SUMMARY")
    print("=" * 40)
    print(rj.find_security_issues().summary())

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    fmt = sys.argv[2] if len(sys.argv) > 2 else "json"
    generate_security_report(path, fmt)
```

## Pre-commit Security Hook

```python
#!/usr/bin/env python
"""Pre-commit hook for security checks."""
import subprocess
import sys
from rejig import Rejig

def get_staged_files() -> list[str]:
    """Get list of staged Python files."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )
    files = result.stdout.strip().split("\n")
    return [f for f in files if f.endswith(".py")]

def check_staged_files() -> int:
    """Check staged files for security issues."""
    staged = get_staged_files()

    if not staged:
        return 0

    print(f"Checking {len(staged)} staged files for security issues...")

    # Check each file
    issues_found = []

    for file_path in staged:
        rj = Rejig(file_path)
        security = rj.find_security_issues()

        critical_high = list(security.critical()) + list(security.high())
        if critical_high:
            issues_found.extend(critical_high)

    if issues_found:
        print()
        print("SECURITY ISSUES FOUND - COMMIT BLOCKED")
        print("=" * 50)
        for issue in issues_found:
            print(f"  [{issue.severity}] {issue.file_path}:{issue.line_number}")
            print(f"    {issue.type}: {issue.message}")
        print()
        print("Fix these issues before committing.")
        print("To bypass (not recommended): git commit --no-verify")
        return 1

    print("No security issues found.")
    return 0

if __name__ == "__main__":
    sys.exit(check_staged_files())
```

## Auto-fix Common Issues

```python
#!/usr/bin/env python
"""Auto-fix common security issues where safe to do so."""
from rejig import Rejig, SecurityType

def auto_fix_security(path: str = "src/", dry_run: bool = True) -> None:
    rj = Rejig(path, dry_run=dry_run)
    security = rj.find_security_issues()

    print("AUTO-FIX SECURITY ISSUES")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    fixed = 0
    skipped = 0

    for issue in security:
        # issue.type is a SecurityType enum member.
        if issue.type == SecurityType.UNSAFE_YAML_LOAD:
            # Safe to auto-fix: yaml.load -> yaml.safe_load
            file_target = issue.to_file_target()
            result = file_target.replace_pattern(
                r"yaml\.load\(",
                "yaml.safe_load(",
            )
            if result.success:
                print(f"FIXED: {issue.file_path}:{issue.line_number}")
                print(f"  yaml.load -> yaml.safe_load")
                fixed += 1
            continue

        if issue.type == SecurityType.INSECURE_RANDOM:
            # Safe to auto-fix: random -> secrets for specific patterns
            # This is more complex, skip for now
            pass

        if issue.type == SecurityType.DEBUG_CODE:
            # Can remove debug statements
            line = issue.to_line_target()
            result = line.delete()
            if result.success:
                print(f"FIXED: {issue.file_path}:{issue.line_number}")
                print(f"  Removed debug statement")
                fixed += 1
            continue

        # Most issues need manual review
        skipped += 1

    print()
    print("SUMMARY")
    print("-" * 40)
    print(f"Fixed: {fixed}")
    print(f"Skipped (manual review needed): {skipped}")

    if dry_run and fixed > 0:
        print()
        print("Run with --apply to apply fixes:")
        print(f"  python {__file__} {path} --apply")

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "src/"
    dry_run = "--apply" not in sys.argv
    auto_fix_security(path, dry_run)
```

## GitHub Actions Security Workflow

```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

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
        id: security
        run: |
          python -c "
          from rejig import Rejig
          rj = Rejig('src/')

          # Generate SARIF for GitHub
          rj.generate_security_report('security.sarif', format='sarif')

          # Check for critical/high issues
          security = rj.find_security_issues()
          critical_high = len(security.critical()) + len(security.high())
          print(f'::set-output name=critical_high::{critical_high}')

          if critical_high:
              print('::error::Found critical/high security issues')
              exit(1)
          "

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: security.sarif

      - name: Comment on PR
        if: failure() && github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '## Security Issues Found\n\nThis PR introduces security issues that must be resolved before merging.\n\nSee the Security tab for details.'
            })
```
