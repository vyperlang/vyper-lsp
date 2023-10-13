import sys
import re
from typing import List, Optional
import warnings
from pygls.lsp.types import Diagnostic, Position, Range
from pygls.workspace import Document
from vyper.compiler import CompilerData
from vyper.exceptions import VyperException
from vyper_lsp.analyzer.BaseAnalyzer import Analyzer
from vyper_lsp.ast import AST
from vyper_lsp.utils import get_expression_at_cursor, get_word_at_cursor

pattern = r"(.+) is deprecated\. Please use `(.+)` instead\."
compiled_pattern = re.compile(pattern)

class AstAnalyzer(Analyzer):

    def __init__(self, ast = None) -> None:
        super().__init__()
        self.ast = ast or AST()

    def hover_info(self, document: Document, pos: Position) -> Optional[str]:
        og_line = document.lines[pos.line]
        word = get_word_at_cursor(og_line, pos.character)
        full_word = get_expression_at_cursor(og_line, pos.character)

        if full_word.startswith("self."):
            if "(" in full_word:
                node = self.ast.find_function_declaration_node_for_name(word)
                if node:
                    fn_name = node.name
                    arg_str = ", ".join([f"{arg.arg}: {arg.annotation.id}" for arg in node.args.args])
                    return f"(Internal Function) **{fn_name}**({arg_str})"
            else:
                node = self.ast.find_state_variable_declaration_node(word)
                if node:
                    variable_type = node.annotation.id
                    return f"(State Variable) **{word}** : **{variable_type}**"
        else:
            if word in self.ast.get_structs():
                node = self.ast.find_type_declaration_node(word)
                if node:
                    return f"(Struct) **{word}**"
            elif word in self.ast.get_enums():
                node = self.ast.find_type_declaration_node(word)
                if node:
                    return f"(Enum) **{word}**"
            elif word in self.ast.get_events():
                node = self.ast.find_type_declaration_node(word)
                if node:
                    return f"(Event) **{word}**"
            elif word in self.ast.get_constants():
                node = self.ast.find_state_variable_declaration_node(word)
                if node:
                    variable_type = node.annotation.id
                    return f"(Constant) **{word}** : **{variable_type}**"
            else:
                return None

    def get_diagnostics(self, doc: Document) -> List[Diagnostic]:
        print(f"get_diagnostics: {doc.uri}", file=sys.stderr)

        diagnostics = []
        replacements = {}

        warnings.simplefilter("always")
        with warnings.catch_warnings(record=True) as w:
            try:
                compiler_data = CompilerData(doc.source)
                compiler_data.vyper_module_folded
            except VyperException as e:
                print(f"VyperException: {e}", file=sys.stderr)
                if e.lineno is not None and e.col_offset is not None:
                    diagnostics.append(
                        Diagnostic(
                            range=Range(
                                start=Position(line=e.lineno - 1, character=e.col_offset - 1),
                                end=Position(line=e.lineno - 1, character=e.col_offset),
                            ),
                            message=str(e),
                            severity=1,
                        )
                    )
                else:
                    for a in e.annotations:
                        diagnostics.append(
                            Diagnostic(
                                range=Range(
                                    start=Position(
                                        line=a.lineno - 1, character=a.col_offset - 1
                                    ),
                                    end=Position(line=a.lineno - 1, character=a.col_offset),
                                ),
                                message=e.message,
                                severity=1,
                            )
                        )
            for warning in w:
                match = compiled_pattern.match(str(warning.message))
                if not match:
                    continue
                deprecated = match.group(1)
                replacement = match.group(2)
                replacements[deprecated] = replacement

        # iterate over doc.lines and find all deprecated values
        # and create a warning for each one at the correct position
        for i, line in enumerate(doc.lines):
            for deprecated, replacement in replacements.items():
                if deprecated in line:
                    diagnostics.append(
                        Diagnostic(
                            range=Range(
                                start=Position(line=i, character=line.index(deprecated)),
                                end=Position(line=i, character=line.index(deprecated) + len(deprecated)),
                            ),
                            message=f"{deprecated} is deprecated. Please use {replacement} instead.",
                            severity=2,
                        )
                    )

        return diagnostics
