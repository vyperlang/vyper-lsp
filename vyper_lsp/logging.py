import logging

logger = logging.getLogger("vyper-lsp")
logger.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class LanguageServerLogHandler(logging.Handler):
    def __init__(self, ls):
        super().__init__()
        self.ls = ls

    def emit(self, record):
        log_entry = self.format(record)
        if not self.ls:
            return
        self.ls.show_message_log(log_entry)
