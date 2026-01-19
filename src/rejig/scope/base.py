"""Base scope class for all scope types."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rejig.core import Manipylate


class BaseScope:
    """Base class for all scope types."""

    def __init__(self, manipylate: Manipylate):
        self.manipylate = manipylate

    @property
    def dry_run(self) -> bool:
        return self.manipylate.dry_run

    @property
    def files(self) -> list[Path]:
        return self.manipylate.files
