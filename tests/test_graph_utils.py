import pytest
import networkx as nx
from datetime import datetime, timedelta
from pyganttccpm.graph_utils import add_global_start_end
from pyganttccpm.config import START_NODE, END_NODE, TaskType


def test_add_start_end_simple():
    """Tests adding START/END to a simple graph."""
    G = nx.DiGraph()
    tasks = {
        'A': {
            'start': datetime(2025, 1, 1),
            'end': datetime(2025, 1, 2),
            'type': TaskType.CRITICAL,
            'chain': 'C1',
        },
        'B': {
            'start': datetime(2025, 1, 2),
            'end': datetime(2025, 1, 3),
            'type': TaskType.CRITICAL,
            'chain': 'C1',
        },
    }
    stream_map = {'A': 'C1', 'B': 'C1'}
    G.add_node('A', **tasks['A'])
    G.add_node('B', **tasks['B'])
    G.add_edge('A', 'B')

    # Function modifies inputs in place
    add_global_start_end(G, tasks, stream_map)

    assert START_NODE in G.nodes
    assert END_NODE in G.nodes
    assert START_NODE in tasks
    assert END_NODE in tasks
    assert START_NODE in stream_map
    assert END_NODE in stream_map

    assert G.has_edge(START_NODE, 'A')  # A is the root
    assert G.has_edge('B', END_NODE)  # B is the leaf
    assert tasks[START_NODE]['type'] == TaskType.SYSTEM
    assert tasks[END_NODE]['type'] == TaskType.SYSTEM


def test_add_start_end_multiple_roots_leaves():
    """Tests adding START/END with multiple disconnected chains."""
    G = nx.DiGraph()
    tasks = {
        'A': {
            'start': datetime(2025, 1, 1),
            'end': datetime(2025, 1, 2),
            'type': TaskType.CRITICAL,
            'chain': 'C1',
        },
        'B': {
            'start': datetime(2025, 1, 1),
            'end': datetime(2025, 1, 2),
            'type': TaskType.CRITICAL,
            'chain': 'C2',
        },
    }
    stream_map = {'A': 'C1', 'B': 'C2'}
    G.add_node('A', **tasks['A'])
    G.add_node('B', **tasks['B'])

    add_global_start_end(G, tasks, stream_map)

    assert G.has_edge(START_NODE, 'A')
    assert G.has_edge(START_NODE, 'B')
    assert G.has_edge('A', END_NODE)
    assert G.has_edge('B', END_NODE)


def test_add_start_end_empty_graph():
    """Tests adding START/END to an empty graph."""
    G = nx.DiGraph()
    tasks = {}
    stream_map = {}
    add_global_start_end(G, tasks, stream_map)
    assert START_NODE not in G.nodes  # Should not add if graph is empty
    assert END_NODE not in G.nodes


# Add more tests for graphs with cycles (if applicable), already existing START/END nodes etc.
