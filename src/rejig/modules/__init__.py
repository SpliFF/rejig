"""Module-level operations for splitting, merging, and reorganizing Python modules.

This package provides utilities for:
- Splitting files by class or function
- Merging multiple modules
- Managing __all__ exports
- Adding/updating file headers (copyright, license)
"""
from rejig.modules.exports import (
    ExportsManager,
    add_to_all,
    generate_all_exports,
    get_all_exports,
    remove_from_all,
    update_all_exports,
)
from rejig.modules.headers import (
    HeaderManager,
    add_copyright_header,
    add_license_header,
    get_license_text,
    update_copyright_year,
)
from rejig.modules.merge import ModuleMerger, merge_modules
from rejig.modules.rename import ModuleRenamer, move_module, rename_module
from rejig.modules.split import ModuleSplitter, split_by_class, split_by_function

__all__ = [
    # Split utilities
    "ModuleSplitter",
    "split_by_class",
    "split_by_function",
    # Merge utilities
    "ModuleMerger",
    "merge_modules",
    # Rename utilities
    "ModuleRenamer",
    "rename_module",
    "move_module",
    # Exports management
    "ExportsManager",
    "get_all_exports",
    "generate_all_exports",
    "update_all_exports",
    "add_to_all",
    "remove_from_all",
    # Header management
    "HeaderManager",
    "add_copyright_header",
    "add_license_header",
    "get_license_text",
    "update_copyright_year",
]
