import logging
import re
from typing import List, Optional
import warnings
from packaging.version import Version
from lsprotocol.types import (
    Diagnostic,
    ParameterInformation,
    Position,
    Range,
    SignatureHelp,
    SignatureInformation,
)
from pygls.workspace import Document
from vyper.compiler import CompilerData
from vyper.exceptions import VyperException
from vyper.ast import nodes
from vyper_lsp.analyzer.BaseAnalyzer import Analyzer
from vyper_lsp.ast import AST
from vyper_lsp.utils import (
    get_expression_at_cursor,
    get_word_at_cursor,
    get_installed_vyper_version,
    get_internal_fn_name_at_cursor,
)
from lsprotocol.types import (
    CompletionItem,
    CompletionList,
    CompletionParams,
    SignatureHelpParams,
)
from pygls.server import LanguageServer

pattern = r"(.+) is deprecated\. Please use `(.+)` instead\."
compiled_pattern = re.compile(pattern)

min_vyper_version = Version("0.3.7")

# Available base types
UNSIGNED_INTEGER_TYPES = {f"uint{8*(i)}" for i in range(32, 0, -1)}
SIGNED_INTEGER_TYPES = {f"int{8*(i)}" for i in range(32, 0, -1)}
INTEGER_TYPES = UNSIGNED_INTEGER_TYPES | SIGNED_INTEGER_TYPES

BYTES_M_TYPES = {f"bytes{i}" for i in range(32, 0, -1)}
DECIMAL_TYPES = {"decimal"}

BASE_TYPES = {"bool", "address"} | INTEGER_TYPES | BYTES_M_TYPES | DECIMAL_TYPES

DECORATORS = ["payable", "nonpayable", "view", "pure", "external", "internal"]

logger = logging.getLogger("vyper-lsp")


class AstAnalyzer(Analyzer):
    def __init__(self, ast: AST) -> None:
        super().__init__()
        self.ast = ast
        if get_installed_vyper_version() < min_vyper_version:
            self.diagnostics_enabled = False
        else:
            self.diagnostics_enabled = True

    def _range_from_exception(self, node: VyperException) -> Range:
        return Range(
            start=Position(line=node.lineno - 1, character=node.col_offset),
            end=Position(line=node.end_lineno - 1, character=node.end_col_offset),
        )

    def _diagnostic_from_exception(self, node: VyperException) -> Diagnostic:
        return Diagnostic(
            range=self._range_from_exception(node),
            message=str(node),
            severity=1,
        )

    def signature_help(
        self, doc: Document, params: SignatureHelpParams
    ) -> SignatureHelp:
        current_line = doc.lines[params.position.line]
        expression = get_expression_at_cursor(
            current_line, params.position.character - 1
        )
        fn_name = get_internal_fn_name_at_cursor(
            current_line, params.position.character - 1
        )

        if expression.startswith("self."):
            node = self.ast.find_function_declaration_node_for_name(fn_name)
            if node:
                fn_name = node.name
                arg_str = ", ".join(
                    [f"{arg.arg}: {arg.annotation.id}" for arg in node.args.args]
                )
                fn_label = f"{fn_name}({arg_str})"
                parameters = []
                if node.returns:
                    line = doc.lines[node.lineno - 1]
                    fn_label = line.removeprefix("def ").removesuffix(":\n")
                for arg in node.args.args:
                    start_index = fn_label.find(arg.arg)
                    end_index = start_index + len(arg.arg)
                    parameters.append(
                        ParameterInformation(
                            label=(start_index, end_index), documentation=None
                        )
                    )
                active_parameter = current_line.split("(")[-1].count(",")
                return SignatureHelp(
                    signatures=[
                        SignatureInformation(
                            label=fn_label,
                            parameters=parameters,
                            documentation=None,
                            active_parameter=active_parameter or 0,
                        )
                    ],
                    active_signature=0,
                )

    def get_completions_in_doc(
        self, document: Document, params: CompletionParams
    ) -> CompletionList:
        items = []
        current_line = document.lines[params.position.line].strip()
        custom_types = self.ast.get_user_defined_types()

        if params.context:
            if params.context.trigger_character == ".":
                # get element before the dot
                element = current_line.split(" ")[-1].split(".")[0]

                # internal functions and state variables
                if element == "self":
                    for fn in self.ast.get_internal_functions():
                        items.append(CompletionItem(label=fn))
                    # TODO: This should exclude constants and immutables
                    for var in self.ast.get_state_variables():
                        items.append(CompletionItem(label=var))
                else:
                    # TODO: This is currently only correct for enums
                    # For structs, we'll need to get the type of the variable
                    for attr in self.ast.get_attributes_for_symbol(element):
                        items.append(CompletionItem(label=attr))
                completions = CompletionList(is_incomplete=False, items=items)
                return completions
            elif params.context.trigger_character == "@":
                for dec in DECORATORS:
                    items.append(CompletionItem(label=dec))
                completions = CompletionList(is_incomplete=False, items=items)
                return completions
            elif params.context.trigger_character == ":":
                for typ in custom_types + list(BASE_TYPES):
                    items.append(CompletionItem(label=typ, insert_text=f" {typ}"))

                completions = CompletionList(is_incomplete=False, items=items)
                return completions
            else:
                if params.context.trigger_character == " ":
                    if current_line[-1] == ":":
                        for typ in custom_types + list(BASE_TYPES):
                            items.append(CompletionItem(label=typ))

                        completions = CompletionList(is_incomplete=False, items=items)
                        return completions
                return CompletionList(is_incomplete=False, items=[])

        else:
            return CompletionList(is_incomplete=False, items=[])

    def get_completions(
        self, ls: LanguageServer, params: CompletionParams
    ) -> CompletionList:
        document = ls.workspace.get_text_document(params.text_document.uri)
        return self.get_completions_in_doc(document, params)

    def _is_internal_fn(self, expression: str) -> bool:
        return expression.startswith("self.") and "(" in expression

    def _is_state_var(self, expression: str) -> bool:
        return expression.startswith("self.") and "(" not in expression

    def _format_arg(self, arg: nodes.arg) -> str:
        if arg.annotation is None:
            return arg.arg

        # Handle case when annotation is a subscript (e.g., List[int])
        if isinstance(arg.annotation, nodes.Subscript):
            annotation_base = arg.annotation.value.id  # e.g., 'List' in 'List[int]'

            # Check if the subscript's slice is a simple name
            if isinstance(arg.annotation.slice.value, nodes.Name):
                annotation_subscript = (
                    arg.annotation.slice.value.id
                )  # e.g., 'int' in 'List[int]'
            else:
                annotation_subscript = (
                    arg.annotation.slice.value.value
                )  # Handle other subscript types

            return f"{arg.arg}: {annotation_base}[{annotation_subscript}]"

        # Default case for simple annotations
        return f"{arg.arg}: {arg.annotation.id}"

    def _format_fn_signature(self, node: nodes.FunctionDef) -> str:
        fn_name = node.name
        arg_str = ", ".join([self._format_arg(arg) for arg in node.args.args])
        if node.returns:
            if isinstance(node.returns, nodes.Subscript):
                return_type_str = (
                    f"{node.returns.value.id}[{node.returns.slice.value.value}]"
                )
            else:
                return_type_str = node.returns.id
            return (
                f"(Internal Function) **{fn_name}**({arg_str}) -> **{return_type_str}**"
            )
        return f"(Internal Function) **{fn_name}**({arg_str})"

    def hover_info(self, document: Document, pos: Position) -> Optional[str]:
        if len(document.lines) < pos.line:
            return None
        og_line = document.lines[pos.line]
        word = get_word_at_cursor(og_line, pos.character)
        full_word = get_expression_at_cursor(og_line, pos.character)

        if self._is_internal_fn(full_word):
            node = self.ast.find_function_declaration_node_for_name(word)
            if node:
                return self._format_fn_signature(node)
        elif self._is_state_var(full_word):
            node = self.ast.find_state_variable_declaration_node_for_name(word)
            if node:
                variable_type = node.annotation.id
                return f"(State Variable) **{word}** : **{variable_type}**"
        elif word in self.ast.get_structs():
            node = self.ast.find_type_declaration_node_for_name(word)
            if node:
                return f"(Struct) **{word}**"
        elif word in self.ast.get_enums():
            node = self.ast.find_type_declaration_node_for_name(word)
            if node:
                return f"(Enum) **{word}**"
        elif word in self.ast.get_events():
            node = self.ast.find_type_declaration_node_for_name(word)
            if node:
                return f"(Event) **{word}**"
        elif word in self.ast.get_constants():
            node = self.ast.find_state_variable_declaration_node_for_name(word)
            if node:
                variable_type = node.annotation.id
                return f"(Constant) **{word}** : **{variable_type}**"
        else:
            return None

    def get_diagnostics(self, doc: Document) -> List[Diagnostic]:
        diagnostics = []

        if not self.diagnostics_enabled:
            return diagnostics

        replacements = {}
        warnings.simplefilter("always")
        with warnings.catch_warnings(record=True) as w:
            try:
                compiler_data = CompilerData(doc.source)
                compiler_data.vyper_module_folded
            except VyperException as e:
                if e.lineno is not None and e.col_offset is not None:
                    diagnostics.append(self._diagnostic_from_exception(e))
                else:
                    for a in e.annotations:
                        diagnostics.append(self._diagnostic_from_exception(a))
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
                                start=Position(
                                    line=i, character=line.index(deprecated)
                                ),
                                end=Position(
                                    line=i,
                                    character=line.index(deprecated) + len(deprecated),
                                ),
                            ),
                            message=f"{deprecated} is deprecated. Please use {replacement} instead.",
                            severity=2,
                        )
                    )

        return diagnostics
