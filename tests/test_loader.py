import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path  # For easier path handling

# Adjust the import based on your package structure
from pyganttccpm.loader import load_process_project_data, process_project_data
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
    (
        start_date,
        tasks,
        dependencies,
        stream_map,
        calendar,
        name,
        publish_date,
        is_synthetic_start_date,
    ) = load_process_project_data(file_path)

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


# --- New Fixture for Missing Optional Fields ---
@pytest.fixture
def sample_data_missing_optional(tmp_path):
    """Creates temporary JSON data missing optional fields."""
    data = {
        'project_info': {
            # 'name': missing -> should default
            'start_date': '2025-02-01',
            # 'publish_date': missing -> should be None
            # 'calendar': missing -> should default to standard
        },
        'tasks': [
            {
                'id': 10,
                'name': 'Minimal Task',
                'start': 1,
                'finish': 2,
                'type': 'FREE',
                'chain': 'MC',
                # 'resources': missing -> should default to ""
                # 'tags': missing -> should default to []
                # 'url': missing -> should default to None
                # 'remaining': missing -> should default to 0 remaining / has_remaining_data=False
                # 'predecessors': missing -> should result in no dependencies
            },
        ],
    }
    file_path = tmp_path / 'missing_optional.json'
    with open(file_path, 'w') as f:
        json.dump(data, f)
    return file_path


def test_load_standard_calendar(sample_json_data_standard):
    """Tests loading data with a standard calendar and basic fields."""
    file_path = sample_json_data_standard
    (
        start_date,
        tasks,
        dependencies,
        stream_map,
        calendar,
        name,
        publish_date,
        is_synthetic_start_date,
    ) = load_process_project_data(file_path)

    # Assertions
    assert start_date is not None
    assert start_date == datetime(2025, 1, 1, 0, 0, 0)
    assert calendar == 'standard'
    assert name == 'Test Project'
    assert publish_date == datetime(2025, 1, 10, 0, 0, 0)
    assert len(tasks) == 4
    assert len(dependencies) == 1
    assert dependencies[0] == ('Task A', 'Task B')

    task_a = tasks.get('Task A')
    assert task_a is not None
    assert task_a['id'] == 1
    assert task_a['start'] == datetime(2025, 1, 1)
    assert task_a['end'] == datetime(2025, 1, 6)
    assert task_a['total_duration'] == timedelta(days=5)
    assert task_a['type'] == TaskType.CRITICAL
    assert task_a['chain'] == 'C1'
    assert task_a['resources'] == 'R1'
    assert task_a['tags'] == ['tag1']
    assert task_a['url'] == 'http://example.com/a'
    assert not task_a['has_remaining_data']

    task_b = tasks.get('Task B')
    assert task_b is not None
    assert task_b['start'] == datetime(2025, 1, 6)
    assert task_b['end'] == datetime(2025, 1, 11)
    assert task_b['total_duration'] == timedelta(days=5)
    assert task_b['remaining_duration'] == timedelta(days=2)
    assert task_b['completed_duration'] == timedelta(days=3)
    assert task_b['has_remaining_data'] is True

    task_c = tasks.get('Task C')
    assert task_c is not None
    assert task_c['type'] == TaskType.UNASSIGNED

    task_d = tasks.get('Task D')
    assert task_d is not None
    assert task_d['start'] == datetime(2025, 1, 11)
    assert task_d['end'] == datetime(2025, 1, 11)
    assert task_d['total_duration'] == timedelta(days=0)


def test_load_missing_file():
    """Tests behavior when the JSON file doesn't exist."""
    result = load_process_project_data('non_existent_file.json')
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
    # Use today's date as a base, normalize to midnight, then adjust
    today_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    expected = (today_midnight, {}, [], {}, 'continuous', 'No Start Date', None, True)
    assert result == expected


# --- New Test for Missing Optional Fields ---
def test_load_missing_optional_fields(sample_data_missing_optional):
    """Tests default values when optional fields are missing."""
    file_path = sample_data_missing_optional
    (
        start_date,
        tasks,
        dependencies,
        stream_map,
        calendar,
        name,
        publish_date,
        is_synthetic_start_date,
    ) = load_process_project_data(file_path)

    # Check project_info defaults
    assert start_date == datetime(2025, 2, 1)  # Check start date is still loaded
    assert name == 'Project'  # Default name
    assert publish_date is None  # Default publish_date
    assert calendar == 'standard'  # Default calendar

    # Check task defaults
    assert len(tasks) == 1
    minimal_task = tasks.get('Minimal Task')
    assert minimal_task is not None

    assert minimal_task['resources'] == ''
    assert minimal_task['tags'] == []
    assert minimal_task['url'] is None
    assert minimal_task['remaining_duration'] == timedelta(0)
    assert (
        minimal_task['completed_duration'] == minimal_task['total_duration']
    )  # Should equal total
    assert minimal_task['has_remaining_data'] is False
    assert minimal_task['predecessors_str'] == ''  # Check the raw string field

    # Check dependencies (should be empty as predecessors was missing)
    assert len(dependencies) == 0


# --- Test for process_project_data (API usage) ---
def test_process_data_missing_optional():
    """Tests default values using the process_project_data API."""
    project_info = {
        'start_date': '2025-03-01',
        # Missing name, publish_date, calendar
    }
    tasks_list = [
        {
            'id': 20,
            'name': 'API Task',
            'start': 0,
            'finish': 1,
            'type': 'BUFFER',
            'chain': 'API',
            # Missing resources, tags, url, remaining, predecessors
        }
    ]

    (
        start_date,
        tasks,
        dependencies,
        stream_map,
        calendar,
        name,
        publish_date,
        is_synthetic_start_date,
    ) = process_project_data(project_info, tasks_list)

    # Check project_info defaults
    assert start_date == datetime(2025, 3, 1)
    assert name == 'Project'
    assert publish_date is None
    assert calendar == 'standard'

    # Check task defaults
    assert len(tasks) == 1
    api_task = tasks.get('API Task')
    assert api_task is not None

    assert api_task['resources'] == ''
    assert api_task['tags'] == []
    assert api_task['url'] is None
    assert api_task['remaining_duration'] == timedelta(0)
    assert api_task['completed_duration'] == api_task['total_duration']
    assert api_task['has_remaining_data'] is False
    assert api_task['predecessors_str'] == ''

    assert len(dependencies) == 0


# Add more tests for:
# - 'continuous' calendar type
# - Invalid date formats
# - Invalid predecessor IDs
# - Empty tasks list
