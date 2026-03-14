import sys
import logging

logger = logging.getLogger("seedling")

class CLIFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            self._style._fmt = "%(message)s"
        elif record.levelno == logging.DEBUG:
            self._style._fmt = "[DEBUG] %(message)s"
        elif record.levelno == logging.WARNING:
            self._style._fmt = "⚠️  %(message)s"
        elif record.levelno == logging.ERROR:
            self._style._fmt = "❌ %(message)s"
        return super().format(record)

def configure_logging(verbose=False, quiet=False):
    level = logging.INFO
    if verbose: 
        level = logging.DEBUG
    elif quiet: 
        level = logging.ERROR
    
    if logger.hasHandlers():
        logger.handlers.clear()
        
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CLIFormatter())
    
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False