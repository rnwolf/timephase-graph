# pyganttccpm/graph_utils.py
import networkx as nx
from datetime import datetime, timedelta
from .config import START_NODE, END_NODE, TaskType  # Relative imports
import logging

log = logging.getLogger('pyganttccpm')  # <-- Get the library logger


# --- Function to add Global START/END Nodes ---
def add_global_start_end(G, tasks, stream_map):
    """Adds global START and END nodes, assigning type and chain. Modifies tasks and stream_map in place."""
    # No return needed as it modifies inputs in place, or return G, tasks, stream_map if preferred
    # Ensure it uses START_NODE, END_NODE, TaskType from .config
    start_node_name = START_NODE
    end_node_name = END_NODE

    if not isinstance(G, nx.Graph):
        raise TypeError("The parameter 'G' must be a networkx Graph object.")

    if start_node_name in G or end_node_name in G:
        log.info('Info: START/END nodes already exist.')
        return  # Already added

    if not G.nodes:
        log.warning('Warning: Graph is empty, cannot add START/END nodes.')
        return  # Empty graph

    root_nodes = [
        node
        for node, degree in G.in_degree()
        if degree == 0 and node not in [start_node_name, end_node_name]
    ]
    leaf_nodes = [
        node
        for node, degree in G.out_degree()
        if degree == 0 and node not in [start_node_name, end_node_name]
    ]

    all_starts = [
        data['start']
        for name, data in tasks.items()
        if isinstance(data.get('start'), datetime)
        and name not in [start_node_name, end_node_name]
    ]
    all_ends = [
        data['end']
        for name, data in tasks.items()
        if isinstance(data.get('end'), datetime)
        and name not in [start_node_name, end_node_name]
    ]

    if not all_starts or not all_ends:
        # If only START/END nodes exist or no valid dates, create a default range
        if tasks:
            base_date = next(iter(tasks.values())).get('start', datetime.now())
        else:
            base_date = datetime.now()
        min_start_date = base_date
        max_end_date = base_date + timedelta(days=1)
        log.warning(
            'Warning: Could not determine date range from tasks. Using default range.'
        )
    else:
        min_start_date = min(all_starts)
        max_end_date = max(all_ends)

    # Define START/END Task Data
    start_node_date = min_start_date - timedelta(days=1)
    start_task_data = {
        'id': 'START',
        'start': start_node_date,
        'end': start_node_date,
        'duration': timedelta(0),
        'type': TaskType.SYSTEM,
        'chain': 'System',
        'resources': '',
    }
    end_node_date = max_end_date + timedelta(days=2)
    end_task_data = {
        'id': 'END',
        'start': end_node_date,
        'end': end_node_date,
        'duration': timedelta(0),
        'type': TaskType.SYSTEM,
        'chain': 'System',
        'resources': '',
    }

    # Add Nodes and Edges (Modifies G, tasks, stream_map directly)
    G.add_node(start_node_name, **start_task_data)
    tasks[start_node_name] = start_task_data
    stream_map[start_node_name] = start_task_data['chain']

    G.add_node(end_node_name, **end_task_data)
    tasks[end_node_name] = end_task_data
    stream_map[end_node_name] = end_task_data['chain']

    log.debug(f'Connecting START to roots: {root_nodes}')
    for root in root_nodes:
        G.add_edge(start_node_name, root)
    log.debug(f'Connecting leaves to END: {leaf_nodes}')
    for leaf in leaf_nodes:
        G.add_edge(leaf, end_node_name)

    return G, tasks, stream_map
