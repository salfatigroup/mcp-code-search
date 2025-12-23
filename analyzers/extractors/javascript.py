"""JavaScript/TypeScript AST extractor using Tree-sitter."""
import logging
from tree_sitter import Node
from analyzers.base import CodeSymbol, CodeRelationship, FileAnalysisResult
from analyzers.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


class JavaScriptExtractor(BaseExtractor):
    """Extract symbols and relationships from JavaScript/TypeScript code."""

    def analyze_file(self, file_path: str, root: Node, content: str) -> FileAnalysisResult:
        """Analyze JS/TS file and extract all code intelligence."""
        symbols = []
        relationships = []
        imports = []

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
        """Recursively traverse AST."""

        # Function declarations
        if node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = self._get_text(name_node)
                symbols.append(CodeSymbol(
                    name=func_name,
                    symbol_type="function",
                    file_path=file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    signature=self._extract_signature(node),
                    parent_symbol=parent
                ))

                # Process body with this function as context
                for child in node.children:
                    self._traverse(child, content, file_path, symbols, relationships, imports, parent, func_name)
                return

        # Arrow functions assigned to variables
        elif node.type == "lexical_declaration":
            # const/let functionName = () => {}
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    value_node = child.child_by_field_name("value")
                    if name_node and value_node and value_node.type in ("arrow_function", "function"):
                        func_name = self._get_text(name_node)
                        symbols.append(CodeSymbol(
                            name=func_name,
                            symbol_type="function",
                            file_path=file_path,
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            parent_symbol=parent
                        ))

        # Class declarations
        elif node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                class_name = self._get_text(name_node)
                symbols.append(CodeSymbol(
                    name=class_name,
                    symbol_type="class",
                    file_path=file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1
                ))

                # Traverse methods with class as parent
                for child in node.children:
                    self._traverse(child, content, file_path, symbols, relationships, imports, class_name, context)
                return

        # Method definitions
        elif node.type == "method_definition":
            name_node = node.child_by_field_name("name")
            if name_node and parent:
                method_name = self._get_text(name_node)
                symbols.append(CodeSymbol(
                    name=method_name,
                    symbol_type="method",
                    file_path=file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    parent_symbol=parent
                ))

                # Process body with this method as context
                for child in node.children:
                    self._traverse(child, content, file_path, symbols, relationships, imports, parent, method_name)
                return

        # Function calls
        elif node.type == "call_expression":
            if context:
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

        # ES6 imports
        elif node.type == "import_statement":
            source_node = node.child_by_field_name("source")
            if source_node:
                module = self._get_text(source_node).strip('"').strip("'")
                imports.append(module)
                relationships.append(CodeRelationship(
                    source_file=file_path,
                    source_symbol="__module__",
                    source_line=node.start_point[0] + 1,
                    target_file=None,
                    target_symbol=module,
                    relationship_type="imports",
                    is_external=True
                ))

        # CommonJS require
        elif node.type == "call_expression":
            func = node.child_by_field_name("function")
            if func and self._get_text(func) == "require":
                args = node.child_by_field_name("arguments")
                if args and len(args.children) > 0:
                    module = self._get_text(args.children[0]).strip('"').strip("'")
                    imports.append(module)

        # Recurse
        for child in node.children:
            self._traverse(child, content, file_path, symbols, relationships, imports, parent, context)

    def _extract_signature(self, func_node: Node) -> str | None:
        """Extract function signature."""
        params_node = func_node.child_by_field_name("parameters")
        if params_node:
            return self._get_text(params_node)
        return None

    def _extract_call_name(self, func_node: Node) -> str | None:
        """Extract the name being called."""
        if func_node.type == "identifier":
            return self._get_text(func_node)
        elif func_node.type == "member_expression":
            # For obj.method() calls
            prop = func_node.child_by_field_name("property")
            if prop:
                return self._get_text(prop)
        return None
