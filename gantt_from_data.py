import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches  # Needed for legend
import matplotlib.ticker as mticker  # Import ticker for axis formatting
import networkx as nx
from datetime import datetime, timedelta
import json
from enum import Enum, auto  # Import Enum

# --- Configuration ---
JSON_FILE_PATH = "project-gantt-data.json"
START_NODE = "START"  # Define global node names
END_NODE = "END"


# --- Task Type Enum and Colors ---
class TaskType(Enum):
    UNASSIGNED = auto()
    CRITICAL = auto()
    FEEDING = auto()
    FREE = auto()
    BUFFER = auto()
    SYSTEM = auto()  # Added for START/END nodes


TASK_COLORS = {
    TaskType.UNASSIGNED: "purple",
    TaskType.CRITICAL: "red",
    TaskType.FEEDING: "orange",
    TaskType.FREE: "blue",
    TaskType.BUFFER: "gray",
    TaskType.SYSTEM: "black",  # Color for START/END nodes
}


# --- Data Loading and Processing Function (Modified Return) ---
def load_process_project_data(file_path):
    """Loads project data from JSON, calculates dates, and prepares graph structures."""
    project_start_date = None  # Initialize
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {file_path}")
        return None, None, None, None  # Added None for start_date
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None, None, None, None  # Added None for start_date

    project_info = data.get("project_info", {})
    tasks_data = data.get("tasks", [])

    try:
        # Use dateutil.parser for robust date parsing if available, otherwise basic ISO format
        try:
            from dateutil import parser

            project_start_date = parser.parse(project_info.get("start_date"))
        except ImportError:
            print("Warning: dateutil not found. Using basic ISO format parsing.")
            project_start_date = datetime.fromisoformat(project_info.get("start_date"))

    except (ValueError, TypeError) as e:
        print(
            f"Error: Invalid project start date format: {project_info.get('start_date')}. {e}"
        )
        project_start_date = datetime.now()  # Fallback to now
        print(f"Using current date as fallback: {project_start_date}")

    # --- Rest of the function remains the same ---
    tasks = {}
    dependencies = []
    stream_map = {}
    id_to_name = {}

    print(f"Project Start Date: {project_start_date.strftime('%Y-%m-%d')}")

    # First pass...
    for task_item in tasks_data:
        # ... (task processing logic) ...
        task_id = task_item.get("id")
        task_name = task_item.get("name")
        if task_id is None or task_name is None:
            continue
        id_to_name[task_id] = task_name
        try:
            start_offset = float(task_item.get("start", 0))
            finish_offset = float(task_item.get("finish", start_offset))
            start_datetime = project_start_date + timedelta(days=start_offset)
            end_datetime = project_start_date + timedelta(days=finish_offset)
            if end_datetime < start_datetime:
                end_datetime = start_datetime
            duration = end_datetime - start_datetime
            type_str = task_item.get("type", "UNASSIGNED").upper()
            try:
                task_type = TaskType[type_str]
            except KeyError:
                task_type = TaskType.UNASSIGNED
            tasks[task_name] = {
                "id": task_id,
                "start": start_datetime,
                "end": end_datetime,
                "duration": duration,
                "type": task_type,
                "chain": task_item.get("chain", "Unknown"),
                "resources": task_item.get("resources", ""),
                "predecessors_str": task_item.get("predecessors", ""),
            }
            stream_map[task_name] = tasks[task_name]["chain"]
        except (ValueError, TypeError) as e:
            print(
                f"Warning: Skipping task '{task_name}' (ID: {task_id}) due to invalid data: {e}"
            )
            continue

    # Second pass...
    for task_name, task_data in tasks.items():
        # ... (dependency processing logic) ...
        pred_str = task_data.get("predecessors_str", "")
        if pred_str:
            try:
                pred_ids = [
                    int(p_id.strip()) for p_id in pred_str.split(",") if p_id.strip()
                ]
                for p_id in pred_ids:
                    pred_name = id_to_name.get(p_id)
                    if pred_name:
                        dependencies.append((pred_name, task_name))
                    else:
                        print(
                            f"Warning: Predecessor ID '{p_id}' not found for task '{task_name}'."
                        )
            except ValueError:
                print(
                    f"Warning: Invalid predecessor format '{pred_str}' for task '{task_name}'."
                )

    # *** Return project_start_date as well ***
    return project_start_date, tasks, dependencies, stream_map


# --- Function to add Global START/END Nodes (Modified for Type/Chain) ---
def add_global_start_end(G, tasks, stream_map):
    """Adds global START and END nodes, assigning type and chain."""
    start_node_name = START_NODE
    end_node_name = END_NODE

    if start_node_name in G or end_node_name in G:
        return G, tasks, stream_map  # Already added

    if not G.nodes:
        return G, tasks, stream_map  # Empty graph

    root_nodes = [node for node, degree in G.in_degree() if degree == 0]
    leaf_nodes = [node for node, degree in G.out_degree() if degree == 0]

    all_starts = [
        data["start"]
        for data in tasks.values()
        if isinstance(data.get("start"), datetime)
    ]
    all_ends = [
        data["end"] for data in tasks.values() if isinstance(data.get("end"), datetime)
    ]

    if not all_starts or not all_ends:
        min_start_date = datetime.now()
        max_end_date = min_start_date + timedelta(days=1)
    else:
        min_start_date = min(all_starts)
        max_end_date = max(all_ends)

    # Define START/END Task Data
    start_node_date = min_start_date - timedelta(days=1)
    start_task_data = {
        "id": "START",  # Use string ID
        "start": start_node_date,
        "end": start_node_date,
        "duration": timedelta(0),
        "type": TaskType.SYSTEM,
        "chain": "System",
        "resources": "",
    }
    # Place END node further out
    end_node_date = max_end_date + timedelta(days=2)
    end_task_data = {
        "id": "END",  # Use string ID
        "start": end_node_date,
        "end": end_node_date,
        "duration": timedelta(0),
        "type": TaskType.SYSTEM,
        "chain": "System",
        "resources": "",
    }

    # Add Nodes and Edges
    G.add_node(start_node_name, **start_task_data)
    tasks[start_node_name] = start_task_data
    stream_map[start_node_name] = start_task_data["chain"]  # Add to stream map

    G.add_node(end_node_name, **end_task_data)
    tasks[end_node_name] = end_task_data
    stream_map[end_node_name] = end_task_data["chain"]  # Add to stream map

    for root in root_nodes:
        G.add_edge(start_node_name, root)
    for leaf in leaf_nodes:
        G.add_edge(leaf, end_node_name)

    return G, tasks, stream_map


# --- Main Execution ---
if __name__ == "__main__":
    # 1. Load and Process Data
    project_start_date, tasks, dependencies, stream_map = load_process_project_data(
        JSON_FILE_PATH
    )
    if tasks is None:
        exit()

    # Calculate the numerical base for the day index
    project_start_num_base = mdates.date2num(project_start_date)
    print(f"Project Start Date Numerical Base: {project_start_num_base}")

    # 2. Build Initial Graph
    G = nx.DiGraph()
    for task_name, data in tasks.items():
        # Add node with all its data attributes from the tasks dict
        G.add_node(task_name, **data)
    G.add_edges_from(dependencies)

    # 3. Add Global START/END Nodes
    G, tasks, stream_map = add_global_start_end(G, tasks, stream_map)

    # 4. Layout Calculations (Streams and Y-Levels)
    # Assign y-levels by stream (using unique chains)
    unique_chains = sorted(list(set(stream_map.values())))
    stream_levels = {chain: i for i, chain in enumerate(unique_chains)}

    # y-position by task = -stream level
    y_levels = {}
    for task_name in G.nodes():
        chain = stream_map.get(task_name)
        if chain is not None and chain in stream_levels:
            y_levels[task_name] = -stream_levels[chain]
        else:
            print(
                f"Warning: Task '{task_name}' has no chain/stream level. Assigning default y=0."
            )
            y_levels[task_name] = 0

    # Position: x = start date, y = level (needed for markers, maybe arrows if not using annotate)
    pos = {}
    for task_name, data in tasks.items():
        if task_name in y_levels and isinstance(data.get("start"), datetime):
            pos[task_name] = (mdates.date2num(data["start"]), y_levels[task_name])
        else:
            print(f"Warning: Could not determine position for task '{task_name}'.")

    # 5. Calculate Date Range for Plotting (AFTER adding START/END)
    all_dates = [
        data["start"]
        for data in tasks.values()
        if isinstance(data.get("start"), datetime)
    ] + [
        data["end"] for data in tasks.values() if isinstance(data.get("end"), datetime)
    ]

    if not all_dates:
        min_date = datetime.now()
        max_date = min_date + timedelta(days=7)  # Default range if no dates
    else:
        min_date = min(all_dates)
        max_date = max(all_dates)

    # Define plot boundaries with padding
    plot_start_date = min_date - timedelta(days=1)
    plot_limit_end_date = max_date + timedelta(days=1.5)  # Use the extended limit

    plot_start_num = mdates.date2num(plot_start_date)
    plot_limit_end_num = mdates.date2num(plot_limit_end_date)

    # --- PLOTTING ---
    fig, ax = plt.subplots(figsize=(16, 8))  # Adjusted size for legend

    # --- Plot Bars FIRST ---
    for task_name, data in tasks.items():
        if isinstance(data.get("start"), datetime) and isinstance(
            data.get("end"), datetime
        ):
            start_num = mdates.date2num(data["start"])
            end_num = mdates.date2num(data["end"])
            y = y_levels.get(task_name, 0)  # Get y-level, default to 0 if missing
            task_type = data.get("type", TaskType.UNASSIGNED)
            color = TASK_COLORS.get(
                task_type, TASK_COLORS[TaskType.UNASSIGNED]
            )  # Get color

            if start_num < end_num:  # Only draw bar if duration > 0
                ax.barh(
                    y,
                    end_num - start_num,
                    left=start_num,
                    height=0.5,
                    color=color,
                    edgecolor="k",
                    alpha=0.8,
                )

                # Format label: ID Name (Resources)
                task_id = data.get("id", "?")
                resources = data.get("resources", "")
                label_text = f"{task_id} {task_name}"
                if resources:
                    label_text += f" ({resources})"

                ax.text(
                    (start_num + end_num) / 2,
                    y,
                    label_text,
                    va="center",
                    ha="center",
                    fontsize=8,
                    color="black",
                )
            # else: # No need to print warning for START/END anymore, handled by check
            #     pass

    # --- Add markers for START/END nodes (optional, subtle) ---
    for node_name in [START_NODE, END_NODE]:
        if node_name in tasks and node_name in y_levels:
            node_data = tasks[node_name]
            if isinstance(node_data.get("start"), datetime):
                x_pos = mdates.date2num(node_data["start"])
                y_pos = y_levels[node_name]
                task_type = node_data.get("type", TaskType.SYSTEM)
                color = TASK_COLORS.get(task_type, TASK_COLORS[TaskType.SYSTEM])
                ax.plot(
                    x_pos,
                    y_pos,
                    "D",
                    markersize=5,
                    color=color,
                    markeredgecolor="black",
                )  # Diamond marker

                # --- Add Date Annotation ---
                date_str = node_data.get("start").strftime("%b %d")  # Format the date
                ax.annotate(
                    date_str,  # The text to display
                    xy=(x_pos, y_pos),  # The point to annotate (marker position)
                    xytext=(5, 5),  # Offset text slightly (pixels)
                    textcoords="offset points",  # Use pixel offset
                    ha="left",  # Horizontal alignment
                    va="bottom",  # Vertical alignment
                    fontsize=8,  # Adjust font size as needed
                    color="black",  # Text color
                )
                # --- End of Annotation ---

    # --- Draw Dependency Arrows Manually SECOND ---
    arrowprops = dict(
        arrowstyle="->", color="gray", lw=1, connectionstyle="arc3,rad=0.1"
    )
    for u, v in G.edges():
        data_u = tasks.get(u)
        data_v = tasks.get(v)
        y_level_u = y_levels.get(u)
        y_level_v = y_levels.get(v)

        if (
            data_u
            and data_v
            and y_level_u is not None
            and y_level_v is not None
            and isinstance(data_u.get("end"), datetime)
            and isinstance(data_v.get("start"), datetime)
        ):
            x_start = mdates.date2num(data_u["end"])
            y_start = y_level_u
            x_end = mdates.date2num(data_v["start"])
            y_end = y_level_v

            # Avoid drawing arrow if start/end points are identical (e.g., START->Task starting day 0)
            if abs(x_start - x_end) > 0.01 or abs(y_start - y_end) > 0.01:
                ax.annotate(
                    "",
                    xy=(x_end, y_end),
                    xytext=(x_start, y_start),
                    arrowprops=arrowprops,
                )
        else:
            print(
                f"Warning: Missing data/level/dates for dependency {u}->{v}. Skipping arrow."
            )

    # --- Configure Axes THIRD ---
    # 1. Set Explicit X-axis Limits
    ax.set_xlim(plot_start_num, plot_limit_end_num)

    # 2. Apply Date Locator and Formatter (Bottom Axis)
    ax.xaxis.set_major_locator(
        mdates.AutoDateLocator(minticks=5, maxticks=15)
    )  # Auto locator often better
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))  # Keep simple format

    # 3. Configure other plot elements
    ax.set_xlabel("Date")
    ax.set_title("Project Timeline Gantt Chart")
    ax.invert_yaxis()  # Chains sorted 0, 1, 2... top-down
    ax.grid(True, axis="x", linestyle="--", alpha=0.6)

    # Set y-ticks to correspond to stream levels
    ax.set_yticks(sorted(list(set(y_levels.values()))))
    # Create labels from stream names based on sorted y_levels
    level_to_chain = {lvl: chain for chain, lvl in stream_levels.items()}
    y_tick_labels = [
        level_to_chain.get(-y, f"Level {-y}")
        for y in sorted(list(set(y_levels.values())))
    ]
    ax.set_yticklabels(y_tick_labels)
    ax.set_ylabel("Task Chain")

    # 4. Auto-format Date Labels (Bottom Axis)
    fig.autofmt_xdate(rotation=30, ha="right")  # Adjust rotation

    # --- Configure Top X-axis (Numerical Dates) ---
    ax2 = ax.twiny()
    # Calculate the corresponding day index limits
    lim_min_num, lim_max_num = ax.get_xlim()
    lim_min_index = lim_min_num - project_start_num_base
    lim_max_index = lim_max_num - project_start_num_base
    # Set limits for ax2 using the calculated day index range
    ax2.set_xlim(lim_min_index, lim_max_index)
    # Set the label for the top axis
    ax2.set_xlabel("Day Index (Relative to Project Start)")
    # Ensure ticks are placed reasonably, preferably as integers
    ax2.xaxis.set_major_locator(
        mticker.MaxNLocator(integer=True, min_n_ticks=5, nbins="auto")
    )
    # Format ticks as integers
    ax2.xaxis.set_major_formatter(mticker.FormatStrFormatter("%d"))

    # --- Add Legend ---
    legend_handles = []
    # Create patches for legend based on colors used in the plot
    used_types = set(task_data["type"] for task_data in tasks.values())
    for task_type in TaskType:  # Iterate through Enum definition for order
        if task_type in used_types:  # Only add if the type exists in the data
            color = TASK_COLORS[task_type]
            label = task_type.name.replace("_", " ").title()  # Format label nicely
            legend_handles.append(mpatches.Patch(color=color, label=label))

    # Place legend outside the plot area on the right
    ax.legend(
        handles=legend_handles,
        title="Task Types",
        bbox_to_anchor=(1.04, 0.5),
        loc="center left",
        borderaxespad=0.0,
    )

    # --- Final Layout and Show ---
    plt.subplots_adjust(right=0.85)  # Adjust right margin to make space for legend
    # plt.tight_layout() # tight_layout can sometimes conflict with bbox_to_anchor, use subplots_adjust first
    plt.show()
