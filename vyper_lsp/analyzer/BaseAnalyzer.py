from abc import ABC, abstractmethod
from typing import List, Optional
from lsprotocol.types import CompletionList, CompletionParams, Diagnostic, Position
from pygls.server import LanguageServer
from pygls.workspace import Document


class Analyzer(ABC):
    @abstractmethod
    def hover_info(self, doc: Document, pos: Position) -> Optional[str]:
        pass

    @abstractmethod
    def get_completions(
        self, ls: LanguageServer, params: CompletionParams
    ) -> CompletionList:
        pass
