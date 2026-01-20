"""File header utilities for copyright and license management.

This module provides utilities for managing file headers:
- Add copyright headers
- Add license headers
- Update copyright years
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig

from rejig.core.results import Result

# Common license header templates
LICENSE_HEADERS = {
    "MIT": '''# SPDX-License-Identifier: MIT
# {copyright}''',
    "Apache-2.0": '''# SPDX-License-Identifier: Apache-2.0
# {copyright}
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.''',
    "GPL-3.0": '''# SPDX-License-Identifier: GPL-3.0-or-later
# {copyright}
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.''',
    "BSD-3-Clause": '''# SPDX-License-Identifier: BSD-3-Clause
# {copyright}
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.''',
    "Proprietary": '''# {copyright}
# All rights reserved. This software is proprietary and confidential.
# Unauthorized copying, distribution, or use is strictly prohibited.''',
}

# Year patterns for finding and updating copyright years
YEAR_PATTERN = re.compile(r"((?:19|20)\d{2})(?:\s*[-–]\s*((?:19|20)\d{2}))?")
COPYRIGHT_PATTERN = re.compile(
    r"^#\s*(?:Copyright|©|\(c\))\s+(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


class HeaderManager:
    """Manages file headers for copyright and license information.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def add_copyright_header(
        self,
        file_path: Path,
        copyright_text: str,
        year: int | None = None,
    ) -> Result:
        """Add a copyright header to a file.

        Parameters
        ----------
        file_path : Path
            Path to the Python file.
        copyright_text : str
            Copyright holder text (e.g., "MyCompany Inc.").
        year : int | None
            Copyright year. Defaults to current year.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not file_path.exists():
            return Result(
                success=False,
                message=f"File not found: {file_path}",
            )

        if year is None:
            year = datetime.now().year

        header = f"# Copyright {year} {copyright_text}"

        return self._add_header(file_path, header)

    def add_license_header(
        self,
        file_path: Path,
        license_name: str,
        copyright_holder: str | None = None,
        year: int | None = None,
    ) -> Result:
        """Add a license header to a file.

        Parameters
        ----------
        file_path : Path
            Path to the Python file.
        license_name : str
            License identifier (e.g., "MIT", "Apache-2.0", "GPL-3.0").
        copyright_holder : str | None
            Copyright holder name. If None, uses a placeholder.
        year : int | None
            Copyright year. Defaults to current year.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not file_path.exists():
            return Result(
                success=False,
                message=f"File not found: {file_path}",
            )

        if license_name not in LICENSE_HEADERS:
            return Result(
                success=False,
                message=f"Unknown license: {license_name}. Available: {', '.join(LICENSE_HEADERS.keys())}",
            )

        if year is None:
            year = datetime.now().year

        if copyright_holder is None:
            copyright_holder = "[Copyright Holder]"

        copyright_text = f"Copyright {year} {copyright_holder}"
        header = LICENSE_HEADERS[license_name].format(copyright=copyright_text)

        return self._add_header(file_path, header)

    def update_copyright_year(
        self,
        file_path: Path,
        new_year: int | None = None,
    ) -> Result:
        """Update the copyright year in a file's header.

        Updates patterns like:
        - "Copyright 2023" -> "Copyright 2023-2024"
        - "Copyright 2023-2024" -> "Copyright 2023-2025"

        Parameters
        ----------
        file_path : Path
            Path to the Python file.
        new_year : int | None
            Target year. Defaults to current year.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not file_path.exists():
            return Result(
                success=False,
                message=f"File not found: {file_path}",
            )

        if new_year is None:
            new_year = datetime.now().year

        try:
            content = file_path.read_text()
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to read {file_path}: {e}",
            )

        # Find copyright lines
        def update_year(match: re.Match) -> str:
            original = match.group(0)
            year_match = YEAR_PATTERN.search(original)

            if not year_match:
                return original

            start_year = year_match.group(1)
            end_year = year_match.group(2)

            start_year_int = int(start_year)

            if end_year:
                # Already has a range, update end year
                if int(end_year) >= new_year:
                    return original
                new_range = f"{start_year}-{new_year}"
            else:
                # Single year
                if start_year_int >= new_year:
                    return original
                elif start_year_int == new_year:
                    return original
                else:
                    new_range = f"{start_year}-{new_year}"

            return original.replace(year_match.group(0), new_range)

        new_content = COPYRIGHT_PATTERN.sub(update_year, content)

        if new_content == content:
            return Result(
                success=True,
                message=f"No copyright year updates needed in {file_path}",
            )

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would update copyright year in {file_path}",
                files_changed=[file_path],
            )

        try:
            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Updated copyright year in {file_path}",
                files_changed=[file_path],
            )
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to write {file_path}: {e}",
            )

    def has_header(self, file_path: Path) -> bool:
        """Check if a file already has a copyright/license header.

        Parameters
        ----------
        file_path : Path
            Path to the Python file.

        Returns
        -------
        bool
            True if the file has a header.
        """
        if not file_path.exists():
            return False

        try:
            content = file_path.read_text()
            # Check first few lines for copyright/license indicators
            first_lines = content.split("\n")[:10]
            for line in first_lines:
                line_lower = line.lower()
                if any(
                    keyword in line_lower
                    for keyword in ["copyright", "license", "spdx", "©", "(c)"]
                ):
                    return True
            return False
        except Exception:
            return False

    def _add_header(self, file_path: Path, header: str) -> Result:
        """Add a header to a file.

        The header is added after any shebang line and encoding declaration.
        """
        try:
            content = file_path.read_text()
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to read {file_path}: {e}",
            )

        # Check if header already exists
        if header.strip() in content:
            return Result(
                success=True,
                message=f"Header already exists in {file_path}",
            )

        lines = content.split("\n")
        insert_idx = 0

        # Skip shebang
        if lines and lines[0].startswith("#!"):
            insert_idx = 1

        # Skip encoding declaration
        if len(lines) > insert_idx:
            if lines[insert_idx].startswith("# -*- coding") or lines[insert_idx].startswith(
                "# coding"
            ):
                insert_idx += 1

        # Insert header
        header_lines = header.split("\n")
        for i, line in enumerate(header_lines):
            lines.insert(insert_idx + i, line)

        # Add blank line after header
        lines.insert(insert_idx + len(header_lines), "")

        new_content = "\n".join(lines)

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would add header to {file_path}",
                files_changed=[file_path],
            )

        try:
            file_path.write_text(new_content)
            return Result(
                success=True,
                message=f"Added header to {file_path}",
                files_changed=[file_path],
            )
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to write {file_path}: {e}",
            )


# Convenience functions


def add_copyright_header(
    rejig: Rejig,
    file_path: Path,
    copyright_text: str,
    year: int | None = None,
) -> Result:
    """Add a copyright header to a file.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the Python file.
    copyright_text : str
        Copyright holder text.
    year : int | None
        Copyright year.

    Returns
    -------
    Result
        Result of the operation.
    """
    manager = HeaderManager(rejig)
    return manager.add_copyright_header(file_path, copyright_text, year)


def add_license_header(
    rejig: Rejig,
    file_path: Path,
    license_name: str,
    copyright_holder: str | None = None,
    year: int | None = None,
) -> Result:
    """Add a license header to a file.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the Python file.
    license_name : str
        License identifier.
    copyright_holder : str | None
        Copyright holder name.
    year : int | None
        Copyright year.

    Returns
    -------
    Result
        Result of the operation.
    """
    manager = HeaderManager(rejig)
    return manager.add_license_header(file_path, license_name, copyright_holder, year)


def update_copyright_year(
    rejig: Rejig,
    file_path: Path,
    new_year: int | None = None,
) -> Result:
    """Update the copyright year in a file's header.

    Parameters
    ----------
    rejig : Rejig
        The parent Rejig instance.
    file_path : Path
        Path to the Python file.
    new_year : int | None
        Target year.

    Returns
    -------
    Result
        Result of the operation.
    """
    manager = HeaderManager(rejig)
    return manager.update_copyright_year(file_path, new_year)


def get_license_text(license_name: str) -> str | None:
    """Get the template text for a license header.

    Parameters
    ----------
    license_name : str
        License identifier.

    Returns
    -------
    str | None
        License header template, or None if unknown.
    """
    return LICENSE_HEADERS.get(license_name)
