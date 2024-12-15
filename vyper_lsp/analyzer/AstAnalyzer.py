import logging
import re
from typing import List, Optional
from packaging.version import Version
from lsprotocol.types import (
    CompletionItemLabelDetails,
    ParameterInformation,
    Position,
    SignatureHelp,
    SignatureInformation,
)
from pygls.workspace import Document
from vyper.ast import FunctionDef, nodes
from vyper_lsp import utils
from vyper_lsp.analyzer.BaseAnalyzer import Analyzer
from vyper_lsp.ast import AST
from vyper_lsp.utils import (
    format_fn,
    get_expression_at_cursor,
    get_word_at_cursor,
    get_installed_vyper_version,
)
from lsprotocol.types import (
    CompletionItem,
    CompletionList,
    CompletionParams,
    SignatureHelpParams,
)
from pygls.server import LanguageServer

pattern_text = r"(.+) is deprecated\. Please use `(.+)` instead\."
deprecation_pattern = re.compile(pattern_text)

min_vyper_version = Version("0.4.0")

# Available base types
UNSIGNED_INTEGER_TYPES = {f"uint{8*(i)}" for i in range(32, 0, -1)}
SIGNED_INTEGER_TYPES = {f"int{8*(i)}" for i in range(32, 0, -1)}
INTEGER_TYPES = UNSIGNED_INTEGER_TYPES | SIGNED_INTEGER_TYPES

BYTES_M_TYPES = {f"bytes{i}" for i in range(32, 0, -1)}
DECIMAL_TYPES = {"decimal"}

BASE_TYPES = list({"bool", "address"} | INTEGER_TYPES | BYTES_M_TYPES | DECIMAL_TYPES)

DECORATORS = ["payable", "nonpayable", "view", "pure", "external", "internal", "deploy"]

logger = logging.getLogger("vyper-lsp")


class AstAnalyzer(Analyzer):
    def __init__(self, ast: AST) -> None:
        super().__init__()
        self.ast = ast
        if get_installed_vyper_version() < min_vyper_version:
            self.diagnostics_enabled = False
        else:
            self.diagnostics_enabled = True

    def _dot_completions_for_module(
        self, element: str, top_level_node=None, line: str = ""
    ) -> List[CompletionItem]:
        completions = []
        for name, fn in self.ast.imports[element].functions.items():
            doc_string = ""
            if getattr(fn.ast_def, "doc_string", False):
                doc_string = fn.ast_def.doc_string.value

            out = format_fn(fn)

            # NOTE: this just gets ignored by most editors
            # so we put the signature in the documentation string also
            completion_item_label_details = CompletionItemLabelDetails(detail=out)

            doc_string = f"{out}\n{doc_string}"

            show_external: bool = isinstance(
                top_level_node, nodes.ExportsDecl
            ) or line.startswith("exports:")
            show_internal_and_deploy: bool = isinstance(
                top_level_node, nodes.FunctionDef
            )

            if show_internal_and_deploy and (fn.is_internal or fn.is_deploy):
                completions.append(
                    CompletionItem(
                        label=name,
                        documentation=doc_string,
                        label_details=completion_item_label_details,
                    )
                )
            elif show_external and fn.is_external:
                completions.append(
                    CompletionItem(
                        label=name,
                        documentation=doc_string,
                        label_details=completion_item_label_details,
                    )
                )

        return completions

    def _dot_completions_for_element(
        self, element: str, top_level_node=None, line: str = ""
    ) -> List[CompletionItem]:
        completions = []
        if element == "self":
            for fn in self.ast.get_internal_functions():
                completions.append(CompletionItem(label=fn))
            # TODO: This should exclude constants and immutables
            for var in self.ast.get_state_variables():
                completions.append(CompletionItem(label=var))
        elif self.ast.imports and element in self.ast.imports.keys():
            completions = self._dot_completions_for_module(
                element, top_level_node=top_level_node, line=line
            )
        elif element in self.ast.flags:
            members = self.ast.flags[element]._flag_members
            for member in members.keys():
                completions.append(CompletionItem(label=member))

        if isinstance(top_level_node, nodes.FunctionDef):
            var_declarations = top_level_node.get_descendants(
                nodes.AnnAssign, filters={"target.id": element}
            )
            assert len(var_declarations) <= 1
            for vardecl in var_declarations:
                type_name = vardecl.annotation.id
                structt = self.ast.structs.get(type_name, None)
                if structt:
                    for member in structt.members:
                        completions.append(CompletionItem(label=member))

        return completions

    def _get_completions_in_doc(
        self, document: Document, params: CompletionParams
    ) -> CompletionList:
        items = []
        current_line = document.lines[params.position.line].strip()
        custom_types = self.ast.get_user_defined_types()

        no_completions = CompletionList(is_incomplete=False, items=[])

        if not params.context:
            return no_completions

        if params.context.trigger_character == ".":
            # get element before the dot
            # TODO: this could lead to bugs if we're not at EOL
            element = current_line.split(" ")[-1].split(".")[0]

            pos = params.position
            surrounding_node = self.ast.find_top_level_node_at_pos(pos)

            # internal + imported fns, state vars, and flags
            dot_completions = self._dot_completions_for_element(
                element, top_level_node=surrounding_node, line=current_line
            )
            if len(dot_completions) > 0:
                return CompletionList(is_incomplete=False, items=dot_completions)
            else:
                for attr in self.ast.get_attributes_for_symbol(element):
                    items.append(CompletionItem(label=attr))
            completions = CompletionList(is_incomplete=False, items=items)
            return completions

        if params.context.trigger_character == "@":
            for dec in DECORATORS:
                items.append(CompletionItem(label=dec))
            completions = CompletionList(is_incomplete=False, items=items)
            return completions

        if params.context.trigger_character == ":":
            # return empty_completions if colon isn't for a type annotation
            object_declaration_keywords = [
                "flag",
                "struct",
                "event",
                "enum",
                "interface",
                "def",
            ]
            if any(
                current_line.startswith(keyword)
                for keyword in object_declaration_keywords
            ):
                return no_completions

            for typ in custom_types + BASE_TYPES:
                items.append(CompletionItem(label=typ, insert_text=f" {typ}"))

            completions = CompletionList(is_incomplete=False, items=items)
            return completions

        if params.context.trigger_character == " ":
            if current_line[-1] == ":":
                for typ in custom_types + BASE_TYPES:
                    items.append(CompletionItem(label=typ))

                completions = CompletionList(is_incomplete=False, items=items)
                return completions

        return CompletionList(is_incomplete=False, items=[])

    def get_completions(
        self, ls: LanguageServer, params: CompletionParams
    ) -> CompletionList:
        document = ls.workspace.get_text_document(params.text_document.uri)
        return self._get_completions_in_doc(document, params)

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
