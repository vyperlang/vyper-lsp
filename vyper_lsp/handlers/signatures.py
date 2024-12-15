import logging

from pygls.workspace import Document
from vyper.ast import FunctionDef
from typing import Optional

from lsprotocol.types import (
    ParameterInformation,
    SignatureHelp,
    SignatureHelpParams,
    SignatureInformation,
)
from vyper_lsp import utils
from vyper_lsp.ast import AST
from vyper_lsp.utils import get_expression_at_cursor

logger = logging.getLogger("vyper-lsp")


class SignatureHandler:
    def __init__(self, ast: AST):
        self.ast = ast

    def _handle_internal_fn_signature(
        self, current_line: str, fn_name: str
    ) -> Optional[SignatureHelp]:
        node = self.ast.find_function_declaration_node_for_name(fn_name)
        if not node:
            return None

        fn_name = node.name
        parameters = []

        fn_label = node.node_source_code.split(":\n")[0].removeprefix("def ")

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

    def _handle_imported_fn_signature(
        self, current_line: str, module: str, fn_name: str
    ) -> Optional[SignatureHelp]:
        if module in self.ast.imports:
            if fn := self.ast.imports[module].functions[fn_name]:
                logger.info(f"getting signature for {fn_name}")
                logger.info(fn.decl_node)
                node: FunctionDef = fn.decl_node
                label = node.node_source_code.split("def ")[1].split(":\n")[0]
                parameters = []
                for arg in node.args.args:
                    parameters.append(
                        ParameterInformation(label=arg.arg, documentation=None)
                    )
                active_parameter = current_line.split("(")[-1].count(",")
                return SignatureHelp(
                    signatures=[
                        SignatureInformation(
                            label=label,
                            parameters=parameters,
                            documentation=None,
                            active_parameter=active_parameter or 0,
                        )
                    ],
                    active_signature=0,
                )

    def signature_help(
        self, doc: Document, params: SignatureHelpParams
    ) -> Optional[SignatureHelp]:
        # TODO: Implement checking external functions, module functions, and interfaces
        current_line = doc.lines[params.position.line]
        expression = get_expression_at_cursor(
            current_line, params.position.character - 1
        )
        parsed = utils.parse_fncall_expression(expression)
        if parsed is None:
            return None
        module, fn_name = parsed

        # this returns for all external functions
        if module == "self":
            return self._handle_internal_fn_signature(current_line, fn_name)
        else:
            return self._handle_imported_fn_signature(current_line, module, fn_name)
