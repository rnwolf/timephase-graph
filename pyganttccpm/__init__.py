# pyganttccpm/__init__.py
import logging
import tkinter
from os import environ
from pathlib import Path
from sys import base_prefix
import platform

# --- Logging Setup ---
# Get a logger for the library package
# Using __name__ ensures the logger name matches the package name ('pyganttccpm')
log = logging.getLogger(__name__)

# Add a NullHandler to the library's logger.
# This prevents log messages from being output unless the calling
# application configures logging for the library's logger or the root logger.
log.addHandler(logging.NullHandler())
# --- End Logging Setup ---

from .plotter import plot_project_gantt
from .loader import process_project_data  # <-- Add this
from .config import TaskType

# Required for matplotlib to work with tkinter on some systems
# https://github.com/astral-sh/uv/issues/7036
if not ('TCL_LIBRARY' in environ and 'TK_LIBRARY' in environ):
    try:
        root = tkinter.Tk()
        root.destroy()
    except tkinter.TclError:
        tk_dir = 'tcl' if platform.system() == 'Windows' else 'lib'
        tk_path = Path(base_prefix) / tk_dir
        environ['TCL_LIBRARY'] = str(next(tk_path.glob('tcl8.*')))
        environ['TK_LIBRARY'] = str(next(tk_path.glob('tk8.*')))


__version__ = '0.1.0'
__author__ = 'R.N. Wolf'

# Optional: Define __all__ to control 'from pyganttccpm import *'
__all__ = [
    'plot_project_gantt_with_start_end',
    'process_project_data',
    'load_process_project_data',
    'TaskType',
    'log',
    '__version__',
    '__author__',
]
