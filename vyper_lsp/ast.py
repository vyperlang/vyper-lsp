import sys
from pygls.lsp.types.language_features import List
from vyper.ast import nodes
from vyper.compiler import CompilerData

ast = None


class AST:
    _instance = None
    ast_data = None

    custom_type_node_types = (nodes.StructDef, nodes.EnumDef, nodes.EventDef)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AST, cls).__new__(cls)
            cls._instance.ast_data = None
        return cls._instance

    def update_ast(self, document):
        try:
            compiler_data = CompilerData(document.source)
            self.ast_data = compiler_data.vyper_module_unfolded
        except Exception as e:
            print(f"Error generating unfolded AST, {e}")
            pass

    def build_ast(self, src: str):
        try:
            compiler_data = CompilerData(src)
            self.ast_data = compiler_data.vyper_module_unfolded
        except Exception as e:
            print(f"Error generating unfolded AST, {e}")
            pass

    def get_enums(self) -> List[str]:
        if self.ast_data is None:
            return []

        return [node.name for node in self.ast_data.get_descendants(nodes.EnumDef)]

    def get_structs(self) -> List[str]:
        if self.ast_data is None:
            return []

        return [node.name for node in self.ast_data.get_descendants(nodes.StructDef)]

    def get_events(self) -> List[str]:
        if self.ast_data is None:
            return []

        return [node.name for node in self.ast_data.get_descendants(nodes.EventDef)]

    def get_user_defined_types(self):
        if self.ast_data is None:
            return []

        return [
            node.name
            for node in self.ast_data.get_descendants(self.custom_type_node_types)
        ]

    def get_constants(self):
        if self.ast_data is None:
            return []

        return [
            node.target.id
            for node in self.ast_data.get_descendants(nodes.VariableDecl)
            if node.is_constant
        ]

    def get_enum_variants(self, enum: str):
        if self.ast_data is None:
            return []

        enum_node = self.find_type_declaration_node(enum)
        if enum_node is None:
            return []

        return [node.value.id for node in enum_node.get_children()]

    def get_state_variables(self):
        if self.ast_data is None:
            return []

        print(f"{self.ast_data.get_descendants(nodes.VariableDecl)}", file=sys.stderr)

        return [
            node.target.id for node in self.ast_data.get_descendants(nodes.VariableDecl)
        ]

    def get_internal_functions(self):
        if self.ast_data is None:
            return []

        function_nodes = self.ast_data.get_descendants(nodes.FunctionDef)
        inernal_nodes = []

        for node in function_nodes:
            for decorator in node.decorator_list:
                if decorator.id == "internal":
                    inernal_nodes.append(node)

        return inernal_nodes

    def find_nodes_referencing_internal_function(self, function: str):
        if self.ast_data is None:
            return []

        return self.ast_data.get_descendants(
            nodes.Call, {"func.attr": function, "func.value.id": "self"}
        )

    def find_nodes_referencing_state_variable(self, variable: str):
        if self.ast_data is None:
            return []

        return self.ast_data.get_descendants(
            nodes.Attribute, {"value.id": "self", "attr": variable}
        )

    def find_nodes_referencing_constant(self, constant: str):
        if self.ast_data is None:
            return []

        name_nodes = self.ast_data.get_descendants(nodes.Name, {"id": constant})
        return [
            node
            for node in name_nodes
            if not isinstance(node.get_ancestor(), nodes.VariableDecl)
        ]

    def get_attributes_for_symbol(self, symbol: str):
        if self.ast_data is None:
            return []

        node = self.find_type_declaration_node(symbol)
        if node is None:
            return []

        if isinstance(node, nodes.StructDef):
            return []
        elif isinstance(node, nodes.EnumDef):
            return self.get_enum_variants(symbol)
        else:
            return []

    def find_function_declaration_node_for_name(self, function: str):
        if self.ast_data is None:
            return None

        for node in self.ast_data.get_descendants(nodes.FunctionDef):
            name_match = node.name == function
            not_interface_declaration = not isinstance(
                node.get_ancestor(), nodes.InterfaceDef
            )
            if name_match and not_interface_declaration:
                return node

        return None

    def find_state_variable_declaration_node(self, variable: str):
        if self.ast_data is None:
            return None

        for node in self.ast_data.get_descendants(nodes.VariableDecl):
            if node.target.id == variable:
                return node

        return None

    def find_type_declaration_node(self, symbol: str):
        if self.ast_data is None:
            return None

        for node in self.ast_data.get_descendants(self.custom_type_node_types):
            if node.name == symbol:
                return node
            if isinstance(node, nodes.EnumDef):
                for variant in node.get_children(nodes.Expr):
                    if variant.value.id == symbol:
                        return variant

        return None

    def find_nodes_referencing_enum(self, enum: str):
        if self.ast_data is None:
            return []

        return_nodes = []

        for node in self.ast_data.get_descendants(
            nodes.AnnAssign, {"annotation.id": enum}
        ):
            return_nodes.append(node)
        for node in self.ast_data.get_descendants(nodes.Attribute, {"value.id": enum}):
            return_nodes.append(node)
        for node in self.ast_data.get_descendants(
            nodes.VariableDecl, {"annotation.id": enum}
        ):
            return_nodes.append(node)

        return return_nodes

    def find_nodes_referencing_enum_variant(self, enum: str, variant: str):
        if self.ast_data is None:
            return None

        return self.ast_data.get_descendants(
            nodes.Attribute, {"attr": variant, "value.id": enum}
        )

    def find_nodes_referencing_struct(self, struct: str):
        if self.ast_data is None:
            return []

        return_nodes = []

        for node in self.ast_data.get_descendants(
            nodes.AnnAssign, {"annotation.id": struct}
        ):
            return_nodes.append(node)
        for node in self.ast_data.get_descendants(nodes.Call, {"func.id": struct}):
            return_nodes.append(node)
        for node in self.ast_data.get_descendants(
            nodes.VariableDecl, {"annotation.id": struct}
        ):
            return_nodes.append(node)
        for node in self.ast_data.get_descendants(
            nodes.FunctionDef, {"returns.id": struct}
        ):
            return_nodes.append(node)

        return return_nodes
