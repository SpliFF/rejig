# Installation

## Requirements

- Python 3.10 or higher
- LibCST (installed automatically)

## Install from PyPI

```bash
pip install rejig
```

## Install with Optional Dependencies

```bash
# Include Rope for semantic refactoring (move with import updates)
pip install rejig[rope]

# Include all optional dependencies
pip install rejig[all]
```

## Install from Source

```bash
git clone https://github.com/your-org/rejig.git
cd rejig
pip install -e ".[dev]"
```

## Verify Installation

```python
from rejig import Rejig

rj = Rejig(".")
print(f"Found {len(rj.find_files())} Python files")
```

## Editor Integration

Rejig is a library, not a CLI tool. You'll typically use it in:

- **Python scripts** — Write refactoring scripts for your project
- **Jupyter notebooks** — Explore and test transformations interactively
- **CI/CD pipelines** — Automate code migrations
- **Custom CLI tools** — Build project-specific refactoring commands
