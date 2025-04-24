# examples/create_chart.py
import sys
import logging

from pyganttccpm import plot_project_gantt_with_start_end  # Import the main function
from pyganttccpm.loader import load_process_project_data  # Import the loader

# --- Basic Logging Configuration for the Application ---
# This configures the root logger. Library logs will flow up to it.
logging.basicConfig(
    level=logging.INFO,  # Set the minimum level you want to see (e.g., INFO, DEBUG)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
# --- End Logging Configuration ---

# --- Configuration ---
JSON_FILE_PATH = '../project-gantt-data.json'  # Adjust path relative to example script
OUTPUT_SVG_FILE = '../gantt_chart_example.svg'  # Adjust path

# 1. Load Data using the loader function from the package
logging.info(f'Loading data from {JSON_FILE_PATH}...')
(
    project_start_date,
    tasks,
    dependencies,
    stream_map,
    calendar_type,
    project_name,
    project_publish_date,
) = load_process_project_data(JSON_FILE_PATH)

if tasks is None or project_start_date is None:
    logging.info('Failed to load or process project data. Exiting.')
    sys.exit(1)
logging.info('Data loaded successfully.')

# 2. Create the Gantt Plot using the main package function
logging.info('Generating plot...')
fig = plot_project_gantt_with_start_end(
    project_start_date,
    tasks,
    dependencies,
    stream_map,
    calendar_type,
    project_name,
    project_publish_date,
)

# 3. Save Plot to SVG File
if fig:
    try:
        logging.info(f'Saving plot to {OUTPUT_SVG_FILE}...')
        fig.savefig(OUTPUT_SVG_FILE, format='svg', bbox_inches='tight')
        logging.info('Plot saved successfully.')
    except Exception as e:
        logging.exception(f'Error saving plot to SVG: {e}')
else:
    logging.info('Plot figure was not generated, skipping save.')

# 4. Optionally Show the Plot (if running interactively)
import matplotlib.pyplot as plt

if fig:
    logging.info('Displaying plot...')
    plt.show()
else:
    logging.info('Plot figure was not generated, skipping display.')

logging.info('Example script finished.')
