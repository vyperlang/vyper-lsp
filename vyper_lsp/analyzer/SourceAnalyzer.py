import re
from typing import List, Optional
from lark import UnexpectedInput, UnexpectedToken
from packaging.specifiers import Specifier
from packaging.version import Version
from pygls.lsp.types import (
    CompletionList,
    CompletionParams,
    Diagnostic,
    Position,
    Range,
)
from pygls.server import LanguageServer
from pygls.workspace import Document
from vvm.exceptions import VyperError
from vyper_lsp.analyzer.BaseAnalyzer import Analyzer
import vvm

from pathlib import Path

from lark import Lark
from vyper.ast.grammar import PythonIndenter

GRAMMAR_FILE_PATH = Path(__file__).parent.parent.parent / "grammar" / "grammar.lark"
GRAMMAR = GRAMMAR_FILE_PATH.read_text()

parser = Lark(GRAMMAR, parser="lalr", start="module", postlex=PythonIndenter())


def format_parse_error(e):
    if isinstance(e, UnexpectedToken):
        expected = ", ".join(e.accepts or e.expected)
        return f"Unexpected token '{e.token}' at {e.line}:{e.column}. Expected one of: {expected}"
    else:
        return str(e)


LEGACY_VERSION_PRAGMA_REGEX = re.compile(r"^#\s*@version\s+(.*)$")
VERSION_PRAGMA_REGEX = re.compile(r"^#pragma\s+version\s+(.*)$")


def extract_version_pragma(line: str) -> Optional[str]:
    if match := LEGACY_VERSION_PRAGMA_REGEX.match(line):
        return match.group(1)
    elif match := VERSION_PRAGMA_REGEX.match(line):
        return match.group(1)
    else:
        return None


# regex that matches numbers and underscores
# ex: 1_000_000
NUMBER_REGEX = re.compile(r"^(_\d+)*$")


class SourceAnalyzer(Analyzer):
    def __init__(self) -> None:
        self.parser_enabled = True
        self.compiler_enabled = False

    def get_version_pragma(self, doc: Document) -> Optional[str]:
        doc_lines = doc.lines
        for line in doc_lines:
            if version := extract_version_pragma(line):
                return version

    def hover_info(self, doc: Document, pos: Position) -> Optional[str]:
        return None

    def get_parser_diagnostics(self, doc: Document) -> List[Diagnostic]:
        diagnostics = []
        last_error = None

        def on_grammar_error(e: UnexpectedInput) -> bool:
            nonlocal last_error
            if (
                last_error is not None
                and last_error.line == e.line
                and last_error.column == e.column
            ):
                return True
            if (
                last_error is not None
                and type(last_error) == type(e)
                and last_error.line == e.line
            ):
                return True
            diagnostics.append(
                Diagnostic(
                    range=Range(
                        start=Position(line=e.line - 1, character=e.column - 1),
                        end=Position(line=e.line - 1, character=e.column),
                    ),
                    message=format_parse_error(e),
                )
            )
            last_error = e
            return True

        try:
            parser.parse(doc.source, on_error=on_grammar_error)
        except Exception:
            # ignore errors that are already handled by on_error
            pass

        return diagnostics

    def get_compiler_diagnostics(self, doc: Document) -> List[Diagnostic]:
        diagnostics = []

        # now compile via vvm to get semantic errors
        try:
            vvm.compile_source(doc.source)
        except VyperError as e:
            if "vyper.exceptions.VersionException" in e.stderr_data:
                # ignore version errors, we handle them separately
                version_pragma = self.get_version_pragma(doc)
                # check if version pragma is just a version or a specifier
                if version_pragma is None:
                    diagnostics.append(
                        Diagnostic(
                            range=Range(
                                start=Position(line=0, character=0),
                                end=Position(line=0, character=0),
                            ),
                            message=str(e),
                        )
                    )
                elif re.match(r"^\d+\.\d+\.\d+$", version_pragma):
                    # version pragma is just a version, so we just install it
                    version: Version = Version(version_pragma)
                    vvm.install_vyper(version)
                    vvm.set_vyper_version(version)
                else:
                    specifier: Specifier = Specifier(version_pragma)
                    for version in vvm.get_installable_vyper_versions():
                        if specifier.contains(version):
                            vvm.install_vyper(version)
                            vvm.set_vyper_version(version)
            else:
                # find the line and number of the error
                # will appear in the text as `line x:y`
                regex = re.compile(r"line (\d+):(\d+)")
                match = regex.search(e.stderr_data)

                type_regex = re.compile(r"vyper\.exceptions\.([a-zA-Z]+): (.*)\n")
                type_match = type_regex.search(e.stderr_data)
                if match and type_match:
                    diagnostics.append(
                        Diagnostic(
                            range=Range(
                                start=Position(
                                    line=int(match.group(1)) - 1,
                                    character=int(match.group(2)) - 1,
                                ),
                                end=Position(
                                    line=int(match.group(1)) - 1,
                                    character=int(match.group(2)),
                                ),
                            ),
                            message=f"{type_match.group(1)}: {type_match.group(2)}",
                        )
                    )
        except Exception:
            pass

        return diagnostics

    def get_diagnostics(self, doc: Document) -> List[Diagnostic]:
        diagnostics = []
        if self.parser_enabled:
            diagnostics.extend(self.get_parser_diagnostics(doc))
        if self.compiler_enabled:
            diagnostics.extend(self.get_compiler_diagnostics(doc))
        return diagnostics

    def get_completions(
        self, ls: LanguageServer, params: CompletionParams
    ) -> CompletionList:
        completions: CompletionList = CompletionList(is_incomplete=False, items=[])
        return completions
