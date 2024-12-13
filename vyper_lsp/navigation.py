import logging
import re
from lsprotocol.types import Position, Range
from typing import List, Optional

from pygls.workspace import Document
from vyper.ast import FlagDef, FunctionDef, VyperNode
from vyper_lsp.ast import AST
from vyper_lsp.utils import (
    get_expression_at_cursor,
    get_word_at_cursor,
    range_from_node,
)

ENUM_VARIANT_PATTERN = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)")

logger = logging.getLogger("vyper-lsp")


# this class should abstract away all the AST stuff
# and just provide a simple interface for navigation
#
# the navigator should mainly return Ranges
class ASTNavigator:
    def __init__(self, ast: AST):
        self.ast = ast

    def _find_state_variable_declaration(self, word: str) -> Optional[Range]:
        node = self.ast.find_state_variable_declaration_node_for_name(word)
        if node:
            return range_from_node(node)

        return None

    def _find_variable_declaration_under_node(
        self, node: VyperNode, symbol: str
    ) -> Optional[Range]:
        decl_node = AST.from_node(node).find_node_declaring_symbol(symbol)
        if decl_node:
            return range_from_node(decl_node)

        return None

    def _find_function_declaration(self, word: str) -> Optional[Range]:
        node = self.ast.find_function_declaration_node_for_name(word)
        if node:
            return range_from_node(node)

        return None

    def find_type_declaration(self, word: str) -> Optional[Range]:
        node = self.ast.find_type_declaration_node_for_name(word)
        if node:
            return range_from_node(node)

        return None

    def _is_state_var_decl(self, line, word):
        is_top_level = not line[0].isspace()
        is_state_variable = word in self.ast.get_state_variables()
        return is_top_level and is_state_variable

    def _is_constant_decl(self, line, word):
        is_constant = "constant(" in line
        return is_constant and self._is_state_var_decl(line, word)

    def _is_internal_fn(self, line, word, expression):
        is_def = line.startswith("def")
        is_internal_call = expression.startswith("self.")
        is_internal_fn = word in self.ast.get_internal_functions()
        return is_def and (is_internal_call or is_internal_fn)

    def find_references(self, doc: Document, pos: Position) -> List[Range]:
        # REVIEW: return is stylistically slightly different from ast analyzer
        if self.ast.ast_data is None:
            return []

        og_line = doc.lines[pos.line]
        word = get_word_at_cursor(og_line, pos.character)
        expression = get_expression_at_cursor(og_line, pos.character)
        top_level_node = self.ast.find_top_level_node_at_pos(pos)

        def finalize(refs):
            return [range_from_node(ref) for ref in refs]

        if word in self.ast.get_enums():
            return finalize(self.ast.find_nodes_referencing_enum(word))

        if word in self.ast.get_structs() or word in self.ast.get_events():
            return finalize(self.ast.find_nodes_referencing_struct(word))

        if self._is_internal_fn(og_line, word, expression):
            return finalize(self.ast.find_nodes_referencing_internal_function(word))

        if self._is_constant_decl(og_line, word):
            return finalize(self.ast.find_nodes_referencing_constant(word))

        if self._is_state_var_decl(og_line, word):
            return finalize(self.ast.find_nodes_referencing_state_variable(word))

        if isinstance(top_level_node, FlagDef):
            return finalize(
                self.ast.find_nodes_referencing_enum_variant(top_level_node.name, word)
            )

        if isinstance(top_level_node, FunctionDef):
            return finalize(
                AST.from_node(top_level_node).find_nodes_referencing_symbol(word)
            )

        return []

    def _match_enum_variant(self, full_word: str) -> Optional[re.Match]:
        match_ = ENUM_VARIANT_PATTERN.match(full_word)

        if (
            match_
            and match_.group(1) in self.ast.get_enums()
            and match_.group(2) in self.ast.get_enum_variants(match_.group(1))
        ):
            return match_

        return None

    def find_declaration(self, document: Document, pos: Position) -> Optional[Range]:
        if self.ast.ast_data is None:
            return None

        line_content = document.lines[pos.line]
        word = get_word_at_cursor(line_content, pos.character)
        full_word = get_expression_at_cursor(line_content, pos.character)
        top_level_node = self.ast.find_top_level_node_at_pos(pos)

        # Determine the type of declaration and find it
        if full_word.startswith("self."):
            if word in self.ast.functions:
                return self._find_function_declaration(word)
            else:
                return self._find_state_variable_declaration(word)
        elif word in self.ast.get_user_defined_types():
            return self.find_type_declaration(word)
        elif word in self.ast.get_events():
            return self.find_type_declaration(word)
        elif word in self.ast.get_constants():
            return self._find_state_variable_declaration(word)
        elif isinstance(top_level_node, FunctionDef):
            range_ = self._find_variable_declaration_under_node(top_level_node, word)
            if range_:
                return range_

            match_ = self._match_enum_variant(full_word)
            if match_:
                return self.find_type_declaration(match_.group(1))

        return None

    def find_implementation(self, document: Document, pos: Position) -> Optional[Range]:
        og_line = document.lines[pos.line]
        word = get_word_at_cursor(og_line, pos.character)
        expression = get_expression_at_cursor(og_line, pos.character)

        if expression.startswith("self."):
            # TODO: This only supports local-module internal fns currently
            if word not in self.ast.functions:
                return None
            return self._find_function_declaration(word)

        # TODO: should be looking up by alias to find implementation for imported fns

        # TODO: this should check that we implement this interface before
        # trying to find an implementation for the given function
        if og_line[0].isspace() and og_line.strip().startswith("def"):
            # only lookup external fns if we're in an interface def
            return self._find_function_declaration(word)

        return None
