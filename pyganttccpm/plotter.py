# pyganttccpm/plotter.py
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import networkx as nx
from datetime import datetime, timedelta

# Import from other modules within the package
from .config import TASK_COLORS, TaskType, START_NODE, END_NODE
from .graph_utils import add_global_start_end

# Set UTC timezone preference within the module or rely on user setting it
# mpl.rcParams["timezone"] = "UTC" # Consider if this should be enforced or documented


# --- Plotting Function ---
def plot_project_gantt_with_start_end(
    project_start_date,
    tasks,
    dependencies,
    stream_map,
    calendar_type="standard",
    project_name="Project",
    project_publish_date=None,
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
            task_url = data.get("url", None)

            # Get duration values (as timedeltas)
            total_duration_td = data.get("total_duration", timedelta(0))
            completed_duration_td = data.get("completed_duration", timedelta(0))
            has_remaining_data = data.get(
                "has_remaining_data", False
            )  # <<< Get the flag
            task_tags = data.get("tags", [])

            # Draw the main (background) task bar if it has duration
            if total_duration_td > timedelta(0):
                main_bar_height = 0.5  # Define main bar height
                bar_total = ax.barh(
                    y,  # Centered vertically
                    total_duration_td.total_seconds() / (24 * 3600),
                    left=start_num,
                    height=main_bar_height,  # Use defined height
                    color=color,
                    edgecolor="k",
                    alpha=0.5,  # Make background slightly more transparent
                    zorder=2,
                )
                if task_url:
                    bar_total[0].set_url(task_url)

                # --- Draw Progress Bar (Thin bar at the bottom) ---
                if has_remaining_data and completed_duration_td > timedelta(0):
                    completed_width_days = completed_duration_td.total_seconds() / (
                        24 * 3600
                    )
                    progress_bar_height = 0.1  # Define thin height for progress

                    # Calculate y-position for the bottom progress bar
                    # Main bar bottom edge is y - main_bar_height / 2
                    # Center of progress bar should be main_bar_bottom_edge + progress_bar_height / 2
                    y_progress = (y - main_bar_height / 2) + (progress_bar_height / 2)

                    ax.barh(
                        y_progress,  # Positioned along the bottom edge
                        completed_width_days,
                        left=start_num,
                        height=progress_bar_height,  # Use the thin height
                        color=color,  # Use same base color (could also use black or a darker shade)
                        edgecolor=None,  # Remove edge for a cleaner line look
                        alpha=1.0,  # Make progress bar fully opaque
                        zorder=3,  # Draw progress bar on top of main bar
                    )
                # --- End Progress Bar ---

                # --- Text Label ---
                # Position text relative to the main bar's center
                task_id = data.get("id", "?")
                resources = data.get("resources", "")
                label_text = f"{task_id} {task_name}"
                if resources:
                    label_text += f" ({resources})"

                text_label = ax.text(
                    start_num + (total_duration_td.total_seconds() / (24 * 3600)) / 2,
                    y,  # Center text vertically in the main bar
                    label_text,
                    va="center",
                    ha="center",
                    fontsize=8,
                    color="black",
                    zorder=4,  # Ensure text is on top
                )
                if task_url:
                    text_label.set_url(task_url)
                # --- End Text Label ---

                # --- Add Tags Text ---
                if task_tags:
                    tags_str = " ".join(
                        [f"#{tag}" for tag in task_tags]
                    )  # Format as #tag1 #tag2
                    # Position near the right edge of the bar
                    # Use end_num and right alignment, maybe small pixel offset
                    ax.text(
                        end_num,  # X position at the end of the bar
                        y,  # Same vertical center
                        tags_str,
                        ha="right",  # Align text to the right of the x position
                        va="center",
                        fontsize=6,  # Make tags smaller
                        color="white",  # Use white for contrast on colored bars
                        zorder=5,  # Ensure tags are on top
                        # Optional: Add a background box for better readability
                        bbox=dict(
                            facecolor="black",
                            alpha=0.4,
                            pad=1,
                            boxstyle="round,pad=0.1",
                        ),
                    )
                # --- End Add Tags Text ---

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
    # *** Use AutoDateLocator for adaptive ticks ***
    locator = mdates.AutoDateLocator(
        minticks=5, maxticks=10
    )  # Adjust minticks/maxticks as desired
    formatter = mdates.ConciseDateFormatter(locator)  # Use concise formatter

    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    # --- End of AutoDateLocator usage ---

    ax.set_xlabel("Date")

    # --- Construct and Set Title ---
    title_str = f"{project_name} - Timeline"
    if project_publish_date:
        # Format publish date nicely
        title_str += f" (Data as of: {project_publish_date.strftime('%Y-%m-%d %H:%M')})"
    ax.set_title(title_str)  # Use the constructed title
    # --- End Title ---

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

    # --- Add Vertical Line for Publish Date ---
    if project_publish_date:
        publish_date_num = mdates.date2num(project_publish_date)
        # Check if the publish date is within the plotted range
        if plot_start_num < publish_date_num < plot_limit_end_num:
            ax.axvline(
                x=publish_date_num,
                color="blue",  # Choose a distinct color
                linestyle="--",  # Make it dashed
                linewidth=1.5,
                label=f"Publish Date ({project_publish_date.strftime('%Y-%m-%d')})",  # Add label for legend
                zorder=10,  # Ensure it's visible on top of most elements
            )
            print(
                f"Adding vertical line for publish date: {project_publish_date.strftime('%Y-%m-%d')}"
            )
        else:
            print(
                f"Publish date {project_publish_date.strftime('%Y-%m-%d')} is outside the plot range, not drawing line."
            )
    # --- End Vertical Line ---

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

    return fig  # Return the figure object
