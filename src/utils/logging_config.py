"""
Logging Configuration
Centralized logging setup for all microservices
"""

import logging
import sys
from datetime import datetime
from typing import Optional

def setup_logging(name: str, level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Setup logging configuration for a module
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    
    Returns:
        Configured logger instance
    """
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with default configuration
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return setup_logging(name)

class LoggerMixin:
    """Mixin class to add logging capabilities to any class"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def log_info(self, message: str, **kwargs):
        """Log info message with additional context"""
        context = " ".join([f"{k}={v}" for k, v in kwargs.items()])
        self.logger.info(f"{message} {context}".strip())
    
    def log_error(self, message: str, error: str = None, **kwargs):
        """Log error message with additional context"""
        context = " ".join([f"{k}={v}" for k, v in kwargs.items()])
        error_msg = f"Error: {error}" if error else ""
        self.logger.error(f"{message} {error_msg} {context}".strip())
    
    def log_warning(self, message: str, **kwargs):
        """Log warning message with additional context"""
        context = " ".join([f"{k}={v}" for k, v in kwargs.items()])
        self.logger.warning(f"{message} {context}".strip())
    
    def log_debug(self, message: str, **kwargs):
        """Log debug message with additional context"""
        context = " ".join([f"{k}={v}" for k, v in kwargs.items()])
        self.logger.debug(f"{message} {context}".strip()) 