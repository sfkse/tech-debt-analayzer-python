"""
Centralized application configuration and initialization.
This module handles environment loading and logging setup.
"""
from pathlib import Path
from dotenv import load_dotenv

from config.logging_config import setup_logging, get_logger as _get_logger


# Global flag to ensure initialization happens only once
_initialized = False

def initialize_app():
    """
    Initialize the application by loading environment variables and setting up logging.
    This should be called once at the start of the application.
    """
    global _initialized
    if _initialized:
        return
    
    # Load environment variables from .env file
    script_dir = Path(__file__).parent
    env_path = script_dir / '.env'
    load_dotenv(env_path)
    
    # Initialize logging system
    setup_logging()
    
    _initialized = True

def get_logger(name: str):
    """
    Get a logger instance for a specific module.
    """
    return _get_logger(name) 