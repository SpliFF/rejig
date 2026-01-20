"""Text file targets for manipulating plain text files.

This package provides Target classes for working with text files:

- TextFileTarget: Any text file (line-based operations)
- TextBlock: Raw text pattern-based manipulation
- TextMatch: Individual pattern match within a file
"""

from rejig.targets.text.text_block import TextBlock
from rejig.targets.text.text_file import TextFileTarget
from rejig.targets.text.text_match import TextMatch

__all__ = [
    "TextFileTarget",
    "TextBlock",
    "TextMatch",
]
