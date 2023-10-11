import sys
from pygls.lsp.types.language_features import Location, Position, Range
from typing import List, Optional

from pygls.workspace import Document
from src.ast import AST

# this class should abstract away all the AST stuff
# and just provide a simple interface for navigation
#
# the navigator should mainly return Ranges
class Navigator:
    def __init__(self, ast=None):
        self.ast = ast or AST()

    def find_declaration(self, word: str) -> Optional[Range]:
        node = self.ast.find_declaration_node(word)
        if node:
            range = Range(
                start=Position(line=node.lineno - 1, character=node.col_offset),
                end=Position(line=node.end_lineno - 1, character=node.end_col_offset),
            )
            return range

    def find_references(self, word: str, doc: Document, pos: Position) -> List[Range]:
        og_line = doc.lines[pos.line]
        if self.ast.ast_data is None:
            return []
        references = []

        if word in self.ast.get_enums():
            # find all references to this type
            refs = self.ast.find_nodes_referencing_enum(word)
            for ref in refs:
                range = Range(
                    start=Position(line=ref.lineno - 1, character=ref.col_offset),
                    end=Position(line=ref.end_lineno - 1, character=ref.end_col_offset),
                )
                references.append(range)
        elif word in self.ast.get_structs():
            refs = self.ast.find_nodes_referencing_struct(word)
            for ref in refs:
                range = Range(
                    start=Position(line=ref.lineno - 1, character=ref.col_offset),
                    end=Position(line=ref.end_lineno - 1, character=ref.end_col_offset),
                )
                references.append(range)
        elif not og_line[0].isspace() and word in self.ast.get_state_variables():
            print("found state variable", word, file=sys.stderr)
            refs = self.ast.find_nodes_referencing_state_variable(word)
            for ref in refs:
                range = Range(
                    start=Position(line=ref.lineno - 1, character=ref.col_offset),
                    end=Position(line=ref.end_lineno - 1, character=ref.end_col_offset),
                )
                references.append(range)
        return references
