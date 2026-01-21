"""Stub file (.pyi) generation utilities.

Generates type stub files from Python source code.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import libcst as cst

if TYPE_CHECKING:
    from rejig.core.rejig import Rejig

from rejig.core.results import Result


class StubGenerator:
    """Generate type stub files from Python source code.

    Extracts function signatures, class definitions, and type annotations
    to create .pyi stub files.
    """

    def __init__(self, rejig: Rejig) -> None:
        self._rejig = rejig

    def generate_stub(self, source_path: Path) -> str:
        """Generate stub content for a Python file.

        Parameters
        ----------
        source_path : Path
            Path to the Python source file.

        Returns
        -------
        str
            The stub file content.
        """
        content = source_path.read_text()
        tree = cst.parse_module(content)

        # Use MetadataWrapper to walk the tree
        wrapper = cst.MetadataWrapper(tree)
        extractor = _StubExtractor(tree)

        # Walk the tree manually by visiting body
        for node in tree.body:
            extractor.visit(node)

        return extractor.get_stub()

    def generate_for_file(self, source_path: Path, output_dir: Path | None = None) -> Result:
        """Generate a stub file for a Python file.

        Parameters
        ----------
        source_path : Path
            Path to the Python source file.
        output_dir : Path | None
            Output directory for the stub file. If None, places the stub
            alongside the source file.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not source_path.exists():
            return Result(
                success=False,
                message=f"Source file not found: {source_path}",
            )

        try:
            stub_content = self.generate_stub(source_path)

            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                stub_path = output_dir / source_path.with_suffix(".pyi").name
            else:
                stub_path = source_path.with_suffix(".pyi")

            if self._rejig.dry_run:
                return Result(
                    success=True,
                    message=f"[DRY RUN] Would generate stub file {stub_path}",
                    files_changed=[stub_path],
                )

            stub_path.write_text(stub_content)
            return Result(
                success=True,
                message=f"Generated stub file {stub_path}",
                files_changed=[stub_path],
            )
        except Exception as e:
            return Result(
                success=False,
                message=f"Failed to generate stub: {e}",
            )

    def generate_for_package(
        self, package_path: Path, output_dir: Path | None = None
    ) -> Result:
        """Generate stub files for all modules in a package.

        Parameters
        ----------
        package_path : Path
            Path to the package directory.
        output_dir : Path | None
            Output directory for stub files. If None, uses a 'stubs/'
            directory next to the package.

        Returns
        -------
        Result
            Result of the operation.
        """
        if not package_path.is_dir():
            return Result(
                success=False,
                message=f"Package not found: {package_path}",
            )

        if output_dir is None:
            output_dir = package_path.parent / "stubs" / package_path.name
        else:
            output_dir = output_dir / package_path.name

        files_changed: list[Path] = []
        errors: list[str] = []

        # Process all Python files recursively
        for py_file in package_path.rglob("*.py"):
            relative = py_file.relative_to(package_path)
            stub_dir = output_dir / relative.parent
            stub_path = stub_dir / relative.with_suffix(".pyi").name

            try:
                stub_content = self.generate_stub(py_file)

                if self._rejig.dry_run:
                    files_changed.append(stub_path)
                    continue

                stub_dir.mkdir(parents=True, exist_ok=True)
                stub_path.write_text(stub_content)
                files_changed.append(stub_path)
            except Exception as e:
                errors.append(f"{py_file}: {e}")

        if errors:
            return Result(
                success=False,
                message=f"Generated stubs with {len(errors)} errors: {'; '.join(errors)}",
                files_changed=files_changed,
            )

        if self._rejig.dry_run:
            return Result(
                success=True,
                message=f"[DRY RUN] Would generate {len(files_changed)} stub files to {output_dir}",
                files_changed=files_changed,
            )

        return Result(
            success=True,
            message=f"Generated {len(files_changed)} stub files in {output_dir}",
            files_changed=files_changed,
        )


class _StubExtractor:
    """Extract stub information from a CST."""

    def __init__(self, module: cst.Module) -> None:
        self._module = module
        self._lines: list[str] = []
        self._imports: set[str] = set()
        self._indent = 0

    def _indent_str(self) -> str:
        return "    " * self._indent

    def get_stub(self) -> str:
        """Get the generated stub content."""
        header = []

        # Add typing imports if we have any
        typing_names = {"Any", "Callable", "Optional", "Union", "List", "Dict", "Tuple"}
        used_typing = typing_names & self._imports
        if used_typing:
            header.append(f"from typing import {', '.join(sorted(used_typing))}")
            header.append("")

        return "\n".join(header + self._lines)

    def visit(self, node: cst.CSTNode) -> None:
        """Visit a node and extract stub information."""
        if isinstance(node, cst.SimpleStatementLine):
            self._visit_simple_statement(node)
        elif isinstance(node, cst.ClassDef):
            self._visit_class(node)
        elif isinstance(node, cst.FunctionDef):
            self._visit_function(node)

    def _visit_simple_statement(self, node: cst.SimpleStatementLine) -> None:
        """Handle imports and module-level assignments."""
        for stmt in node.body:
            if isinstance(stmt, (cst.Import, cst.ImportFrom)):
                code = self._module.code_for_node(stmt)
                self._lines.append(code.strip())
            elif isinstance(stmt, cst.AnnAssign):
                code = self._module.code_for_node(stmt)
                self._lines.append(f"{self._indent_str()}{code.strip()}")

    def _visit_class(self, node: cst.ClassDef) -> None:
        """Handle class definition."""
        # Add decorators
        for decorator in node.decorators:
            dec_code = self._module.code_for_node(decorator)
            self._lines.append(f"{self._indent_str()}{dec_code.strip()}")

        # Class header
        bases = ""
        if node.bases:
            # Extract base class names from Arg nodes
            bases_list = [self._module.code_for_node(base.value).strip() for base in node.bases]
            bases = f"({', '.join(bases_list)})"

        self._lines.append(f"{self._indent_str()}class {node.name.value}{bases}:")

        self._indent += 1

        # Process class body
        has_content = False
        if isinstance(node.body, cst.IndentedBlock):
            for stmt in node.body.body:
                if isinstance(stmt, cst.SimpleStatementLine):
                    # Handle class-level assignments (including type annotations)
                    for s in stmt.body:
                        if isinstance(s, cst.AnnAssign):
                            code = self._module.code_for_node(s)
                            self._lines.append(f"{self._indent_str()}{code.strip()}")
                            has_content = True
                elif isinstance(stmt, cst.FunctionDef):
                    self._visit_function(stmt)
                    has_content = True

        # If no methods or assignments, add '...'
        if not has_content:
            self._lines.append(f"{self._indent_str()}...")

        self._indent -= 1
        self._lines.append("")

    def _visit_function(self, node: cst.FunctionDef) -> None:
        """Handle function/method definition."""
        # Add decorators
        for decorator in node.decorators:
            dec_code = self._module.code_for_node(decorator)
            self._lines.append(f"{self._indent_str()}{dec_code.strip()}")

        # Build signature
        params = self._extract_params(node.params)
        return_type = ""
        if node.returns:
            return_type = f" -> {self._module.code_for_node(node.returns.annotation).strip()}"

        self._lines.append(f"{self._indent_str()}def {node.name.value}({params}){return_type}: ...")

    def _extract_params(self, params: cst.Parameters) -> str:
        """Extract parameter string with types."""
        parts: list[str] = []

        for param in params.params:
            p = param.name.value
            if param.annotation:
                ann = self._module.code_for_node(param.annotation.annotation).strip()
                p = f"{p}: {ann}"
            if param.default:
                default = self._module.code_for_node(param.default).strip()
                # Use '...' for complex defaults in stubs
                if len(default) > 10 or "\n" in default:
                    default = "..."
                p = f"{p} = {default}"
            parts.append(p)

        if params.star_arg and isinstance(params.star_arg, cst.Param):
            p = f"*{params.star_arg.name.value}"
            if params.star_arg.annotation:
                ann = self._module.code_for_node(params.star_arg.annotation.annotation).strip()
                p = f"{p}: {ann}"
            parts.append(p)
        elif isinstance(params.star_arg, cst.ParamStar):
            # Bare * separator for keyword-only args
            parts.append("*")

        for param in params.kwonly_params:
            p = param.name.value
            if param.annotation:
                ann = self._module.code_for_node(param.annotation.annotation).strip()
                p = f"{p}: {ann}"
            if param.default:
                default = self._module.code_for_node(param.default).strip()
                if len(default) > 10 or "\n" in default:
                    default = "..."
                p = f"{p} = {default}"
            parts.append(p)

        if params.star_kwarg:
            p = f"**{params.star_kwarg.name.value}"
            if params.star_kwarg.annotation:
                ann = self._module.code_for_node(params.star_kwarg.annotation.annotation).strip()
                p = f"{p}: {ann}"
            parts.append(p)

        return ", ".join(parts)
