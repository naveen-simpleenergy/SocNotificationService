import logging
import os
from logging.handlers import RotatingFileHandler
import json
from colorlog import ColoredFormatter

class StructuredMessage:
    def __init__(self, message, **kwargs):
        self.message = message
        self.kwargs = kwargs

    def to_dict(self):
        return {**self.kwargs, "message": self.message}

def setup_logging():
    log_dir = os.getenv('LOG_DIR', 'logs')
    log_file_name = os.getenv('LOG_FILE_NAME', 'app.log')
    log_file_path = os.path.join(log_dir, log_file_name)

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

    # Advanced colorized formatter for console output
    console_formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)-8s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'bold_green',
            'WARNING': 'bold_yellow',
            'ERROR': 'bold_red',
            'CRITICAL': 'bold_red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    )

    # Standard formatter for file output
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)-8s - %(module)s.%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler with rotating logs
    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=10**6, backupCount=5
    )
    file_handler.setFormatter(file_formatter)

    # Console handler with colorized output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    logging.basicConfig(
        level=getattr(logging, log_level),
        handlers=[file_handler, console_handler]
    )

    logging.info("Logging is set up.")

# Function to log structured messages
def log(message, level=logging.INFO, **kwargs):
    logging.log(level, StructuredMessage(message, **kwargs).to_dict())
