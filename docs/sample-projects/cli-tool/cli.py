"""Command-line tool with various issues for testing."""
import os
import sys
import json
import click
from pathlib import Path


# Magic numbers
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
BUFFER_SIZE = 8192


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """A sample CLI tool."""
    pass


@cli.command()
@click.argument("path")
@click.option("--format", "-f", type=click.Choice(["json", "text"]), default="text")
def analyze(path, format):
    """Analyze a file or directory."""
    target = Path(path)
    if not target.exists():
        click.echo(f"Error: {path} does not exist", err=True)
        sys.exit(1)

    if target.is_file():
        result = analyze_file(target)
    else:
        result = analyze_directory(target)

    if format == "json":
        click.echo(json.dumps(result, indent=2))
    else:
        # Complex formatting logic
        for key, value in result.items():
            if isinstance(value, dict):
                click.echo(f"{key}:")
                for k, v in value.items():
                    click.echo(f"  {k}: {v}")
            elif isinstance(value, list):
                click.echo(f"{key}:")
                for item in value:
                    click.echo(f"  - {item}")
            else:
                click.echo(f"{key}: {value}")


def analyze_file(path):
    """Analyze a single file."""
    content = path.read_text()
    lines = content.split("\n")

    return {
        "path": str(path),
        "lines": len(lines),
        "characters": len(content),
        "words": len(content.split()),
    }


def analyze_directory(path):
    """Analyze a directory."""
    total_files = 0
    total_lines = 0
    total_chars = 0

    for file_path in path.rglob("*"):
        if file_path.is_file():
            total_files += 1
            try:
                content = file_path.read_text()
                total_lines += len(content.split("\n"))
                total_chars += len(content)
            except:  # bare except - should be specific
                pass

    return {
        "path": str(path),
        "files": total_files,
        "total_lines": total_lines,
        "total_characters": total_chars,
    }


@cli.command()
@click.argument("source")
@click.argument("dest")
@click.option("--overwrite", "-o", is_flag=True)
def copy(source, dest, overwrite):
    """Copy a file or directory."""
    src_path = Path(source)
    dst_path = Path(dest)

    if not src_path.exists():
        click.echo(f"Error: {source} does not exist", err=True)
        sys.exit(1)

    if dst_path.exists() and not overwrite:
        click.echo(f"Error: {dest} already exists. Use --overwrite to replace.", err=True)
        sys.exit(1)

    # Complex nested logic - should be refactored
    if src_path.is_file():
        if dst_path.is_dir():
            dst_path = dst_path / src_path.name
        dst_path.write_bytes(src_path.read_bytes())
        click.echo(f"Copied {source} to {dst_path}")
    else:
        if dst_path.exists():
            if dst_path.is_file():
                click.echo("Error: Cannot copy directory to file", err=True)
                sys.exit(1)
        else:
            dst_path.mkdir(parents=True)

        for item in src_path.rglob("*"):
            relative = item.relative_to(src_path)
            target = dst_path / relative
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(item.read_bytes())

        click.echo(f"Copied {source} to {dest}")


@cli.command()
@click.argument("pattern")
@click.option("--path", "-p", default=".")
@click.option("--recursive", "-r", is_flag=True)
def find(pattern, path, recursive):
    """Find files matching a pattern."""
    search_path = Path(path)

    if not search_path.exists():
        click.echo(f"Error: {path} does not exist", err=True)
        sys.exit(1)

    if recursive:
        matches = list(search_path.rglob(pattern))
    else:
        matches = list(search_path.glob(pattern))

    for match in matches:
        click.echo(str(match))

    click.echo(f"\nFound {len(matches)} matches")


@cli.command()
@click.argument("files", nargs=-1)
@click.option("--verbose", "-v", is_flag=True)
def validate(files, verbose):
    """Validate files."""
    errors = []
    warnings = []

    for file_path in files:
        path = Path(file_path)
        if not path.exists():
            errors.append(f"{file_path}: File not found")
            continue

        content = path.read_text()

        # Duplicate validation logic
        if not content.strip():
            warnings.append(f"{file_path}: File is empty")

        if len(content) > 1000000:  # Magic number
            warnings.append(f"{file_path}: File is very large")

        # More duplicate logic
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if len(line) > 120:  # Magic number
                warnings.append(f"{file_path}:{i}: Line too long")

    if errors:
        click.echo("Errors:", err=True)
        for error in errors:
            click.echo(f"  {error}", err=True)

    if warnings and verbose:
        click.echo("Warnings:")
        for warning in warnings:
            click.echo(f"  {warning}")

    if errors:
        sys.exit(1)


# Duplicate function - same as analyze_file
def get_file_stats(path):
    """Get statistics for a file."""
    content = Path(path).read_text()
    lines = content.split("\n")

    return {
        "path": str(path),
        "lines": len(lines),
        "characters": len(content),
        "words": len(content.split()),
    }


# Unused function
def deprecated_format_output(data):
    """Old output formatter - deprecated."""
    output = []
    for key, value in data.items():
        output.append(f"{key}={value}")
    return "\n".join(output)


# TODO: Add progress bars for long operations
# FIXME: Memory usage is high for large directories

class Config:
    """Configuration handler."""

    def __init__(self, config_path=None):
        self.config_path = config_path or Path.home() / ".cli-tool.json"
        self.data = {}
        self.load()

    def load(self):
        if self.config_path.exists():
            self.data = json.loads(self.config_path.read_text())

    def save(self):
        self.config_path.write_text(json.dumps(self.data, indent=2))

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()


# Duplicate class - similar to Config
class Settings:
    """Settings handler."""

    def __init__(self, settings_path=None):
        self.settings_path = settings_path or Path.home() / ".cli-settings.json"
        self.data = {}
        self.load()

    def load(self):
        if self.settings_path.exists():
            self.data = json.loads(self.settings_path.read_text())

    def save(self):
        self.settings_path.write_text(json.dumps(self.data, indent=2))

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()


if __name__ == "__main__":
    cli()
