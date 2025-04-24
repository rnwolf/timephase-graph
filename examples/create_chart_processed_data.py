# examples/create_chart_processed_data.py
import sys
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import logging


# Import the processing and plotting functions
from pyganttccpm import process_project_data, plot_project_gantt_with_start_end

# --- Basic Logging Configuration for the Application ---
# This configures the root logger. Library logs will flow up to it.
logging.basicConfig(
    level=logging.INFO,  # Set the minimum level you want to see (e.g., INFO, DEBUG)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
# --- End Logging Configuration ---


# --- 1. Define Raw Project Data in Python ---
project_info = {
    'name': 'Processed Data Project',
    'start_date': '2025-01-01',
    'publish_date': '2025-01-15',
    'calendar': 'standard',
}

# List of task dictionaries, similar to JSON structure
tasks_input = [
    {
        'id': 101,
        'name': 'Task Alpha',
        'start': 0,
        'finish': 5,
        'type': 'CRITICAL',
        'chain': 'Main',
        'resources': 'Team A',
        'tags': ['init'],
        'url': None,
    },
    {
        'id': 102,
        'name': 'Task Beta',
        'start': 5,
        'finish': 12,
        'type': 'FEEDING',
        'chain': 'Main',
        'resources': 'Team B',
        'predecessors': '101',
        'remaining': 4,  # Use offsets/IDs as strings if needed by processing
        'tags': ['core', 'api'],
        'url': 'http://example.com/beta',
    },
    {
        'id': 103,
        'name': 'Task Gamma',
        'start': 5,
        'finish': 8,
        'type': 'FREE',
        'chain': 'Side',
        'resources': 'Team C',
        'predecessors': '101',
        'tags': [],
    },
]

# --- 2. Process the Raw Data using the package function ---
logging.info('Processing raw data...')
(
    project_start_date,
    tasks,
    dependencies,
    stream_map,
    calendar_type,
    project_name,
    project_publish_date,
) = process_project_data(project_info, tasks_input)

if tasks is None or project_start_date is None:
    logging.info('Failed to process project data. Exiting.')
    sys.exit(1)
logging.info('Data processed successfully.')

# --- 3. Create the Gantt Plot using the main package function ---
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

# --- 4. Save Plot to SVG File ---
OUTPUT_SVG_FILE = '../gantt_chart_processed.svg'  # Adjust path
if fig:
    try:
        logging.info(f'Saving plot to {OUTPUT_SVG_FILE}...')
        fig.savefig(OUTPUT_SVG_FILE, format='svg', bbox_inches='tight')
        logging.info('Plot saved successfully.')
    except Exception as e:
        logging.info(f'Error saving plot to SVG: {e}')
else:
    logging.info('Plot figure was not generated, skipping save.')

# --- 5. Optionally Show the Plot ---
if fig:
    logging.info('Displaying plot...')
    plt.show()
else:
    logging.info('Plot figure was not generated, skipping display.')

logging.info('Example script finished.')
