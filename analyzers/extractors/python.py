"""Python AST extractor using Tree-sitter."""
import logging
from tree_sitter import Node
from analyzers.base import CodeSymbol, CodeRelationship, FileAnalysisResult
from analyzers.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


class PythonExtractor(BaseExtractor):
    """Extract symbols and relationships from Python code."""

    def analyze_file(self, file_path: str, root: Node, content: str) -> FileAnalysisResult:
        """Analyze Python file and extract all code intelligence."""
        symbols = []
        relationships = []
        imports = []

        # Extract everything in one traversal for efficiency
        self._traverse(root, content, file_path, symbols, relationships, imports, parent=None, context=None)

        return FileAnalysisResult(
            file_path=file_path,
            symbols=symbols,
            relationships=relationships,
            imports=imports
        )

    def _traverse(self, node: Node, content: str, file_path: str,
                  symbols: list, relationships: list, imports: list,
                  parent: str | None = None, context: str | None = None):
        """Recursively traverse AST and extract information."""

        # Extract function definitions
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = self._get_text(name_node)
                symbols.append(CodeSymbol(
                    name=func_name,
                    symbol_type="method" if parent else "function",
                    file_path=file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=self._extract_signature(node),
                    docstring=self._extract_python_docstring(node),
                    parent_symbol=parent
                ))

                # Process function body with this function as context
                for child in node.children:
                    self._traverse(child, content, file_path, symbols, relationships, imports, parent, func_name)
                return  # Don't traverse further from here

        # Extract class definitions
        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                class_name = self._get_text(name_node)
                symbols.append(CodeSymbol(
                    name=class_name,
                    symbol_type="class",
                    file_path=file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    docstring=self._extract_python_docstring(node)
                ))

                # Extract base classes (inheritance)
                bases = node.child_by_field_name("superclasses")
                if bases:
                    for base in bases.children:
                        if base.type == "identifier":
                            base_name = self._get_text(base)
                            relationships.append(CodeRelationship(
                                source_file=file_path,
                                source_symbol=class_name,
                                source_line=node.start_point[0] + 1,
                                target_file=None,
                                target_symbol=base_name,
                                relationship_type="inherits"
                            ))

                # Traverse methods with class as parent
                for child in node.children:
                    self._traverse(child, content, file_path, symbols, relationships, imports, class_name, context)
                return

        # Extract function calls
        elif node.type == "call":
            if context:  # Only track calls within functions
                function_node = node.child_by_field_name("function")
                if function_node:
                    callee = self._extract_call_name(function_node)
                    if callee:
                        relationships.append(CodeRelationship(
                            source_file=file_path,
                            source_symbol=context,
                            source_line=node.start_point[0] + 1,
                            target_file=None,
                            target_symbol=callee,
                            relationship_type="calls"
                        ))

        # Extract imports
        elif node.type == "import_statement":
            # import module
            for child in node.children:
                if child.type == "dotted_name":
                    module_name = self._get_text(child)
                    imports.append(module_name)
                    relationships.append(CodeRelationship(
                        source_file=file_path,
                        source_symbol="__module__",
                        source_line=node.start_point[0] + 1,
                        target_file=None,
                        target_symbol=module_name,
                        relationship_type="imports",
                        is_external=True
                    ))

        elif node.type == "import_from_statement":
            # from module import symbol
            module_node = node.child_by_field_name("module_name")
            if module_node:
                module_name = self._get_text(module_node)
                imports.append(module_name)
                relationships.append(CodeRelationship(
                    source_file=file_path,
                    source_symbol="__module__",
                    source_line=node.start_point[0] + 1,
                    target_file=None,
                    target_symbol=module_name,
                    relationship_type="imports",
                    is_external=True
                ))

        # Recurse to children
        for child in node.children:
            self._traverse(child, content, file_path, symbols, relationships, imports, parent, context)

    def _extract_signature(self, func_node: Node) -> str | None:
        """Extract function signature."""
        params_node = func_node.child_by_field_name("parameters")
        if params_node:
            return self._get_text(params_node)
        return None

    def _extract_python_docstring(self, node: Node) -> str | None:
        """Extract docstring from function/class."""
        body = node.child_by_field_name("body")
        if body and len(body.children) > 0:
            first_stmt = body.children[0]
            if first_stmt.type == "expression_statement":
                expr = first_stmt.children[0] if first_stmt.children else None
                if expr and expr.type == "string":
                    docstring = self._get_text(expr)
                    # Clean up quotes
                    return docstring.strip('"""').strip("'''").strip('"').strip("'").strip()
        return None

    def _extract_call_name(self, func_node: Node) -> str | None:
        """Extract the name being called."""
        if func_node.type == "identifier":
            return self._get_text(func_node)
        elif func_node.type == "attribute":
            # For obj.method() calls, get the method name
            attr = func_node.child_by_field_name("attribute")
            if attr:
                return self._get_text(attr)
        return None
