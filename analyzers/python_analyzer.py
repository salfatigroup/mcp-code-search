"""Python AST analyzer using Python's built-in ast module."""
import ast
import logging
from typing import Optional

from analyzers.base import (
    ASTAnalyzer,
    CodeSymbol,
    CodeRelationship,
    FileAnalysisResult,
)

logger = logging.getLogger(__name__)


class PythonASTAnalyzer(ASTAnalyzer):
    """AST analyzer for Python files using the ast module."""

    PYTHON_EXTENSIONS = {".py", ".pyw"}

    def can_analyze(self, file_path: str) -> bool:
        """Check if this analyzer can handle Python files."""
        return any(file_path.endswith(ext) for ext in self.PYTHON_EXTENSIONS)

    def analyze(self, file_path: str, content: str) -> FileAnalysisResult:
        """Analyze a Python file and extract symbols and relationships."""
        result = FileAnalysisResult(file_path=file_path)

        try:
            tree = ast.parse(content, filename=file_path)
            result.summary = ast.get_docstring(tree)

            visitor = PythonVisitor(file_path)
            visitor.visit(tree)

            result.symbols = visitor.symbols
            result.relationships = visitor.relationships
            result.imports = visitor.imports

        except SyntaxError as e:
            result.error = f"Syntax error: {e}"
            logger.debug(f"Failed to parse {file_path}: {e}")
        except Exception as e:
            result.error = f"Analysis error: {e}"
            logger.error(f"Error analyzing {file_path}: {e}")

        return result


class PythonVisitor(ast.NodeVisitor):
    """AST visitor to extract symbols and relationships from Python code."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.symbols: list[CodeSymbol] = []
        self.relationships: list[CodeRelationship] = []
        self.imports: list[str] = []
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import x' statements."""
        for alias in node.names:
            module_name = alias.name
            self.imports.append(module_name)
            self.relationships.append(
                CodeRelationship(
                    source_file=self.file_path,
                    source_symbol="<module>",
                    source_line=node.lineno,
                    target_file=None,
                    target_symbol=module_name,
                    relationship_type="imports",
                    is_external=True,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from x import y' statements."""
        if node.module:
            self.imports.append(node.module)
            for alias in node.names:
                imported_name = alias.name
                self.relationships.append(
                    CodeRelationship(
                        source_file=self.file_path,
                        source_symbol="<module>",
                        source_line=node.lineno,
                        target_file=None,
                        target_symbol=f"{node.module}.{imported_name}",
                        relationship_type="imports",
                        is_external=True,
                    )
                )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Handle function definitions."""
        parent_symbol = self.current_class
        symbol_type = "method" if parent_symbol else "function"

        # Build signature
        args = [arg.arg for arg in node.args.args]
        signature = f"{node.name}({', '.join(args)})"

        symbol = CodeSymbol(
            name=node.name,
            symbol_type=symbol_type,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            signature=signature,
            docstring=ast.get_docstring(node),
            parent_symbol=parent_symbol,
        )
        self.symbols.append(symbol)

        # Track current function for call analysis
        previous_function = self.current_function
        self.current_function = node.name

        # Visit function body to find calls
        self.generic_visit(node)

        self.current_function = previous_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Handle async function definitions."""
        # Treat async functions the same as regular functions
        self.visit_FunctionDef(node)  # type: ignore

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Handle class definitions."""
        symbol = CodeSymbol(
            name=node.name,
            symbol_type="class",
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node),
        )
        self.symbols.append(symbol)

        # Track inheritance
        for base in node.bases:
            if isinstance(base, ast.Name):
                self.relationships.append(
                    CodeRelationship(
                        source_file=self.file_path,
                        source_symbol=node.name,
                        source_line=node.lineno,
                        target_file=None,
                        target_symbol=base.id,
                        relationship_type="inherits",
                    )
                )

        # Visit class body with current class context
        previous_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = previous_class

    def visit_Call(self, node: ast.Call) -> None:
        """Handle function/method calls."""
        if not self.current_function and not self.current_class:
            # Skip module-level calls for now (they're complex)
            self.generic_visit(node)
            return

        source_symbol = self.current_function or self.current_class or "<module>"

        # Extract called function name
        called_name = self._extract_call_name(node.func)

        if called_name:
            self.relationships.append(
                CodeRelationship(
                    source_file=self.file_path,
                    source_symbol=source_symbol,
                    source_line=node.lineno,
                    target_file=None,  # Will be resolved later
                    target_symbol=called_name,
                    relationship_type="calls",
                )
            )

        self.generic_visit(node)

    def _extract_call_name(self, node: ast.expr) -> Optional[str]:
        """Extract the function name from a call expression."""
        if isinstance(node, ast.Name):
            # Simple function call: func()
            return node.id
        elif isinstance(node, ast.Attribute):
            # Method call or module function: obj.method() or module.func()
            parts = []
            current = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None
