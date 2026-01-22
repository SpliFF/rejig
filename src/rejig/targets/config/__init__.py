"""Configuration file targets for manipulating config files.

This package provides Target classes for working with configuration files:

- ConfigTarget: Abstract base class for config targets
- TomlTarget: TOML files (pyproject.toml, etc.)
- JsonTarget: JSON files (package.json, etc.)
- YamlTarget: YAML files (config.yaml, etc.)
- IniTarget: INI/CFG files (setup.cfg, etc.)
"""

from rejig.targets.config.base import ConfigTarget
from rejig.targets.config.ini import IniTarget
from rejig.targets.config.json import JsonTarget
from rejig.targets.config.toml import TomlTarget
from rejig.targets.config.yaml import YamlTarget

__all__ = [
    "ConfigTarget",
    "TomlTarget",
    "JsonTarget",
    "YamlTarget",
    "IniTarget",
]
