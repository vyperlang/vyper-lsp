from vyper.ast import nodes
from vyper.compiler import CompilerData

ast = None


class AST:
    _instance = None
    ast_data = None

    custom_type_node_types = (
        nodes.StructDef,
        nodes.EnumDef,
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AST, cls).__new__(cls)
            cls._instance.ast_data = None
        return cls._instance

    def update_ast(self, document):
        try:
            compiler_data = CompilerData(document.source)
            self.ast_data = compiler_data.vyper_module_unfolded
        except Exception:
            pass

    def get_user_defined_type_names(self):
        if self.ast_data is None:
            return []

        return [
            node.name
            for node in self.ast_data.get_descendants(self.custom_type_node_types)
        ]

    def get_enum_variants(self, enum: str):
        if self.ast_data is None:
            return []

        enum_node = self.find_declaration_node(enum)
        if enum_node is None:
            return []

        return [node.value.id for node in enum_node.get_children()]

    def get_attributes_for_symbol(self, symbol: str):
        if self.ast_data is None:
            return []

        node = self.find_declaration_node(symbol)
        if node is None:
            return []

        if isinstance(node, nodes.StructDef):
            return []
        elif isinstance(node, nodes.EnumDef):
            return self.get_enum_variants(symbol)
        else:
            return []

    def find_declaration_node(self, symbol: str):
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
