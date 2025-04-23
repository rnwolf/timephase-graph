# examples/create_chart.py
import sys
from pyganttccpm import plot_project_gantt_with_start_end  # Import the main function
from pyganttccpm.loader import load_process_project_data  # Import the loader

# --- Configuration ---
JSON_FILE_PATH = '../project-gantt-data.json'  # Adjust path relative to example script
OUTPUT_SVG_FILE = '../gantt_chart_example.svg'  # Adjust path

# 1. Load Data using the loader function from the package
print(f'Loading data from {JSON_FILE_PATH}...')
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
    print('Failed to load or process project data. Exiting.')
    sys.exit(1)
print('Data loaded successfully.')

# 2. Create the Gantt Plot using the main package function
print('Generating plot...')
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
        print(f'Saving plot to {OUTPUT_SVG_FILE}...')
        fig.savefig(OUTPUT_SVG_FILE, format='svg', bbox_inches='tight')
        print('Plot saved successfully.')
    except Exception as e:
        print(f'Error saving plot to SVG: {e}')
else:
    print('Plot figure was not generated, skipping save.')

# 4. Optionally Show the Plot (if running interactively)
import matplotlib.pyplot as plt

if fig:
    print('Displaying plot...')
    plt.show()
else:
    print('Plot figure was not generated, skipping display.')

print('Example script finished.')
