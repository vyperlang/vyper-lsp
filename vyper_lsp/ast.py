import copy
import logging
from typing import Optional, List
from lsprotocol.types import Position
from vyper.ast import VyperNode, nodes
from vyper.compiler import CompilerData

logger = logging.getLogger("vyper-lsp")


class AST:
    ast_data = None
    ast_data_folded = None
    ast_data_unfolded = None

    custom_type_node_types = (
        nodes.StructDef,
        nodes.EnumDef,
        nodes.InterfaceDef,
        nodes.EventDef,
    )

    @classmethod
    def from_node(cls, node: VyperNode):
        ast = cls()
        ast.ast_data = node
        ast.ast_data_unfolded = node
        ast.ast_data_folded = node
        return ast

    def update_ast(self, document):
        self.build_ast(document.source)

    def build_ast(self, src: str):
        compiler_data = CompilerData(src)
        try:
            # unforunately we need this deep copy so the ast doesnt change
            # out from under us when folding stuff happens
            self.ast_data = copy.deepcopy(compiler_data.vyper_module)
        except Exception as e:
            logger.error(f"Error generating AST, {e}")

        try:
            self.ast_data_unfolded = compiler_data.vyper_module_unfolded
        except Exception as e:
            logger.error(f"Error generating unfolded AST, {e}")

        try:
            self.ast_data_folded = compiler_data.vyper_module_folded
        except Exception as e:
            logger.error(f"Error generating folded AST, {e}")

    @property
    def best_ast(self):
        if self.ast_data_unfolded:
            return self.ast_data_unfolded
        elif self.ast_data:
            return self.ast_data
        elif self.ast_data_folded:
            return self.ast_data_folded

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
        return [node.name for node in self.get_top_level_nodes(nodes.EnumDef)]

    def get_structs(self) -> List[str]:
        return [node.name for node in self.get_top_level_nodes(nodes.StructDef)]

    def get_events(self) -> List[str]:
        return [node.name for node in self.get_top_level_nodes(nodes.EventDef)]

    def get_interfaces(self):
        return [node.name for node in self.get_top_level_nodes(nodes.InterfaceDef)]

    def get_user_defined_types(self):
        return [
            node.name for node in self.get_top_level_nodes(self.custom_type_node_types)
        ]

    def get_constants(self):
        # NOTE: Constants should be fetched from self.ast_data, they are missing
        # from self.ast_data_unfolded and self.ast_data_folded
        if self.ast_data is None:
            return []

        return [
            node.target.id
            for node in self.get_top_level_nodes(nodes.VariableDecl)
            if node.is_constant
        ]

    def get_immutables(self):
        return [
            node.target.id
            for node in self.get_top_level_nodes(nodes.VariableDecl)
            if node.is_immutable
        ]

    def get_state_variables(self):
        # NOTE: The state variables should be fetched from self.ast_data, they are
        # missing from self.ast_data_unfolded and self.ast_data_folded when constants
        if self.ast_data is None:
            return []

        return [
            node.target.id
            for node in self.get_top_level_nodes(nodes.VariableDecl)
            if not node.is_constant and not node.is_immutable
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

    def get_internal_function_nodes(self):
        function_nodes = self.get_descendants(nodes.FunctionDef)
        internal_nodes = []

        for node in function_nodes:
            for decorator in node.decorator_list:
                if isinstance(decorator, nodes.Name) and decorator.id == "internal":
                    internal_nodes.append(node)

        return internal_nodes

    def get_internal_functions(self):
        return [node.name for node in self.get_internal_function_nodes()]

    def find_nodes_referencing_internal_function(self, function: str):
        return self.get_descendants(
            nodes.Call, {"func.attr": function, "func.value.id": "self"}
        )

    def find_nodes_referencing_state_variable(self, variable: str):
        return self.get_descendants(
            nodes.Attribute, {"value.id": "self", "attr": variable}
        )

    def find_nodes_referencing_constant_or_immutable(self, name: str):
        name_nodes = self.get_descendants(nodes.Name, {"id": name})
        return [
            node
            for node in name_nodes
            if not isinstance(node.get_ancestor(), nodes.VariableDecl)
        ]

    def find_nodes_referencing_constant(self, constant: str):
        return self.find_nodes_referencing_constant_or_immutable(constant)

    def find_nodes_referencing_immutable(self, immutable: str):
        return self.find_nodes_referencing_constant_or_immutable(immutable)

    def get_attributes_for_symbol(self, symbol: str):
        node = self.find_type_declaration_node_for_name(symbol)
        if node is None:
            return []

        if isinstance(node, nodes.StructDef):
            return self.get_struct_fields(symbol)
        elif isinstance(node, nodes.EnumDef):
            return self.get_enum_variants(symbol)

        return []

    def find_function_declaration_node_for_name(self, function: str):
        for node in self.get_top_level_nodes(nodes.FunctionDef):
            if node.name == function:
                return node

        return None

    def find_state_variable_declaration_node_for_name(self, variable: str):
        # NOTE: The state variables should be fetched from self.ast_data, they are
        # missing from self.ast_data_unfolded and self.ast_data_folded when constants
        if self.ast_data is None:
            return None

        for node in self.get_top_level_nodes(nodes.VariableDecl):
            if node.target.id == variable:
                return node

        return None

    def find_type_declaration_node_for_name(self, symbol: str):
        searchable_types = self.custom_type_node_types
        for node in self.get_top_level_nodes(searchable_types):
            if node.name == symbol:
                return node
            if isinstance(node, nodes.EnumDef):
                for variant in node.get_children(nodes.Expr):
                    if variant.value.id == symbol:
                        return variant

        return None

    def find_nodes_referencing_type(self, type_name: str):
        return_nodes = []

        type_expressions = set()

        for node in self.get_descendants():
            if hasattr(node, "annotation"):
                type_expressions.add(node.annotation)
            elif hasattr(node, "returns") and node.returns:
                type_expressions.add(node.returns)

        # TODO cover more builtin
        for node in self.get_descendants(nodes.Call, {"func.id": "empty"}):
            type_expressions.add(node.args[0])

        for node in type_expressions:
            for subnode in node.get_descendants(include_self=True):
                if isinstance(subnode, nodes.Name) and subnode.id == type_name:
                    return_nodes.append(subnode)

        return return_nodes

    def find_nodes_referencing_callable_type(self, type_name: str):
        return_nodes = self.find_nodes_referencing_type(type_name)

        for node in self.get_descendants(nodes.Call, {"func.id": type_name}):
            # ERC20(foo)
            # my_struct({x:0})
            return_nodes.append(node.func)

        return return_nodes

    def find_nodes_referencing_enum(self, type_name: str):
        return_nodes = self.find_nodes_referencing_type(type_name)

        for node in self.get_descendants(nodes.Attribute, {"value.id": type_name}):
            # A.o
            return_nodes.append(node.value)

        return return_nodes

    def find_nodes_referencing_enum_variant(self, enum: str, variant: str):
        return self.get_descendants(
            nodes.Attribute, {"attr": variant, "value.id": enum}
        )

    def find_nodes_referencing_struct(self, type_name: str):
        return self.find_nodes_referencing_callable_type(type_name)

    def find_nodes_referencing_interfaces(self, type_name: str):
        return self.find_nodes_referencing_callable_type(type_name)

    def find_top_level_node_at_pos(self, pos: Position) -> Optional[VyperNode]:
        for node in self.get_top_level_nodes():
            if node.lineno <= pos.line and pos.line <= node.end_lineno:
                return node

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
