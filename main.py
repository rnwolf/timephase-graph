import matplotlib as mpl  # Make sure matplotlib is imported
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches  # Needed for legend
import matplotlib.ticker as mticker  # Import ticker for axis formatting
import networkx as nx
from datetime import datetime, timedelta
import json
from enum import Enum, auto  # Import Enum
import sys  # For exiting on error

# --- Configuration ---
JSON_FILE_PATH = "project-gantt-data.json"
OUTPUT_SVG_FILE = "gantt_chart.svg"
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

# *** Add this line to set the default timezone for Matplotlib date handling ***
mpl.rcParams["timezone"] = "UTC"


# --- Data Loading and Processing Function ---
def load_process_project_data(file_path):
    """Loads project data from JSON, calculates dates, and prepares graph structures."""
    project_start_date = None  # Initialize
    calendar_type = "standard"  # Default calendar type
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {file_path}")
        return None, None, None, None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None, None, None, None

    project_info = data.get("project_info", {})
    tasks_data = data.get("tasks", [])

    # --- Get Calendar Type ---
    raw_calendar_type = project_info.get("calendar", "standard").lower()
    if raw_calendar_type in ["standard", "continuous"]:
        calendar_type = raw_calendar_type
    else:
        print(
            f"Warning: Invalid calendar type '{project_info.get('calendar', '')}'. Defaulting to 'standard'."
        )
        calendar_type = "standard"
    print(f"Using calendar type: {calendar_type}")
    # --- End Calendar Type ---

    try:
        # Parse the date string (might include time)
        raw_start_date_str = project_info.get("start_date")
        if raw_start_date_str is None:
            raise ValueError("Project start date is missing in JSON")

        try:
            from dateutil import parser

            parsed_start_date = parser.parse(raw_start_date_str)
        except ImportError:
            # print("Warning: dateutil not found. Using basic ISO format parsing.")
            parsed_start_date = datetime.fromisoformat(raw_start_date_str)

        # --- Normalize to midnight ---
        project_start_date = parsed_start_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        print(
            f"Normalized Project Start Date (Midnight): {project_start_date.isoformat()}"
        )
        # --- End Normalization ---

    except (ValueError, TypeError, AttributeError) as e:
        print(
            f"Error: Invalid or missing project start date: {project_info.get('start_date')}. {e}"
        )
        return None, None, None, None, None

    tasks = {}
    dependencies = []
    stream_map = {}
    id_to_name = {}

    # First pass...
    for task_item in tasks_data:
        task_id = task_item.get("id")
        task_name = task_item.get("name")
        if task_id is None or task_name is None:
            print(f"Warning: Skipping task with missing id or name: {task_item}")
            continue
        id_to_name[task_id] = task_name
        try:
            start_offset = float(task_item.get("start", 0))
            finish_offset = float(task_item.get("finish", start_offset))

            print(project_start_date)
            print(timedelta(days=start_offset))
            # --- Corrected date calculations based on finish index meaning ---
            # Start date is midnight at the beginning of the start_offset day
            start_datetime = project_start_date + timedelta(days=start_offset)

            # End date is midnight at the beginning of the finish_offset day
            # (meaning the task ends just before this time)
            end_datetime = project_start_date + timedelta(days=finish_offset)
            # --- End of correction ---

            # --- DEBUG PRINT for the specific task ---
            # Check if this is the task you're interested in (e.g., start offset is 0)
            if start_offset == 0 and finish_offset == 30:
                print("-" * 20)
                print(f"DEBUG: Task '{task_name}' (ID: {task_id})")
                print(f"  JSON start: {start_offset}, finish: {finish_offset}")
                print(f"  Calculated start_datetime: {start_datetime.isoformat()}")
                print(f"  Calculated end_datetime:   {end_datetime.isoformat()}")
                print("-" * 20)
            # --- END DEBUG PRINT ---

            # Check if calculated end is not after start
            if end_datetime <= start_datetime:
                print(
                    f"Warning: Task '{task_name}' (ID: {task_id}) has finish offset not after start offset. Setting zero effective duration at start time."
                )
                end_datetime = start_datetime  # Set end time equal for zero duration

            duration = end_datetime - start_datetime

            type_str = task_item.get("type", "UNASSIGNED").upper()
            try:
                task_type = TaskType[type_str]
            except KeyError:
                print(
                    f"Warning: Unknown task type '{type_str}' for task '{task_name}'. Using UNASSIGNED."
                )
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

    return project_start_date, tasks, dependencies, stream_map, calendar_type


# --- Function to add Global START/END Nodes ---
def add_global_start_end(G, tasks, stream_map):
    """Adds global START and END nodes, assigning type and chain. Modifies tasks and stream_map in place."""
    start_node_name = START_NODE
    end_node_name = END_NODE

    if start_node_name in G or end_node_name in G:
        print("Info: START/END nodes already exist.")
        return  # Already added

    if not G.nodes:
        print("Warning: Graph is empty, cannot add START/END nodes.")
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
        data["start"]
        for name, data in tasks.items()
        if isinstance(data.get("start"), datetime)
        and name not in [start_node_name, end_node_name]
    ]
    all_ends = [
        data["end"]
        for name, data in tasks.items()
        if isinstance(data.get("end"), datetime)
        and name not in [start_node_name, end_node_name]
    ]

    if not all_starts or not all_ends:
        # If only START/END nodes exist or no valid dates, create a default range
        if tasks:
            base_date = next(iter(tasks.values())).get("start", datetime.now())
        else:
            base_date = datetime.now()
        min_start_date = base_date
        max_end_date = base_date + timedelta(days=1)
        print(
            "Warning: Could not determine date range from tasks. Using default range."
        )
    else:
        min_start_date = min(all_starts)
        max_end_date = max(all_ends)

    # Define START/END Task Data
    start_node_date = min_start_date - timedelta(days=1)
    start_task_data = {
        "id": "START",
        "start": start_node_date,
        "end": start_node_date,
        "duration": timedelta(0),
        "type": TaskType.SYSTEM,
        "chain": "System",
        "resources": "",
    }
    end_node_date = max_end_date + timedelta(days=2)
    end_task_data = {
        "id": "END",
        "start": end_node_date,
        "end": end_node_date,
        "duration": timedelta(0),
        "type": TaskType.SYSTEM,
        "chain": "System",
        "resources": "",
    }

    # Add Nodes and Edges (Modifies G, tasks, stream_map directly)
    G.add_node(start_node_name, **start_task_data)
    tasks[start_node_name] = start_task_data
    stream_map[start_node_name] = start_task_data["chain"]

    G.add_node(end_node_name, **end_task_data)
    tasks[end_node_name] = end_task_data
    stream_map[end_node_name] = end_task_data["chain"]

    print(f"Connecting START to roots: {root_nodes}")
    for root in root_nodes:
        G.add_edge(start_node_name, root)
    print(f"Connecting leaves to END: {leaf_nodes}")
    for leaf in leaf_nodes:
        G.add_edge(leaf, end_node_name)


# --- Plotting Function ---
def plot_project_gantt_with_start_end(
    project_start_date, tasks, dependencies, stream_map, calendar_type="standard"
):
    """
    Generates the Gantt chart plot including START/END nodes.

    Args:
        project_start_date (datetime): The official start date of the project.
        tasks (dict): Dictionary of task data (potentially modified by add_global_start_end).
        dependencies (list): List of dependency tuples [(u, v), ...].
        stream_map (dict): Dictionary mapping task names to stream/chain names
                           (potentially modified by add_global_start_end).
        calendar_type (str): 'standard' or 'continuous'.

    Returns:
        matplotlib.figure.Figure: The generated Matplotlib figure object.
    """
    print("Generating Gantt plot...")

    # 1. Build Graph (including START/END if not already present)
    G = nx.DiGraph()
    for task_name, data in tasks.items():
        G.add_node(task_name, **data)
    G.add_edges_from(dependencies)

    # Add START/END nodes (modifies tasks and stream_map in place)
    # Note: This assumes tasks/stream_map passed in might not have START/END yet
    # If they are guaranteed to be added before calling this function, this call can be removed.
    add_global_start_end(G, tasks, stream_map)

    # 2. Layout Calculations
    # *** Ensure base is calculated from midnight ***
    project_start_midnight = datetime(
        project_start_date.year,
        project_start_date.month,
        project_start_date.day,
        0,
        0,
        0,  # Explicitly set time to 00:00:00
        # tzinfo can be omitted if mpl.rcParams['timezone'] = 'UTC' is set,
        # otherwise consider adding tzinfo=timezone.utc if needed.
    )
    project_start_num_base = mdates.date2num(project_start_midnight)
    # *** End of base calculation adjustment ***

    # 2. Layout Calculations
    unique_chains = sorted(list(set(stream_map.values())))
    stream_levels = {chain: i for i, chain in enumerate(unique_chains)}
    y_levels = {}
    for task_name in G.nodes():
        chain = stream_map.get(task_name)
        if chain is not None and chain in stream_levels:
            y_levels[task_name] = -stream_levels[chain]
        else:
            # This case should ideally not happen if add_global_start_end ran correctly
            print(
                f"Warning: Task '{task_name}' missing chain/stream level. Assigning default y=0."
            )
            y_levels[task_name] = 0

    # 3. Calculate Date Range for Plotting
    all_dates = [
        data["start"]
        for data in tasks.values()
        if isinstance(data.get("start"), datetime)
    ] + [
        data["end"] for data in tasks.values() if isinstance(data.get("end"), datetime)
    ]
    if not all_dates:
        min_date = project_start_date  # Use project start if no tasks
        max_date = min_date + timedelta(days=7)
        print(
            "Warning: No valid dates found in tasks for range calculation. Using default range."
        )
    else:
        min_date = min(all_dates)
        max_date = max(all_dates)

    plot_start_date = min_date - timedelta(days=1)
    plot_limit_end_date = max_date + timedelta(days=1.5)
    plot_start_num = mdates.date2num(plot_start_date)
    plot_limit_end_num = mdates.date2num(plot_limit_end_date)

    # 4. --- PLOTTING ---
    fig, ax = plt.subplots(figsize=(16, 8))

    # --- Add Weekend Shading (if standard calendar) ---
    if calendar_type == "standard":
        print("Applying weekend shading...")
        # Ensure we iterate starting from midnight of the plot_start_date
        iter_start_date = datetime(
            plot_start_date.year, plot_start_date.month, plot_start_date.day
        )
        # Iterate up to the day *after* the plot limit to ensure the last day is included
        iter_end_limit = datetime(
            plot_limit_end_date.year, plot_limit_end_date.month, plot_limit_end_date.day
        ) + timedelta(days=1)

        current_date = iter_start_date
        while (
            current_date < iter_end_limit
        ):  # Loop until the start of the day after the limit
            weekday = current_date.weekday()
            if weekday >= 5:  # Saturday (5) or Sunday (6)
                # Explicitly define start and end datetimes as midnight
                day_start_dt = datetime(
                    current_date.year, current_date.month, current_date.day, 0, 0, 0
                )
                # The end is midnight of the *next* day
                day_end_dt = day_start_dt + timedelta(days=1)

                # Convert precise midnight datetimes to numbers
                day_start_num = mdates.date2num(day_start_dt)
                day_end_num = mdates.date2num(day_end_dt)

                # Draw the vertical span using these precise boundaries
                ax.axvspan(
                    day_start_num,
                    day_end_num,
                    facecolor="lightgray",
                    alpha=0.3,
                    zorder=-1,  # Ensure it's behind grid lines and bars
                )
            current_date += timedelta(days=1)
    # --- End Weekend Shading ---

    # Plot Bars
    for task_name, data in tasks.items():
        if isinstance(data.get("start"), datetime) and isinstance(
            data.get("end"), datetime
        ):
            start_num = mdates.date2num(data["start"])
            end_num = mdates.date2num(data["end"])
            y = y_levels.get(task_name, 0)
            task_type = data.get("type", TaskType.UNASSIGNED)
            color = TASK_COLORS.get(task_type, TASK_COLORS[TaskType.UNASSIGNED])

            if start_num < end_num:
                ax.barh(
                    y,
                    end_num - start_num,
                    left=start_num,
                    height=0.5,
                    color=color,
                    edgecolor="k",
                    alpha=0.8,
                )
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

    # Add markers and annotations for START/END nodes
    for node_name in [START_NODE, END_NODE]:
        if node_name in tasks and node_name in y_levels:
            node_data = tasks[node_name]
            if isinstance(node_data.get("start"), datetime):
                node_date = node_data["start"]
                x_pos = mdates.date2num(node_date)
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
                )
                date_str = node_date.strftime("%b %d")
                ax.annotate(
                    date_str,
                    xy=(x_pos, y_pos),
                    xytext=(5, 5),
                    textcoords="offset points",
                    ha="left",
                    va="bottom",
                    fontsize=8,
                    color="black",
                )

    # Draw Dependency Arrows
    arrowprops = dict(
        arrowstyle="->", color="gray", lw=1, connectionstyle="arc3,rad=0.1"
    )
    for u, v in G.edges():
        # Check if edge source/target are in tasks and have y_levels before proceeding
        if u not in tasks or v not in tasks or u not in y_levels or v not in y_levels:
            print(
                f"Warning: Skipping arrow for edge {u}->{v} due to missing task data or y-level."
            )
            continue

        data_u = tasks[u]
        data_v = tasks[v]
        y_level_u = y_levels[u]
        y_level_v = y_levels[v]

        if isinstance(data_u.get("end"), datetime) and isinstance(
            data_v.get("start"), datetime
        ):
            x_start = mdates.date2num(data_u["end"])
            y_start = y_level_u
            x_end = mdates.date2num(data_v["start"])
            y_end = y_level_v
            if abs(x_start - x_end) > 0.01 or abs(y_start - y_end) > 0.01:
                ax.annotate(
                    "",
                    xy=(x_end, y_end),
                    xytext=(x_start, y_start),
                    arrowprops=arrowprops,
                )
        else:
            print(
                f"Warning: Missing start/end dates for dependency {u}->{v}. Skipping arrow."
            )

    # 5. Configure Axes
    ax.set_xlim(plot_start_num, plot_limit_end_num)
    # --- Configure Bottom X-axis (Dates) ---
    # *** Use DayLocator to force ticks at midnight ***
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    # Minor ticks can be useful for seeing hours if zoomed, but not strictly needed for alignment
    # ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))

    ax.set_xlabel("Date")
    ax.set_title("Project Timeline Gantt Chart")
    ax.invert_yaxis()
    ax.grid(True, axis="x", linestyle="--", alpha=0.6)
    ax.set_yticks(sorted(list(set(y_levels.values()))))
    level_to_chain = {lvl: chain for chain, lvl in stream_levels.items()}
    y_tick_labels = [
        level_to_chain.get(-y, f"Level {-y}")
        for y in sorted(list(set(y_levels.values())))
    ]
    ax.set_yticklabels(y_tick_labels)
    ax.set_ylabel("Task Chain")
    fig.autofmt_xdate(rotation=30, ha="right")

    # --- Configure Top X-axis (Day Index) ---
    ax2 = ax.twiny()
    lim_min_num, lim_max_num = ax.get_xlim()
    ax2.set_xlim(lim_min_num, lim_max_num)

    # --- Link the Locators and Apply FuncFormatter ---
    bottom_locator = ax.xaxis.get_major_locator()
    ax2.xaxis.set_major_locator(bottom_locator)  # Keep locators linked

    # 3. Define the formatter function (using round())
    def day_index_formatter(tick_val, pos):
        # Calculate the difference in days (float)
        day_index_float = tick_val - project_start_num_base
        # Round the float to the NEAREST integer for the label
        day_index_int = round(day_index_float)
        # --- Optional Debug Print (Uncomment to diagnose further if needed) ---
        # try:
        #     tick_dt = mdates.num2date(tick_val)
        #     # Check specifically around the expected start date tick
        #     if abs(tick_val - project_start_num_base) < 0.1 or abs(tick_val - (project_start_num_base + 1)) < 0.1:
        #          print(f"Tick Date: {tick_dt.strftime('%Y-%m-%d %H:%M')}, Tick Val: {tick_val:.6f}, Base: {project_start_num_base:.6f}, Diff: {day_index_float:.6f}, Rounded Int: {day_index_int}")
        # except Exception as e:
        #     print(f"Debug print error: {e}")
        # --- End Debug Print ---
        return f"{day_index_int}"  # Return the rounded integer as a string

    # 4. Apply the FuncFormatter to the top axis
    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(day_index_formatter))
    # --- End of Linking ---

    ax2.set_xlabel("Day Index (Relative to Project Start)")

    # Link limits callback
    def update_ax2_limits(ax_bottom):
        ax2.set_xlim(ax_bottom.get_xlim())

    ax.callbacks.connect("xlim_changed", update_ax2_limits)

    # 6. Add Legend
    legend_handles = []
    used_types = set(
        task_data["type"] for task_data in tasks.values() if "type" in task_data
    )  # Check 'type' exists
    for task_type in TaskType:
        if task_type in used_types:
            color = TASK_COLORS[task_type]
            label = task_type.name.replace("_", " ").title()
            legend_handles.append(mpatches.Patch(color=color, label=label))
    if legend_handles:  # Only add legend if there are handles
        ax.legend(
            handles=legend_handles,
            title="Task Types",
            bbox_to_anchor=(1.04, 0.5),
            loc="center left",
            borderaxespad=0.0,
        )
        plt.subplots_adjust(right=0.85)  # Adjust layout only if legend is present

    print("Gantt plot generated.")
    return fig


# --- Main Execution ---
if __name__ == "__main__":
    # 1. Load Data from File
    print(f"Loading data from {JSON_FILE_PATH}...")
    project_start_date, tasks, dependencies, stream_map, calendar_type = (
        load_process_project_data(JSON_FILE_PATH)
    )
    if tasks is None or project_start_date is None:
        print("Failed to load or process project data. Exiting.")
        sys.exit(1)  # Exit with error code
    print("Data loaded successfully.")

    # 2. Create the Gantt Plot
    # Note: START/END nodes are added within the plotting function now
    fig = plot_project_gantt_with_start_end(
        project_start_date, tasks, dependencies, stream_map, calendar_type
    )

    # 3. Save Plot to SVG File
    if fig:
        try:
            print(f"Saving plot to {OUTPUT_SVG_FILE}...")
            # Use bbox_inches='tight' to include elements like the legend
            fig.savefig(OUTPUT_SVG_FILE, format="svg", bbox_inches="tight")
            print("Plot saved successfully.")
        except Exception as e:
            print(f"Error saving plot to SVG: {e}")
    else:
        print("Plot figure was not generated, skipping save.")

    # 4. Show the Plot
    if fig:
        print("Displaying plot...")
        plt.show()
    else:
        print("Plot figure was not generated, skipping display.")
