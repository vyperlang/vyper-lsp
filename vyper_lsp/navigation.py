import re
import sys
from pygls.lsp.types.language_features import Location, Position, Range
from typing import List, Optional

from pygls.workspace import Document
from vyper_lsp.ast import AST
from vyper_lsp.utils import get_expression_at_cursor, get_word_at_cursor

# this class should abstract away all the AST stuff
# and just provide a simple interface for navigation
#
# the navigator should mainly return Ranges
class Navigator:
    def __init__(self, ast=None):
        self.ast = ast or AST()

    def find_state_variable_declaration(self, word: str) -> Optional[Range]:
        node = self.ast.find_state_variable_declaration_node(word)
        if node:
            range = Range(
                start=Position(line=node.lineno - 1, character=node.col_offset),
                end=Position(line=node.end_lineno - 1, character=node.end_col_offset),
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
        node = self.ast.find_type_declaration_node(word)
        if node:
            range = Range(
                start=Position(line=node.lineno - 1, character=node.col_offset),
                end=Position(line=node.end_lineno - 1, character=node.end_col_offset),
            )
            return range

    def find_references(self, doc: Document, pos: Position) -> List[Range]:
        og_line = doc.lines[pos.line]
        word = get_word_at_cursor(og_line, pos.character)
        if self.ast.ast_data is None:
            print("ast data is none", file=sys.stderr)
            return []
        references = []

        print(f"state variables: {self.ast.get_state_variables()}", file=sys.stderr)
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
            print("found struct or event", word, file=sys.stderr)
            refs = self.ast.find_nodes_referencing_struct(word)
            for ref in refs:
                range = Range(
                    start=Position(line=ref.lineno - 1, character=ref.col_offset),
                    end=Position(line=ref.end_lineno - 1, character=ref.end_col_offset),
                )
                references.append(range)
        elif not og_line[0].isspace() and word in self.ast.get_state_variables():
            print("found state variable", word, file=sys.stderr)
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
        return references

    def find_declaration(self, document: Document, pos: Position) -> Optional[Range]:
        if self.ast.ast_data is None:
            return None

        og_line = document.lines[pos.line]
        word = get_word_at_cursor(og_line, pos.character)
        full_word = get_expression_at_cursor(og_line, pos.character)
        range = None

        if full_word.startswith("self."):
            if "(" in full_word:
                range = self.find_function_declaration(word)
            else:
                range = self.find_state_variable_declaration(word)
        else:
            if word in self.ast.get_user_defined_types():
                range = self.find_type_declaration(word)
            elif word in self.ast.get_constants():
                range = self.find_state_variable_declaration(word)
            else:
                # check if full_word matches "enum.variant" regex
                pattern = r"([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)"
                match = re.match(pattern, full_word)
                if match:
                    enum_name = match.group(1)
                    variant_name = match.group(2)
                    if enum_name in self.ast.get_enums():
                        variants = self.ast.get_enum_variants(enum_name)
                        if variant_name in variants:
                            range = self.find_type_declaration(enum_name)
        if range:
            return range

    def find_implementation(self, document: Document, pos: Position) -> Optional[Range]:
        og_line = document.lines[pos.line]
        word = get_word_at_cursor(og_line, pos.character)
        expression = get_expression_at_cursor(og_line, pos.character)

        if not "(" in expression:
            return None

        if expression.startswith("self."):
            return self.find_function_declaration(word)
        elif og_line[0].isspace() and og_line.strip().startswith("def"):
            # only lookup external fns if we're in an interface def
            return self.find_function_declaration(word)
        else:
            return None
