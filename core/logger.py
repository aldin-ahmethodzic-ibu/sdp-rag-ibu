import os
import logging
from logging.handlers import RotatingFileHandler
from core.settings import ROOT_DIR

# Ensure the logs directory exists
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)


def get_logger(name: str, log_file: str = "app.log", level: int = logging.INFO) -> logging.Logger:
    """
    Creates and returns a logger instance with the given name, log file, and log level.

    Args:
        name (str): Name of the logger, usually `__name__`.
        log_file (str): Name of the log file (default: app.log).
        level (int): Logging level (e.g., logging.INFO, logging.DEBUG). Default is `logging.INFO`.

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Construct the full path for the log file
    log_file_path = os.path.join(LOGS_DIR, log_file)

    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Check if logger already has handlers to avoid duplicate logs
    if not logger.hasHandlers():
        # Console handler for stdout
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)

        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file_path, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)

        # Add handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger