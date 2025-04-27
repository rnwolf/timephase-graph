import pytest
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import re
import os
import pathlib as Path

# Adjust imports
from pyganttccpm import plot_project_gantt_with_start_end
from pyganttccpm.loader import load_process_project_data

from pyganttccpm.config import TASK_COLORS, TaskType, START_NODE, END_NODE


def sanitize_svg_for_comparison(svg_content: str) -> str:
    svg_content = re.sub(r'<dc:date>.*?</dc:date>', '', svg_content)
    svg_content = re.sub(r'\sclip-path="url\(#.*?\)"', '', svg_content)
    svg_content = re.sub(r'\sid="m[a-f0-9]{8,}"', '', svg_content)
    svg_content = re.sub(r'\sxlink:href="#m[a-f0-9]{8,}"', '', svg_content)
    svg_content = re.sub(r'<clipPath id="p[a-f0-9]{8,}">', '<clipPath>', svg_content)
    svg_content = re.sub(r'\s+', ' ', svg_content).strip()
    return svg_content


def assert_svg_equivalent(svg_file: str, reference_svg: str, debug_dir: Path = None):
    with open(svg_file) as f1, open(reference_svg) as f2:
        svg1 = sanitize_svg_for_comparison(f1.read())
        svg2 = sanitize_svg_for_comparison(f2.read())

    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        out1 = debug_dir / 'sanitized_input.svg'
        out2 = debug_dir / 'sanitized_reference.svg'
        out1.write_text(svg1)
        out2.write_text(svg2)

    assert svg1 == svg2, 'SVGs are not visually identical.' + (
        f'\nSanitized files saved to:\n  {out1}\n  {out2}' if debug_dir else ''
    )


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


def test_plotter_reference_svg(minimal_plot_data, tmp_path):
    """Tests if the plotting function create SVGs that are visually equivalent to reference file."""
    plt.close('all')  # Close any previous plots
    fig = plot_project_gantt_with_start_end(*minimal_plot_data)
    svg_file = tmp_path / 'test_plotter_reference_svg.svg'
    fig.savefig(svg_file, format='svg')

    # Compare against reference - get path to reference SVG
    test_dir = os.path.dirname(os.path.abspath(__file__))
    reference_svg = os.path.join(
        test_dir, 'reference', 'test_plotter_reference_svg.svg'
    )

    # Check if we're in write mode - Needed for first run
    write_mode = os.environ.get('TDDA_WRITE_ALL', '0') == '1'

    if write_mode:
        # Create the reference directory if it doesn't exist
        os.makedirs(os.path.dirname(reference_svg), exist_ok=True)
        # Create the reference SVG file
        import shutil

        shutil.copy2(svg_file, reference_svg)
        pytest.fail(
            f'Created reference SVG file: {reference_svg}. \nSet TDDA_WRITE_ALL=0 to run tests without writing files.'
        )
        return

    try:
        assert fig is not None
        assert isinstance(fig, plt.Figure)
        # Compare against the reference file
        assert_svg_equivalent(svg_file, reference_svg)
    except Exception as e:
        pytest.fail(f'test_plotter_reference_svg raised an exception: {e}')
    finally:
        plt.close('all')  # Clean up the figure
