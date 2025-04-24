# pyganttccpm/__init__.py
import logging

# --- Logging Setup ---
# Get a logger for the library package
# Using __name__ ensures the logger name matches the package name ('pyganttccpm')
log = logging.getLogger(__name__)

# Add a NullHandler to the library's logger.
# This prevents log messages from being output unless the calling
# application configures logging for the library's logger or the root logger.
log.addHandler(logging.NullHandler())
# --- End Logging Setup ---

from .plotter import plot_project_gantt_with_start_end
from .loader import process_project_data  # <-- Add this
from .config import TaskType

__version__ = '0.1.0'
__author__ = 'R.N. Wolf'

# Optional: Define __all__ to control 'from pyganttccpm import *'
__all__ = [
    'plot_project_gantt_with_start_end',
    'process_project_data',
    'TaskType',
    'log',
    '__version__',
    '__author__',
]
