# pyganttccpm/loader.py
import json
from datetime import datetime, timedelta
import sys
from .config import TaskType
import logging
import math  # Import math for infinity

log = logging.getLogger('pyganttccpm')  # <-- Get the library logger


# --- New Processing Function ---
def process_project_data(project_info_dict, tasks_list):
    """Processes project data provided as Python dicts/lists."""
    project_start_date = None
    calendar_type = 'standard'
    project_name = 'Project'
    project_publish_date = None
    is_synthetic_start_date = False

    # --- Process Project Info ---
    project_name = project_info_dict.get('name', 'Project')
    raw_calendar_type = project_info_dict.get('calendar', 'standard').lower()
    if raw_calendar_type in ['standard', 'continuous']:
        calendar_type = raw_calendar_type
    else:
        log.warning(
            f"Warning: Invalid calendar type '{project_info_dict.get('calendar', '')}'. Defaulting to 'standard'."
        )
        calendar_type = 'standard'

    raw_publish_date_str = project_info_dict.get('publish_date')
    if raw_publish_date_str:
        try:
            # Use dateutil if available, otherwise isoformat
            try:
                from dateutil import parser

                project_publish_date = parser.parse(raw_publish_date_str)
            except ImportError:
                project_publish_date = datetime.fromisoformat(raw_publish_date_str)
        except (ValueError, TypeError) as e:
            log.warning(
                f"Warning: Could not parse project publish date '{raw_publish_date_str}'. {e}"
            )
            project_publish_date = None

    # --- Process Start Date (or synthesize if missing/invalid) ---
    raw_start_date_str = project_info_dict.get('start_date')
    start_date_valid = False
    if raw_start_date_str:
        try:
            try:
                from dateutil import parser

                parsed_start_date = parser.parse(raw_start_date_str)
            except ImportError:
                parsed_start_date = datetime.fromisoformat(raw_start_date_str)
            # Normalize valid start date
            project_start_date = parsed_start_date.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            start_date_valid = True
        except (ValueError, TypeError, AttributeError) as e:
            log.warning(
                f"Invalid project start date '{raw_start_date_str}': {e}. Synthesizing start date."
            )
            # Proceed to synthesize below

    if not start_date_valid:
        is_synthetic_start_date = True
        log.info(
            'Project start date missing or invalid. Defaulting to continuous calendar and synthesizing start date based on earliest task.'
        )
        calendar_type = 'continuous'  # Force continuous calendar

        # Find minimum start offset from tasks
        min_offset = math.inf
        has_tasks = False
        for task_item in tasks_list:
            try:
                offset = float(task_item.get('start', 0))
                min_offset = min(min_offset, offset)
                has_tasks = True
            except (ValueError, TypeError):
                continue  # Ignore tasks with invalid start offsets for this calculation

        if not has_tasks or min_offset == math.inf:
            log.warning(
                'No valid task start offsets found. Using today as Day 0 for synthetic start date.'
            )
            min_offset = 0

        # Create synthetic start date so Day 0 aligns with min_offset
        # Use today's date as a base, normalize to midnight, then adjust
        today_midnight = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        project_start_date = today_midnight - timedelta(days=min_offset)
        log.info(
            f'Synthetic Project Start Date (for Day 0 = offset {min_offset}): {project_start_date.isoformat()}'
        )

    # --- End Process Start Date ---

    # --- Process Tasks (similar logic as load_process_project_data) ---
    tasks = {}
    stream_map = {}
    id_to_name = {}

    # First pass...
    for task_item in tasks_list:  # Iterate over the input list
        task_id = task_item.get('id')
        task_name = task_item.get('name')
        if task_id is None or task_name is None:
            continue
        id_to_name[task_id] = task_name
        try:
            start_offset = float(task_item.get('start', 0))
            finish_offset = float(task_item.get('finish', start_offset))
            start_datetime = project_start_date + timedelta(days=start_offset)
            end_datetime = project_start_date + timedelta(days=finish_offset)
            if end_datetime <= start_datetime:
                end_datetime = start_datetime
            total_duration_td = end_datetime - start_datetime
            remaining_offset = task_item.get('remaining')
            remaining_duration_td = timedelta(0)
            has_remaining_data = False
            if remaining_offset is not None:
                has_remaining_data = True
                try:
                    remaining_offset_float = float(remaining_offset)
                    if remaining_offset_float < 0:
                        remaining_offset_float = 0
                    remaining_duration_td = timedelta(days=remaining_offset_float)
                    if remaining_duration_td > total_duration_td:
                        remaining_duration_td = total_duration_td
                except (ValueError, TypeError):
                    remaining_duration_td = timedelta(0)
                    has_remaining_data = False
            completed_duration_td = total_duration_td - remaining_duration_td
            type_str = task_item.get('type', 'UNASSIGNED').upper()
            try:
                task_type = TaskType[type_str]
            except KeyError:
                task_type = TaskType.UNASSIGNED
            task_url = task_item.get('url', None)
            task_tags = task_item.get('tags', [])
            if not isinstance(task_tags, list):
                task_tags = []

            tasks[task_name] = {
                'id': task_id,
                'start': start_datetime,
                'end': end_datetime,
                'total_duration': total_duration_td,
                'completed_duration': completed_duration_td,
                'remaining_duration': remaining_duration_td,
                'has_remaining_data': has_remaining_data,
                'type': task_type,
                'chain': task_item.get('chain', 'Unknown'),
                'resources': task_item.get('resources', ''),
                'predecessors_str': task_item.get('predecessors', ''),
                'url': task_url,
                'tags': task_tags,
            }
            stream_map[task_name] = tasks[task_name]['chain']
        except (ValueError, TypeError) as e:
            log.warning(
                f"Warning: Skipping task '{task_name}' (ID: {task_id}) due to invalid data: {e}"
            )
            continue

    # Second pass: resolve dependencies
    dependencies = []
    for task_name, task_data in tasks.items():
        pred_str = task_data.get('predecessors_str', '')
        if pred_str:
            try:
                # Assuming predecessors are given as string of IDs, convert to names
                pred_ids = [
                    int(p_id.strip()) for p_id in pred_str.split(',') if p_id.strip()
                ]
                for p_id in pred_ids:
                    pred_name = id_to_name.get(p_id)
                    if pred_name:
                        dependencies.append((pred_name, task_name))
                    else:
                        log.warning(
                            f"Warning: Predecessor ID '{p_id}' not found for task '{task_name}'."
                        )
            except ValueError:
                log.warning(
                    f"Warning: Invalid predecessor format '{pred_str}' for task '{task_name}'."
                )
    # --- End Process Tasks ---

    return (
        project_start_date,
        tasks,
        dependencies,
        stream_map,
        calendar_type,
        project_name,
        project_publish_date,
        is_synthetic_start_date,
    )


# --- Keep the original load_process_project_data function ---
def load_process_project_data(file_path):
    """Loads project data from JSON and processes it."""
    project_info_dict = {}
    tasks_list = []
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        project_info_dict = data.get('project_info', {})
        tasks_list = data.get('tasks', [])
    except FileNotFoundError:
        log.error(f'Error: JSON file not found at {file_path}')
        return None, None, None, None, None, None, None, None
    except json.JSONDecodeError:
        log.error(f'Error: Could not decode JSON from {file_path}')
        return None, None, None, None, None, None, None, None

    # Delegate processing to the new function
    return process_project_data(project_info_dict, tasks_list)
