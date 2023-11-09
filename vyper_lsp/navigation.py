import re
from pygls.lsp.types.language_features import Position, Range
from typing import List, Optional

from pygls.workspace import Document
from vyper.ast import EnumDef, FunctionDef, VyperNode
from vyper_lsp.ast import AST
from vyper_lsp.utils import get_expression_at_cursor, get_word_at_cursor

ENUM_VARIANT_PATTERN = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)")


# this class should abstract away all the AST stuff
# and just provide a simple interface for navigation
#
# the navigator should mainly return Ranges
class ASTNavigator:
    def __init__(self, ast):
        self.ast = ast

    def find_state_variable_declaration(self, word: str) -> Optional[Range]:
        node = self.ast.find_state_variable_declaration_node_for_name(word)
        if node:
            range = Range(
                start=Position(line=node.lineno - 1, character=node.col_offset),
                end=Position(line=node.end_lineno - 1, character=node.end_col_offset),
            )
            return range

    def find_variable_declaration_under_node(
        self, node: VyperNode, symbol: str
    ) -> Optional[Range]:
        decl_node = AST.from_node(node).find_node_declaring_symbol(symbol)
        if decl_node:
            range = Range(
                start=Position(
                    line=decl_node.lineno - 1, character=decl_node.col_offset
                ),
                end=Position(
                    line=decl_node.end_lineno - 1, character=decl_node.end_col_offset
                ),
            )
            return range

    def find_function_declaration(self, word: str) -> Optional[Range]:
        node = self.ast.find_function_declaration_node_for_name(word)
        if node:
            range = Range(
                start=Position(line=node.lineno - 1, character=node.col_offset),
                end=Position(line=node.end_lineno - 1, character=node.end_col_offset),
            )
            return range

    def find_type_declaration(self, word: str) -> Optional[Range]:
        node = self.ast.find_type_declaration_node_for_name(word)
        if node:
            range = Range(
                start=Position(line=node.lineno - 1, character=node.col_offset),
                end=Position(line=node.end_lineno - 1, character=node.end_col_offset),
            )
            return range

    def find_references(self, doc: Document, pos: Position) -> List[Range]:
        og_line = doc.lines[pos.line]
        word = get_word_at_cursor(og_line, pos.character)
        expression = get_expression_at_cursor(og_line, pos.character)
        if self.ast.ast_data is None:
            return []
        references = []

        top_level_node = self.ast.find_top_level_node_at_pos(pos)

        if word in self.ast.get_enums():
            # find all references to this type
            refs = self.ast.find_nodes_referencing_enum(word)
            for ref in refs:
                range = Range(
                    start=Position(line=ref.lineno - 1, character=ref.col_offset),
                    end=Position(line=ref.end_lineno - 1, character=ref.end_col_offset),
                )
                references.append(range)
        elif word in self.ast.get_structs() or word in self.ast.get_events():
            refs = self.ast.find_nodes_referencing_struct(word)
            for ref in refs:
                range = Range(
                    start=Position(line=ref.lineno - 1, character=ref.col_offset),
                    end=Position(line=ref.end_lineno - 1, character=ref.end_col_offset),
                )
                references.append(range)
        elif word in self.ast.get_internal_functions() and (
            og_line.startswith("def") or expression.startswith("self.")
        ):
            refs = self.ast.find_nodes_referencing_internal_function(word)
            for ref in refs:
                range = Range(
                    start=Position(line=ref.lineno - 1, character=ref.col_offset),
                    end=Position(line=ref.end_lineno - 1, character=ref.end_col_offset),
                )
                references.append(range)
        elif not og_line[0].isspace() and word in self.ast.get_state_variables():
            if "constant(" in og_line:
                refs = self.ast.find_nodes_referencing_constant(word)
            else:
                refs = self.ast.find_nodes_referencing_state_variable(word)
            for ref in refs:
                range = Range(
                    start=Position(line=ref.lineno - 1, character=ref.col_offset),
                    end=Position(line=ref.end_lineno - 1, character=ref.end_col_offset),
                )
                references.append(range)
        elif isinstance(top_level_node, EnumDef):
            # find all references to this enum variant
            refs = self.ast.find_nodes_referencing_enum_variant(
                top_level_node.name, word
            )
            for ref in refs:
                range = Range(
                    start=Position(line=ref.lineno - 1, character=ref.col_offset),
                    end=Position(line=ref.end_lineno - 1, character=ref.end_col_offset),
                )
                references.append(range)
        elif isinstance(top_level_node, FunctionDef):
            refs = AST.from_node(top_level_node).find_nodes_referencing_symbol(word)
            for ref in refs:
                range = Range(
                    start=Position(line=ref.lineno - 1, character=ref.col_offset),
                    end=Position(line=ref.end_lineno - 1, character=ref.end_col_offset),
                )
                references.append(range)
        return references

    def find_declaration(self, document: Document, pos: Position) -> Optional[Range]:
        if self.ast.ast_data is None:
            return None

        line_content = document.lines[pos.line]
        word = get_word_at_cursor(line_content, pos.character)
        full_word = get_expression_at_cursor(line_content, pos.character)
        top_level_node = self.ast.find_top_level_node_at_pos(pos)

        print(f"word: {word} events: {self.ast.get_events()}")
        # Determine the type of declaration and find it
        if full_word.startswith("self."):
            if "(" in full_word:
                return self.find_function_declaration(word)
            else:
                return self.find_state_variable_declaration(word)
        elif word in self.ast.get_user_defined_types():
            return self.find_type_declaration(word)
        elif word in self.ast.get_events():
            print(f"finding event declaration for {word}")
            return self.find_type_declaration(word)
        elif word in self.ast.get_constants():
            return self.find_state_variable_declaration(word)
        elif isinstance(top_level_node, FunctionDef):
            range = self.find_variable_declaration_under_node(top_level_node, word)
            if range:
                return range
            else:
                match = ENUM_VARIANT_PATTERN.match(full_word)
                if (
                    match
                    and match.group(1) in self.ast.get_enums()
                    and match.group(2) in self.ast.get_enum_variants(match.group(1))
                ):
                    return self.find_type_declaration(match.group(1))

    def find_implementation(self, document: Document, pos: Position) -> Optional[Range]:
        og_line = document.lines[pos.line]
        word = get_word_at_cursor(og_line, pos.character)
        expression = get_expression_at_cursor(og_line, pos.character)

        if "(" not in expression:
            return None

        if expression.startswith("self."):
            return self.find_function_declaration(word)
        elif og_line[0].isspace() and og_line.strip().startswith("def"):
            # only lookup external fns if we're in an interface def
            return self.find_function_declaration(word)
        else:
            return None
