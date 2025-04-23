import pytest
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Adjust imports
from pyganttccpm import plot_project_gantt_with_start_end
from pyganttccpm.loader import load_process_project_data

from pyganttccpm.config import TASK_COLORS, TaskType, START_NODE, END_NODE


# Use the same fixture as test_loader or create a minimal one
@pytest.fixture
def minimal_plot_data():
    """Provides minimal valid data for plotting."""
    start_date = datetime(2025, 1, 1)
    tasks = {
        'Task1': {
            'id': 1,
            'start': datetime(2025, 1, 1),
            'end': datetime(2025, 1, 5),
            'total_duration': timedelta(days=4),
            'completed_duration': timedelta(days=2),
            'remaining_duration': timedelta(days=2),
            'has_remaining_data': True,
            'type': TaskType.CRITICAL,
            'chain': 'C1',
            'resources': 'R',
            'tags': [],
            'url': None,
        }
    }
    dependencies = []
    stream_map = {'Task1': 'C1'}
    calendar = 'standard'
    name = 'Minimal Test'
    publish_date = None
    return start_date, tasks, dependencies, stream_map, calendar, name, publish_date


def test_plotter_runs_without_error(minimal_plot_data):
    """Tests if the plotting function executes without raising exceptions."""
    plt.close('all')  # Close any previous plots
    try:
        fig = plot_project_gantt_with_start_end(*minimal_plot_data)
        assert fig is not None
        assert isinstance(fig, plt.Figure)
        # We don't visually inspect the plot here, just check it ran
    except Exception as e:
        pytest.fail(f'plot_project_gantt_with_start_end raised an exception: {e}')
    finally:
        plt.close('all')  # Clean up the figure


# More advanced tests could:
# - Mock matplotlib calls (complex)
# - Check properties of the returned figure/axes (e.g., title, labels, number of bars)
# - Use image comparison libraries (like pytest-mpl) if visual regression testing is needed
