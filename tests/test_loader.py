import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path  # For easier path handling

# Adjust the import based on your package structure
from pyganttccpm.loader import load_process_project_data
from pyganttccpm.config import TaskType


# Use pytest fixtures for setup (e.g., creating temporary JSON files)
@pytest.fixture
def sample_json_data_standard(tmp_path):
    """Creates a temporary standard JSON file for testing."""
    data = {
        'project_info': {
            'name': 'Test Project',
            'start_date': '2025-01-01T08:00:00',  # Include time to test normalization
            'publish_date': '2025-01-10',
            'calendar': 'standard',
        },
        'tasks': [
            {
                'id': 1,
                'name': 'Task A',
                'start': 0,
                'finish': 5,
                'type': 'CRITICAL',
                'chain': 'C1',
                'resources': 'R1',
                'tags': ['tag1'],
                'url': 'http://example.com/a',
            },
            {
                'id': 2,
                'name': 'Task B',
                'start': 5,
                'finish': 10,
                'type': 'FEEDING',
                'chain': 'C1',
                'resources': 'R2',
                'predecessors': '1',
                'remaining': 2,  # Add remaining
            },
            {
                'id': 3,
                'name': 'Task C',
                'start': 0,
                'finish': 3,
                'type': 'INVALID_TYPE',
                'chain': 'C2',  # Test invalid type
            },
            {
                'id': 4,
                'name': 'Task D',
                'start': 10,
                'finish': 8,  # Test invalid finish
            },
        ],
    }
    file_path = tmp_path / 'test_project.json'
    with open(file_path, 'w') as f:
        json.dump(data, f)
    return file_path


# Test function names should start with 'test_'
def test_load_standard_calendar(sample_json_data_standard):
    """Tests loading data with a standard calendar and basic fields."""
    file_path = sample_json_data_standard
    (start_date, tasks, dependencies, stream_map, calendar, name, publish_date) = (
        load_process_project_data(file_path)
    )

    # Assertions
    assert start_date is not None
    # Check normalization to midnight
    assert start_date == datetime(2025, 1, 1, 0, 0, 0)
    assert calendar == 'standard'
    assert name == 'Test Project'
    assert publish_date == datetime(
        2025, 1, 10, 0, 0, 0
    )  # Assuming parser defaults time to 00:00

    assert len(tasks) == 4  # Check number of tasks loaded
    assert len(dependencies) == 1  # Check number of dependencies found
    assert dependencies[0] == ('Task A', 'Task B')  # Check dependency pair

    # Check details of a specific task
    task_a = tasks.get('Task A')
    assert task_a is not None
    assert task_a['id'] == 1
    assert task_a['start'] == datetime(2025, 1, 1)
    assert task_a['end'] == datetime(
        2025, 1, 6
    )  # finish 5 means end before day 5 starts
    assert task_a['total_duration'] == timedelta(days=5)
    assert task_a['type'] == TaskType.CRITICAL
    assert task_a['chain'] == 'C1'
    assert task_a['resources'] == 'R1'
    assert task_a['tags'] == ['tag1']
    assert task_a['url'] == 'http://example.com/a'
    assert not task_a['has_remaining_data']  # No 'remaining' field

    # Check task with 'remaining'
    task_b = tasks.get('Task B')
    assert task_b is not None
    assert task_b['start'] == datetime(2025, 1, 6)
    assert task_b['end'] == datetime(2025, 1, 11)
    assert task_b['total_duration'] == timedelta(days=5)
    assert task_b['remaining_duration'] == timedelta(days=2)
    assert task_b['completed_duration'] == timedelta(days=3)
    assert task_b['has_remaining_data'] is True

    # Check handling of invalid type
    task_c = tasks.get('Task C')
    assert task_c is not None
    assert task_c['type'] == TaskType.UNASSIGNED  # Should default

    # Check handling of invalid finish offset
    task_d = tasks.get('Task D')
    assert task_d is not None
    assert task_d['start'] == datetime(2025, 1, 11)
    assert task_d['end'] == datetime(2025, 1, 11)  # Should default to zero duration
    assert task_d['total_duration'] == timedelta(days=0)


def test_load_missing_file():
    """Tests behavior when the JSON file doesn't exist."""
    result = load_process_project_data('non_existent_file.json')
    # Expecting multiple None values returned
    assert all(item is None for item in result)


def test_load_invalid_json(tmp_path):
    """Tests behavior with invalid JSON content."""
    file_path = tmp_path / 'invalid.json'
    with open(file_path, 'w') as f:
        f.write('{invalid json content')
    result = load_process_project_data(file_path)
    assert all(item is None for item in result)


def test_load_missing_start_date(tmp_path):
    """Tests behavior when project_info lacks start_date."""
    data = {'project_info': {'name': 'No Start Date'}}
    file_path = tmp_path / 'no_start.json'
    with open(file_path, 'w') as f:
        json.dump(data, f)
    result = load_process_project_data(file_path)
    assert all(item is None for item in result)


# Add more tests for:
# - 'continuous' calendar type
# - Missing optional fields (publish_date, calendar, name, resources, tags, url, remaining, predecessors)
# - Invalid date formats
# - Invalid predecessor IDs
# - Empty tasks list
