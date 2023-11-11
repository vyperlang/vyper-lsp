import copy
from typing import Optional
from pygls.lsp.types import Position
from pygls.lsp.types.language_features import List
from vyper.ast import VyperNode, nodes
from vyper.compiler import CompilerData


class AST:
    ast_data = None
    ast_data_folded = None
    ast_data_unfolded = None

    custom_type_node_types = (nodes.StructDef, nodes.EnumDef)

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
            print(f"Error generating AST, {e}")
            pass
        try:
            self.ast_data_unfolded = compiler_data.vyper_module_unfolded
        except Exception as e:
            print(f"Error generating unfolded AST, {e}")
            pass
        try:
            self.ast_data_folded = compiler_data.vyper_module_folded
        except Exception as e:
            print(f"Error generating folded AST, {e}")
            pass

    @property
    def best_ast(self):
        if self.ast_data_unfolded:
            return self.ast_data_unfolded
        elif self.ast_data:
            return self.ast_data
        elif self.ast_data_folded:
            return self.ast_data_folded
        else:
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
        return [node.name for node in self.get_descendants(nodes.EnumDef)]

    def get_structs(self) -> List[str]:
        return [node.name for node in self.get_descendants(nodes.StructDef)]

    def get_events(self) -> List[str]:
        return [node.name for node in self.get_descendants(nodes.EventDef)]

    def get_user_defined_types(self):
        return [node.name for node in self.get_descendants(self.custom_type_node_types)]

    def get_constants(self):
        # NOTE: Constants should be fetched from self.ast_data, they are missing
        # from self.ast_data_unfolded and self.ast_data_folded
        if self.ast_data is None:
            return []

        return [
            node.target.id
            for node in self.ast_data.get_children(nodes.VariableDecl)
            if node.is_constant
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
        return [node.name for node in self.get_internal_function_nodes()]

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
        elif isinstance(node, nodes.EnumDef):
            return self.get_enum_variants(symbol)
        else:
            return []

    def find_function_declaration_node_for_name(self, function: str):
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
            if isinstance(node, nodes.EnumDef):
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
        for node in self.get_top_level_nodes():
            if node.lineno <= pos.line and pos.line <= node.end_lineno:
                return node

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
