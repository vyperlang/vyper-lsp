import sys

from pygls.lsp.types.language_features import (
    CompletionItem,
    CompletionList,
    CompletionParams,
)
from pygls.server import LanguageServer

from src.ast import AST
from src.types import BASE_TYPES

DECORATORS = ["payable", "nonpayable", "view", "pure", "external", "internal"]


class Completer:
    def __init__(self, ast=None):
        self.ast = ast or AST()

    def get_completions(
        self, ls: LanguageServer, params: CompletionParams
    ) -> CompletionList:
        items = []
        document = ls.workspace.get_document(params.text_document.uri)
        og_line = document.lines[params.position.line]
        current_line = document.lines[params.position.line].strip()
        custom_types = self.ast.get_user_defined_types()

        if params.context:
            if params.context.trigger_character == ".":
                # get element before the dot
                element = current_line.split(" ")[-1].split(".")[0]
                for attr in self.ast.get_attributes_for_symbol(element):
                    items.append(CompletionItem(label=attr))
                l = CompletionList(is_incomplete=False, items=[])
                l.add_items(items)
                return l
            elif params.context.trigger_character == "@":
                for dec in DECORATORS:
                    items.append(CompletionItem(label=dec))
                l = CompletionList(is_incomplete=False, items=[])
                l.add_items(items)
                return l
            elif params.context.trigger_character == ":":
                for typ in custom_types + list(BASE_TYPES):
                    items.append(CompletionItem(label=typ, insert_text=f" {typ}"))

                l = CompletionList(is_incomplete=False, items=[])
                l.add_items(items)
                return l
            else:
                if params.context.trigger_character == " ":
                    if current_line[-1] == ":":
                        print("triggered type", file=sys.stderr)
                        for typ in custom_types + list(BASE_TYPES):
                            items.append(CompletionItem(label=typ))

                        l = CompletionList(is_incomplete=False, items=[])
                        l.add_items(items)
                        return l

                print(
                    f"unknown trigger character {params.context.trigger_character}",
                    file=sys.stderr,
                )
        else:
            print("no context", file=sys.stderr)
            print(params, file=sys.stderr)
        return CompletionList(is_incomplete=False, items=[])
