import copy
import logging
from typing import Optional, List
from lsprotocol.types import Diagnostic, Position
from pygls.workspace import Document
from vyper.ast import VyperNode, nodes
from vyper.compiler import CompilerData
from vyper.compiler.input_bundle import FilesystemInputBundle
from vyper.compiler.phases import DEFAULT_CONTRACT_PATH, ModuleT
from vyper.semantics.types import StructT
from vyper.semantics.types.user import FlagT
from vyper.exceptions import VyperException
from vyper.cli.vyper_compile import get_search_paths
import warnings
import re

from vyper_lsp.utils import (
    create_diagnostic_warning,
    diagnostic_from_exception,
    working_directory_for_document,
    document_to_fileinput,
)

logger = logging.getLogger("vyper-lsp")


pattern_text = r"(.+) will be deprecated in a future release, use (.+) instead\."
deprecation_pattern = re.compile(pattern_text)


class AST:
    ast_data = None
    ast_data_annotated = None

    custom_type_node_types = (nodes.StructDef, nodes.FlagDef)

    # Module Data
    functions = {}
    variables = {}
    flags = {}
    structs = {}

    # Import Data
    imports = {}

    @classmethod
    def from_node(cls, node: VyperNode):
        ast = cls()
        ast.ast_data = node
        ast.ast_data_annotated = node
        return ast

    def _load_import_data(self):
        ast = self.ast_data_annotated
        if ast is None:
            return
        import_nodes = ast.get_descendants((nodes.ImportFrom, nodes.Import))
        node: nodes.ImportFrom | nodes.Import
        imports = {}
        for node in import_nodes:
            import_info = node._metadata["import_info"]
            module_t: ModuleT = import_info.typ.module_t
            alias = node._metadata["import_info"].alias
            imports[alias] = module_t

        self.imports = imports

    def _load_module_data(self):
        ast = self.ast_data_annotated
        if ast is None:
            return
        self.functions = ast._metadata["type"].functions
        self.variables = ast._metadata["type"].variables

        flagt_list = [
            FlagT.from_FlagDef(node) for node in ast._metadata["type"].flag_defs
        ]
        self.flags = {flagt.name: flagt for flagt in flagt_list}

        structt_list = [
            StructT.from_StructDef(node) for node in ast._metadata["type"].struct_defs
        ]
        self.structs = {structt.name: structt for structt in structt_list}

    def update_ast(self, doc: Document) -> List[Diagnostic]:
        diagnostics = self.build_ast(doc)
        return diagnostics

    def build_ast(self, doc: Document | str) -> List[Diagnostic]:
        if isinstance(doc, str):
            doc = Document(uri=str(DEFAULT_CONTRACT_PATH), source=doc)
        uri_parent_path = working_directory_for_document(doc)
        search_paths = get_search_paths([str(uri_parent_path)])
        fileinput = document_to_fileinput(doc)
        compiler_data = CompilerData(
            fileinput, input_bundle=FilesystemInputBundle(search_paths)
        )
        diagnostics = []
        replacements = {}
        warnings.simplefilter("always")
        with warnings.catch_warnings(record=True) as w:
            try:
                # unforunately we need this deep copy so the ast doesnt change
                # out from under us when folding stuff happens
                self.ast_data = copy.deepcopy(compiler_data.vyper_module)
                self.ast_data_annotated = compiler_data.annotated_vyper_module

                self._load_module_data()
                self._load_import_data()

            except VyperException as e:
                # make message string include class name
                message = f"{e.__class__.__name__}: {e}"
                if e.lineno is not None and e.col_offset is not None:
                    diagnostics.append(diagnostic_from_exception(e))
                if e.annotations:
                    for a in e.annotations:
                        diagnostics.append(
                            diagnostic_from_exception(a, message=message)
                        )

            for warning in w:
                m = deprecation_pattern.match(str(warning.message))
                if not m:
                    continue
                deprecated = m.group(1)
                replacement = m.group(2)
                replacements[deprecated] = replacement

        # Iterate over doc.lines and find all deprecated values
        for i, line in enumerate(doc.lines):
            for deprecated, replacement in replacements.items():
                for match in re.finditer(re.escape(deprecated), line):
                    character_start = match.start()
                    character_end = match.end()
                    diagnostic_message = (
                        f"{deprecated} is deprecated. Please use {replacement} instead."
                    )
                    diagnostics.append(
                        create_diagnostic_warning(
                            line_num=i,
                            character_start=character_start,
                            character_end=character_end,
                            message=diagnostic_message,
                        )
                    )

        return diagnostics

    @property
    def best_ast(self):
        if self.ast_data_annotated:
            return self.ast_data_annotated
        elif self.ast_data:
            return self.ast_data

        return None

    def get_descendants(self, *args, **kwargs):
        if self.best_ast is None:
            return []
        return self.best_ast.get_descendants(*args, **kwargs)

    def get_top_level_nodes(self, *args, **kwargs):
        if self.best_ast is None:
            return []
        return self.best_ast.get_children(*args, **kwargs)

    def get_enums(self) -> List[str]:
        # return [node.name for node in self.get_descendants(nodes.FlagDef)]
        return list(self.flags.keys())

    def get_structs(self) -> List[str]:
        # return [node.name for node in self.get_descendants(nodes.StructDef)]
        return list(self.structs.keys())

    def get_events(self) -> List[str]:
        return [node.name for node in self.get_descendants(nodes.EventDef)]

    def get_user_defined_types(self):
        return [node.name for node in self.get_descendants(self.custom_type_node_types)]

    def get_constants(self):
        # NOTE: Constants should be fetched from self.ast_data, they are missing
        # from self.ast_data_unfolded and self.ast_data_folded
        # NOTE: This may no longer be the case with the new AST format
        if self.ast_data is None:
            return []

        return [
            node.target.id
            for node in self.ast_data.get_children(
                nodes.VariableDecl, {"is_constant": True}
            )
        ]

    def get_enum_variants(self, enum: str):
        enum_node = self.find_type_declaration_node_for_name(enum)
        if enum_node is None:
            return []

        return [node.value.id for node in enum_node.get_children(nodes.Expr)]

    def get_struct_fields(self, struct: str):
        struct_node = self.find_type_declaration_node_for_name(struct)
        if struct_node is None:
            return []

        return [node.target.id for node in struct_node.get_children(nodes.AnnAssign)]

    def get_state_variables(self):
        # NOTE: The state variables should be fetched from self.ast_data, they are
        # missing from self.ast_data_unfolded and self.ast_data_folded when constants
        if self.ast_data is None:
            return []

        return [
            node.target.id for node in self.ast_data.get_descendants(nodes.VariableDecl)
        ]

    def get_internal_function_nodes(self):
        function_nodes = self.get_descendants(nodes.FunctionDef)
        internal_nodes = []

        for node in function_nodes:
            for decorator in node.decorator_list:
                if isinstance(decorator, nodes.Name) and decorator.id == "internal":
                    internal_nodes.append(node)

        return internal_nodes

    def get_internal_functions(self):
        internal_fn_names = [k for k, v in self.functions.items() if v.is_internal]
        return internal_fn_names

    def find_nodes_referencing_internal_function(self, function: str):
        return self.get_descendants(
            nodes.Call, {"func.attr": function, "func.value.id": "self"}
        )

    def find_nodes_referencing_state_variable(self, variable: str):
        return self.get_descendants(
            nodes.Attribute, {"value.id": "self", "attr": variable}
        )

    def find_nodes_referencing_constant(self, constant: str):
        name_nodes = self.get_descendants(nodes.Name, {"id": constant})
        return [
            node
            for node in name_nodes
            if not isinstance(node.get_ancestor(), nodes.VariableDecl)
        ]

    def get_attributes_for_symbol(self, symbol: str):
        node = self.find_type_declaration_node_for_name(symbol)
        if node is None:
            return []

        if isinstance(node, nodes.StructDef):
            return self.get_struct_fields(symbol)
        elif isinstance(node, nodes.FlagDef):
            return self.get_enum_variants(symbol)

        return []

    def find_function_declaration_node_for_name(
        self, function: str
    ) -> Optional[nodes.FunctionDef]:
        for node in self.get_descendants(nodes.FunctionDef):
            name_match = node.name == function
            not_interface_declaration = not isinstance(
                node.get_ancestor(), nodes.InterfaceDef
            )
            if name_match and not_interface_declaration:
                return node

        return None

    def find_state_variable_declaration_node_for_name(self, variable: str):
        # NOTE: The state variables should be fetched from self.ast_data, they are
        # missing from self.ast_data_unfolded and self.ast_data_folded when constants
        if self.ast_data is None:
            return None

        for node in self.ast_data.get_descendants(nodes.VariableDecl):
            if node.target.id == variable:
                return node

        return None

    def find_type_declaration_node_for_name(self, symbol: str):
        searchable_types = self.custom_type_node_types + (nodes.EventDef,)
        for node in self.get_descendants(searchable_types):
            if node.name == symbol:
                return node
            if isinstance(node, nodes.FlagDef):
                for variant in node.get_children(nodes.Expr):
                    if variant.value.id == symbol:
                        return variant

        return None

    def find_nodes_referencing_enum(self, enum: str):
        return_nodes = []

        for node in self.get_descendants(nodes.AnnAssign, {"annotation.id": enum}):
            return_nodes.append(node)
        for node in self.get_descendants(nodes.Attribute, {"value.id": enum}):
            return_nodes.append(node)
        for node in self.get_descendants(nodes.VariableDecl, {"annotation.id": enum}):
            return_nodes.append(node)
        for node in self.get_descendants(nodes.FunctionDef, {"returns.id": enum}):
            return_nodes.append(node)

        return return_nodes

    def find_nodes_referencing_enum_variant(self, enum: str, variant: str):
        return self.get_descendants(
            nodes.Attribute, {"attr": variant, "value.id": enum}
        )

    def find_nodes_referencing_struct(self, struct: str):
        return_nodes = []

        for node in self.get_descendants(nodes.AnnAssign, {"annotation.id": struct}):
            return_nodes.append(node)
        for node in self.get_descendants(nodes.Call, {"func.id": struct}):
            return_nodes.append(node)
        for node in self.get_descendants(nodes.VariableDecl, {"annotation.id": struct}):
            return_nodes.append(node)
        for node in self.get_descendants(nodes.FunctionDef, {"returns.id": struct}):
            return_nodes.append(node)

        return return_nodes

    def find_top_level_node_at_pos(self, pos: Position) -> Optional[VyperNode]:
        nodes = self.get_top_level_nodes()
        for node in nodes:
            if node.lineno <= pos.line and pos.line <= node.end_lineno:
                return node

        # return node with highest lineno if no node found
        if nodes:
            # sort
            nodes.sort(key=lambda x: x.lineno, reverse=True)
            return nodes[0]

        return None

    def find_nodes_referencing_symbol(self, symbol: str):
        # this only runs on subtrees
        return_nodes = []

        for node in self.get_descendants(nodes.Name, {"id": symbol}):
            parent = node.get_ancestor()
            if isinstance(parent, nodes.Dict):
                # skip struct key names
                if symbol not in [key.id for key in parent.keys]:
                    return_nodes.append(node)
            elif isinstance(parent, nodes.AnnAssign):
                if node.id == parent.target.id:
                    # lhs of variable declaration
                    continue
                else:
                    return_nodes.append(node)
            else:
                return_nodes.append(node)

        return return_nodes

    def find_node_declaring_symbol(self, symbol: str):
        for node in self.get_descendants((nodes.AnnAssign, nodes.VariableDecl)):
            if node.target.id == symbol:
                return node

        return None
