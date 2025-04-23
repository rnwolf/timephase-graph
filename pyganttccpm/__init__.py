# pyganttccpm/__init__.py
from .plotter import plot_project_gantt_with_start_end
from .loader import process_project_data  # <-- Add this
from .config import TaskType

__version__ = '0.1.0'
__author__ = 'R.N. Wolf'

# Optional: Define __all__ to control 'from pyganttccpm import *'
__all__ = ['plot_project_gantt_with_start_end', 'process_project_data', 'TaskType']
