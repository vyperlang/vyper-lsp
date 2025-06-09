import logging
import re
from typing import Optional
from packaging.version import Version
from lsprotocol.types import (
    Position,
)
from pygls.workspace import Document
from vyper.ast import nodes
from vyper_lsp.ast import AST
from vyper_lsp.utils import (
    get_expression_at_cursor,
    get_word_at_cursor,
)

pattern_text = r"(.+) is deprecated\. Please use `(.+)` instead\."
deprecation_pattern = re.compile(pattern_text)

min_vyper_version = Version("0.4.0")

logger = logging.getLogger("vyper-lsp")


class HoverHandler:
    def __init__(self, ast: AST) -> None:
        self.ast = ast

    def _format_fn_signature(self, node: nodes.FunctionDef) -> str:
        pattern = r"def\s+(\w+)\((?:[^()]|\n)*\)(?:\s*->\s*[\w\[\], \n]+)?:"
        match = re.search(pattern, node.node_source_code, re.MULTILINE)
        if match:
            function_def = match.group()
            return f"(Internal Function) {function_def}"

    def _is_internal_fn(self, expression: str):
        if not expression.startswith("self."):
            return False
        fn_name = expression.split("self.")[-1]
        return fn_name in self.ast.functions and self.ast.functions[fn_name].is_internal

    def _is_state_var(self, expression: str):
        if not expression.startswith("self."):
            return False
        var_name = expression.split("self.")[-1]
        return var_name in self.ast.variables

    def hover_info(self, doc: Document, pos: Position) -> Optional[str]:
        if len(doc.lines) < pos.line:
            return None

        og_line = doc.lines[pos.line]
        word = get_word_at_cursor(og_line, pos.character)
        full_word = get_expression_at_cursor(og_line, pos.character)

        # Check for module references (e.g., "lib.function" or "lib.variable")
        if "." in full_word and not full_word.startswith("self."):
            parts = full_word.split(".")
            if len(parts) == 2:
                module_name, member_name = parts
                if module_name in self.ast.imports:
                    module = self.ast.imports[module_name]
                    if hasattr(module, "functions") and member_name in module.functions:
                        fn = module.functions[member_name]
                        return f"(Module Function) **{module_name}.{member_name}**"
                    elif hasattr(module, "variables") and member_name in module.variables:
                        var = module.variables[member_name]
                        return f"(Module Variable) **{module_name}.{member_name}**"

        if self._is_internal_fn(full_word):
            node = self.ast.find_function_declaration_node_for_name(word)
            return node and self._format_fn_signature(node)

        if self._is_state_var(full_word):
            node = self.ast.find_state_variable_declaration_node_for_name(word)
            if not node:
                return None
            variable_type = node.annotation.id
            return f"(State Variable) **{word}** : **{variable_type}**"

        if word in self.ast.get_structs():
            node = self.ast.find_type_declaration_node_for_name(word)
            return node and f"(Struct) **{word}**"

        if word in self.ast.get_enums():
            node = self.ast.find_type_declaration_node_for_name(word)
            return node and f"(Enum) **{word}**"

        if word in self.ast.get_events():
            node = self.ast.find_type_declaration_node_for_name(word)
            return node and f"(Event) **{word}**"

        if word in self.ast.get_constants():
            node = self.ast.find_state_variable_declaration_node_for_name(word)
            if not node:
                return None

            variable_type = node.annotation.id
            return f"(Constant) **{word}** : **{variable_type}**"

        return None
