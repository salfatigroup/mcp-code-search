"""JavaScript/TypeScript AST analyzer using tree-sitter."""
import logging
from typing import Optional
from pathlib import Path

from analyzers.base import (
    ASTAnalyzer,
    CodeSymbol,
    CodeRelationship,
    FileAnalysisResult,
)

try:
    from tree_sitter import Language, Parser, Node
    import tree_sitter_javascript
    import tree_sitter_typescript
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

logger = logging.getLogger(__name__)


class JavaScriptAnalyzer(ASTAnalyzer):
    """AST analyzer for JavaScript/TypeScript files using tree-sitter."""

    JS_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs"}
    TS_EXTENSIONS = {".ts", ".tsx", ".mts", ".cts"}

    def __init__(self):
        if not TREE_SITTER_AVAILABLE:
            raise ImportError("tree-sitter not available")

        self.js_parser = Parser(Language(tree_sitter_javascript.language()))
        self.ts_parser = Parser(Language(tree_sitter_typescript.language_typescript()))
        self.tsx_parser = Parser(Language(tree_sitter_typescript.language_tsx()))

    def can_analyze(self, file_path: str) -> bool:
        """Check if this analyzer can handle JS/TS files."""
        return any(file_path.endswith(ext) for ext in self.JS_EXTENSIONS | self.TS_EXTENSIONS)

    def analyze(self, file_path: str, content: str) -> FileAnalysisResult:
        """Analyze a JavaScript/TypeScript file."""
        result = FileAnalysisResult(file_path=file_path)

        try:
            # Select parser based on file extension
            parser = self._get_parser(file_path)
            tree = parser.parse(bytes(content, "utf8"))

            visitor = JSVisitor(file_path, content)
            visitor.visit(tree.root_node)

            result.symbols = visitor.symbols
            result.relationships = visitor.relationships
            result.imports = visitor.imports
            result.summary = visitor.extract_file_summary(tree.root_node)

        except Exception as e:
            result.error = f"Analysis error: {e}"
            logger.error(f"Error analyzing {file_path}: {e}")

        return result

    def _get_parser(self, file_path: str) -> Parser:
        """Get the appropriate parser for the file."""
        if file_path.endswith(".tsx"):
            return self.tsx_parser
        elif any(file_path.endswith(ext) for ext in self.TS_EXTENSIONS):
            return self.ts_parser
        else:
            return self.js_parser


class JSVisitor:
    """Visitor to extract symbols and relationships from JS/TS AST."""

    def __init__(self, file_path: str, content: str):
        self.file_path = file_path
        self.content = content
        self.symbols: list[CodeSymbol] = []
        self.relationships: list[CodeRelationship] = []
        self.imports: list[str] = []
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None

    def visit(self, node: Node) -> None:
        """Visit a node and its children."""
        method_name = f"visit_{node.type}"
        method = getattr(self, method_name, self.generic_visit)
        method(node)

    def generic_visit(self, node: Node) -> None:
        """Visit all children of a node."""
        for child in node.children:
            self.visit(child)

    def extract_file_summary(self, root: Node) -> Optional[str]:
        """Extract file summary from comments at the top."""
        # Look for the first comment node
        for child in root.children:
            if child.type == "comment":
                comment_text = self._get_node_text(child)
                # Clean up comment markers
                comment_text = comment_text.replace("//", "").replace("/*", "").replace("*/", "").strip()
                if len(comment_text) > 10:  # Only meaningful comments
                    return comment_text[:200]
        return None

    def visit_import_statement(self, node: Node) -> None:
        """Handle ES6 import statements."""
        source_node = node.child_by_field_name("source")
        if source_node:
            module_name = self._get_node_text(source_node).strip("'\"")
            self.imports.append(module_name)
            self.relationships.append(
                CodeRelationship(
                    source_file=self.file_path,
                    source_symbol="<module>",
                    source_line=node.start_point[0] + 1,
                    target_file=None,
                    target_symbol=module_name,
                    relationship_type="imports",
                    is_external=not module_name.startswith("."),
                )
            )
        self.generic_visit(node)

    def visit_function_declaration(self, node: Node) -> None:
        """Handle function declarations."""
        name_node = node.child_by_field_name("name")
        if name_node:
            func_name = self._get_node_text(name_node)
            params = self._extract_parameters(node)

            symbol = CodeSymbol(
                name=func_name,
                symbol_type="function",
                file_path=self.file_path,
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
                signature=f"{func_name}({', '.join(params)})",
                parent_symbol=self.current_class,
            )
            self.symbols.append(symbol)

            previous_function = self.current_function
            self.current_function = func_name
            self.generic_visit(node)
            self.current_function = previous_function
        else:
            self.generic_visit(node)

    def visit_arrow_function(self, node: Node) -> None:
        """Handle arrow functions."""
        # Arrow functions may not have names unless they're assigned
        # We handle them in variable_declarator
        previous_function = self.current_function
        self.generic_visit(node)
        self.current_function = previous_function

    def visit_method_definition(self, node: Node) -> None:
        """Handle class method definitions."""
        name_node = node.child_by_field_name("name")
        if name_node:
            method_name = self._get_node_text(name_node)
            params = self._extract_parameters(node)

            symbol = CodeSymbol(
                name=method_name,
                symbol_type="method",
                file_path=self.file_path,
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
                signature=f"{method_name}({', '.join(params)})",
                parent_symbol=self.current_class,
            )
            self.symbols.append(symbol)

            previous_function = self.current_function
            self.current_function = method_name
            self.generic_visit(node)
            self.current_function = previous_function
        else:
            self.generic_visit(node)

    def visit_class_declaration(self, node: Node) -> None:
        """Handle class declarations."""
        name_node = node.child_by_field_name("name")
        if name_node:
            class_name = self._get_node_text(name_node)

            symbol = CodeSymbol(
                name=class_name,
                symbol_type="class",
                file_path=self.file_path,
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
            )
            self.symbols.append(symbol)

            # Check for inheritance
            heritage_node = node.child_by_field_name("heritage")
            if heritage_node:
                for child in heritage_node.children:
                    if child.type == "identifier":
                        base_class = self._get_node_text(child)
                        self.relationships.append(
                            CodeRelationship(
                                source_file=self.file_path,
                                source_symbol=class_name,
                                source_line=node.start_point[0] + 1,
                                target_file=None,
                                target_symbol=base_class,
                                relationship_type="inherits",
                            )
                        )

            previous_class = self.current_class
            self.current_class = class_name
            self.generic_visit(node)
            self.current_class = previous_class
        else:
            self.generic_visit(node)

    def visit_call_expression(self, node: Node) -> None:
        """Handle function calls."""
        if not self.current_function and not self.current_class:
            self.generic_visit(node)
            return

        function_node = node.child_by_field_name("function")
        if function_node:
            called_name = self._extract_call_name(function_node)
            if called_name:
                source_symbol = self.current_function or self.current_class or "<module>"
                self.relationships.append(
                    CodeRelationship(
                        source_file=self.file_path,
                        source_symbol=source_symbol,
                        source_line=node.start_point[0] + 1,
                        target_file=None,
                        target_symbol=called_name,
                        relationship_type="calls",
                    )
                )

        self.generic_visit(node)

    def _extract_call_name(self, node: Node) -> Optional[str]:
        """Extract function name from call expression."""
        if node.type == "identifier":
            return self._get_node_text(node)
        elif node.type == "member_expression":
            parts = []
            current = node
            while current.type == "member_expression":
                prop = current.child_by_field_name("property")
                if prop:
                    parts.append(self._get_node_text(prop))
                current = current.child_by_field_name("object")
            if current and current.type == "identifier":
                parts.append(self._get_node_text(current))
            return ".".join(reversed(parts))
        return None

    def _extract_parameters(self, node: Node) -> list[str]:
        """Extract parameter names from a function."""
        params = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for child in params_node.children:
                if child.type in ("identifier", "required_parameter"):
                    params.append(self._get_node_text(child))
        return params

    def _get_node_text(self, node: Node) -> str:
        """Get the text content of a node."""
        return self.content[node.start_byte:node.end_byte]
