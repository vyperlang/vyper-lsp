import logging
import re
from typing import List, Optional
from packaging.version import Version
from lsprotocol.types import (
    CompletionItemLabelDetails,
    Diagnostic,
    DiagnosticSeverity,
    ParameterInformation,
    Position,
    Range,
    SignatureHelp,
    SignatureInformation,
)
from pygls.workspace import Document
from vyper.ast import nodes
from vyper_lsp.analyzer.BaseAnalyzer import Analyzer
from vyper_lsp.ast import AST
from vyper_lsp.utils import (
    format_fn,
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

    def signature_help(
        self, doc: Document, params: SignatureHelpParams
    ) -> Optional[SignatureHelp]:
        logger.info("signature help triggered")
        current_line = doc.lines[params.position.line]
        expression = get_expression_at_cursor(
            current_line, params.position.character - 1
        )
        logger.info(f"expression: {expression}")
        # regex for matching 'module.function'
        fncall_pattern = "(.*)\\.(.*)"

        if matches := re.match(fncall_pattern, expression):
            module, fn = matches.groups()
            logger.info(f"looking up function {fn} in module {module}")
            if module in self.ast.imports:
                logger.info(f"found module")
                if fn := self.ast.imports[module].functions[fn]:
                    logger.info(f"args: {fn.arguments}")


        # this returns for all external functions
        # TODO: Implement checking interfaces
        if not expression.startswith("self."):
            return None

        # TODO: Implement checking external functions, module functions, and interfaces
        fn_name = get_internal_fn_name_at_cursor(
            current_line, params.position.character - 1
        )

        if not fn_name:
            return None

        node = self.ast.find_function_declaration_node_for_name(fn_name)
        if not node:
            return None

        fn_name = node.name
        parameters = []
        line = doc.lines[node.lineno - 1]

        decl_str = f"def {fn_name}("
        search_start_line_no = 0

        while not line.startswith(decl_str):
            line = doc.lines[search_start_line_no]
            search_start_line_no += 1


        fn_label = line.removeprefix("def ").removesuffix(":\n")

        for arg in node.args.args:
            start_index = fn_label.find(arg.arg)
            end_index = start_index + len(arg.arg)
            parameters.append(
                ParameterInformation(label=(start_index, end_index), documentation=None)
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

    def _dot_completions_for_element(self, element: str, top_level_node = None, line: str="") -> List[CompletionItem]:
        completions = []
        logger.info(f"getting dot completions for element: {element}")
        #logger.info(f"import keys: {self.ast.imports.keys()}")
        self.ast.imports.keys()
        if element == "self":
            for fn in self.ast.get_internal_functions():
                completions.append(CompletionItem(label=fn))
            # TODO: This should exclude constants and immutables
            for var in self.ast.get_state_variables():
                completions.append(CompletionItem(label=var))
        elif self.ast.imports and element in self.ast.imports.keys():
            for name, fn in self.ast.imports[element].functions.items():
                doc_string = ""
                if getattr(fn.ast_def, "doc_string", False):
                    doc_string = fn.ast_def.doc_string.value

                #out = self._format_fn_signature(fn.decl_node)
                out = format_fn(fn)

                # NOTE: this just gets ignored by most editors
                # so we put the signature in the documentation string also
                completion_item_label_details = CompletionItemLabelDetails(detail=out)

                doc_string = f"{out}\n{doc_string}"

                show_external: bool = isinstance(top_level_node, nodes.ExportsDecl) or line.startswith("exports:")
                show_internal_and_deploy: bool = isinstance(top_level_node, nodes.FunctionDef)

                if show_internal_and_deploy and (fn.is_internal or fn.is_deploy):
                        completions.append(CompletionItem(label=name, documentation=doc_string, label_details=completion_item_label_details))
                elif show_external and fn.is_external:
                        completions.append(CompletionItem(label=name, documentation=doc_string, label_details=completion_item_label_details))
        elif element in self.ast.flags:
            members = self.ast.flags[element]._flag_members
            for member in members.keys():
                completions.append(CompletionItem(label=member))

        if isinstance(top_level_node, nodes.FunctionDef):
            var_declarations = top_level_node.get_descendants(nodes.AnnAssign, filters={"target.id": element})
            assert len(var_declarations) <= 1
            for vardecl in var_declarations:
                type_name = vardecl.annotation.id
                structt = self.ast.structs.get(type_name, None)
                if structt:
                    for member in structt.members:
                        completions.append(CompletionItem(label=member))

        return completions

    def get_completions_in_doc(
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
            dot_completions = self._dot_completions_for_element(element, top_level_node=surrounding_node, line=current_line)
            if len(dot_completions) > 0:
                return CompletionList(is_incomplete=False, items=dot_completions)
            else:
                logger.info(f"no dot completions for {element}")
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
            # return empty_completions if the line starts with "flag", "struct", or "event"
            object_declaration_keywords = ["flag", "struct", "event", "enum", "interface"]
            if any(current_line.startswith(keyword) for keyword in object_declaration_keywords):
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
        return self.get_completions_in_doc(document, params)

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
        pattern = r"def\s+(\w+)\((?:[^()]|\n)*\)(?:\s*->\s*[\w\[\], \n]+)?:"
        match = re.search(pattern, node.node_source_code, re.MULTILINE)
        if match:
            function_def = match.group()
            return f"(Internal Function) {function_def}"

    def is_internal_fn(self, expression: str):
        if not expression.startswith("self."):
            return False
        fn_name = expression.split("self.")[-1]
        return fn_name in self.ast.functions and self.ast.functions[fn_name].is_internal

    def is_state_var(self, expression: str):
        if not expression.startswith("self."):
            return False
        var_name = expression.split("self.")[-1]
        return var_name in self.ast.variables


    def hover_info(self, document: Document, pos: Position) -> Optional[str]:
        if len(document.lines) < pos.line:
            return None

        og_line = document.lines[pos.line]
        word = get_word_at_cursor(og_line, pos.character)
        full_word = get_expression_at_cursor(og_line, pos.character)

        if self.is_internal_fn(full_word):
            logger.info("looking for internal fn")
            node = self.ast.find_function_declaration_node_for_name(word)
            return node and self._format_fn_signature(node)

        if self.is_state_var(full_word):
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
