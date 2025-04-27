# pyganttccpm/plotter.py
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import networkx as nx
from datetime import datetime, timedelta
import logging

# Import from other modules within the package
# Re-add START_NODE, END_NODE and add_global_start_end
from .config import TASK_COLORS, TaskType, START_NODE, END_NODE
from .graph_utils import add_global_start_end  # Re-add this import

log = logging.getLogger('pyganttccpm')

# Set UTC timezone preference within the module or rely on user setting it
# mpl.rcParams["timezone"] = "UTC" # Consider if this should be enforced or documented


# --- Unified Plotting Function with Optional START/END ---
def plot_project_gantt(
    project_start_date,
    tasks,
    dependencies,
    stream_map,
    calendar_type='standard',
    project_name='Project',
    project_publish_date=None,
    is_synthetic_start_date=False,
    add_start_end_nodes=True,  # <-- New parameter
):
    """
    Generates the Gantt chart plot.

    Optionally adds global START and END nodes to wrap the network based on
    the `add_start_end_nodes` parameter.

    Args:
        project_start_date (datetime): The official start date of the project.
        tasks (dict): Dictionary of task data.
        dependencies (list): List of dependency tuples [(u, v), ...].
        stream_map (dict): Dictionary mapping task names to stream/chain names.
        calendar_type (str): 'standard' or 'continuous'.
        project_name (str): Name of the project for the title.
        project_publish_date (datetime, optional): Date when the project data was published.
                                                   Used for title and optional vertical line. Defaults to None.
        is_synthetic_start_date (bool): Flag indicating if project_start_date was synthesized.
                                         If True, bottom date axis is hidden.
        add_start_end_nodes (bool): If True (default), add global START and END nodes
                                    to wrap the entire network graph. If False, plot the
                                    graph as provided.
    Returns:
        matplotlib.figure.Figure: The generated Matplotlib figure object.
    """
    if add_start_end_nodes:
        log.info('Generating Gantt plot with automatic START/END nodes...')
    else:
        log.info('Generating Gantt plot without automatic START/END nodes...')

    # 1 - Make copies to avoid modifying original data ---
    # Especially important if add_global_start_end modifies them in place
    tasks_copy = tasks.copy()
    dependencies_copy = list(dependencies)  # Create a shallow copy of the list
    stream_map_copy = stream_map.copy()
    # --- End copies ---

    # 2. Build Graph from potentially modified tasks and dependencies
    G = nx.DiGraph()
    # Add nodes first to ensure all tasks from the dict are included
    for task_name, data in tasks_copy.items():
        G.add_node(task_name, **data)
    # Add edges, which might add nodes if they weren't in tasks_copy (less likely now)
    G.add_edges_from(dependencies_copy)
    # Re-apply attributes just in case some nodes were added implicitly by edges
    # (though the first loop should prevent this)
    for task_name, data in tasks_copy.items():
        if task_name in G:
            G.nodes[task_name].update(data)
        else:
            # This case should be rare now but good to keep the warning
            log.warning(
                f"Task '{task_name}' defined in tasks dict but not present in graph nodes after processing dependencies."
            )

    # 2. Optionally add global START/END nodes
    if add_start_end_nodes:
        # This function might modify tasks_copy, dependencies_copy, stream_map_copy
        G, tasks_copy, stream_map_copy = add_global_start_end(
            G, tasks_copy, stream_map_copy
        )
        log.debug('Added global START and END nodes.')

    # --- Check if graph is empty ---
    if not G.nodes:
        log.warning('Graph is empty. Returning an empty figure.')
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.set_title(f'{project_name} - Timeline (No Tasks)')
        ax.text(
            0.5,
            0.5,
            'No tasks to display.',
            ha='center',
            va='center',
            transform=ax.transAxes,
        )
        return fig
    # --- End Empty Graph Check ---

    # 3. Layout Calculations
    # *** Ensure base is calculated from midnight ***
    project_start_midnight = datetime(
        project_start_date.year,
        project_start_date.month,
        project_start_date.day,
        0,
        0,
        0,
    )
    project_start_num_base = mdates.date2num(project_start_midnight)
    # *** End of base calculation adjustment ***

    # Use the potentially modified stream_map_copy
    unique_chains = sorted(list(set(stream_map_copy.values())))
    stream_levels = {chain: i for i, chain in enumerate(unique_chains)}
    y_levels = {}
    for task_name in G.nodes():
        # Use the potentially modified stream_map_copy
        chain = stream_map_copy.get(task_name)
        if chain is not None and chain in stream_levels:
            y_levels[task_name] = -stream_levels[chain]
        else:
            # Assign a default level if chain is missing or not in map
            log.warning(
                f"Warning: Task '{task_name}' missing chain or chain not found in stream_map. Assigning default y=0."
            )
            # Ensure task_name exists in y_levels even if chain is missing
            if task_name not in y_levels:
                y_levels[task_name] = 0  # Assign a default level

    # 4. Calculate Date Range for Plotting
    # Use the potentially modified tasks_copy
    all_starts = [
        data['start']
        for data in tasks_copy.values()
        if isinstance(data.get('start'), datetime)
    ]
    all_ends = [
        data['end']
        for data in tasks_copy.values()
        if isinstance(data.get('end'), datetime)
    ]

    if not all_starts and not all_ends:
        # Handle case with no valid dates at all
        min_date = project_start_date
        max_date = min_date + timedelta(days=7)  # Default range
        log.warning(
            'Warning: No valid start/end dates found in tasks. Using default date range based on project start.'
        )
    elif not all_starts:
        # Only end dates available
        min_date = min(all_ends) - timedelta(days=1)  # Estimate start
        max_date = max(all_ends)
    elif not all_ends:
        # Only start dates available
        min_date = min(all_starts)
        max_date = max(all_starts) + timedelta(days=1)  # Estimate end
    else:
        # Both available
        min_date = min(all_starts)
        max_date = max(all_ends)

    # Add buffer for plotting limits
    plot_start_date = min_date - timedelta(days=1)
    plot_limit_end_date = max_date + timedelta(days=1.5)
    plot_start_num = mdates.date2num(plot_start_date)
    plot_limit_end_num = mdates.date2num(plot_limit_end_date)

    # 5. --- PLOTTING ---
    fig, ax = plt.subplots(figsize=(16, 8))

    # --- Add Weekend Shading (if standard calendar) ---
    if calendar_type == 'standard':
        log.info('Applying weekend shading...')
        iter_start_date = datetime(
            plot_start_date.year, plot_start_date.month, plot_start_date.day
        )
        iter_end_limit = datetime(
            plot_limit_end_date.year, plot_limit_end_date.month, plot_limit_end_date.day
        ) + timedelta(days=1)

        current_date = iter_start_date
        while current_date < iter_end_limit:
            weekday = current_date.weekday()
            if weekday >= 5:  # Saturday (5) or Sunday (6)
                day_start_dt = datetime(
                    current_date.year, current_date.month, current_date.day, 0, 0, 0
                )
                day_end_dt = day_start_dt + timedelta(days=1)
                day_start_num = mdates.date2num(day_start_dt)
                day_end_num = mdates.date2num(day_end_dt)
                ax.axvspan(
                    day_start_num,
                    day_end_num,
                    facecolor='lightgray',
                    alpha=0.3,
                    zorder=-1,
                )
            current_date += timedelta(days=1)
    # --- End Weekend Shading ---

    # Plot Bars
    plotted_task_names = set()  # Keep track of tasks actually plotted
    # Iterate using the potentially modified tasks_copy
    for task_name, data in tasks_copy.items():
        # Ensure task exists in the graph and has a y-level before plotting
        if task_name not in G or task_name not in y_levels:
            log.debug(
                f"Skipping plot for task '{task_name}' as it's not in the graph or y_levels."
            )
            continue

        if isinstance(data.get('start'), datetime) and isinstance(
            data.get('end'), datetime
        ):
            start_num = mdates.date2num(data['start'])
            end_num = mdates.date2num(data['end'])
            y = y_levels[task_name]  # Use pre-calculated y_level
            task_type = data.get('type', TaskType.UNASSIGNED)
            color = TASK_COLORS.get(task_type, TASK_COLORS[TaskType.UNASSIGNED])
            task_url = data.get('url', None)

            total_duration_td = data.get('total_duration', timedelta(0))
            completed_duration_td = data.get('completed_duration', timedelta(0))
            has_remaining_data = data.get('has_remaining_data', False)
            task_tags = data.get('tags', [])

            # --- Special handling for START/END nodes (if added) ---
            if add_start_end_nodes and (
                task_name == START_NODE or task_name == END_NODE
            ):
                plotted_task_names.add(task_name)  # Mark as plotted
                # Plot START/END as markers (e.g., circles)
                marker = 'o'  # Circle marker
                marker_size = 8
                ax.plot(
                    start_num,  # Position at the start date
                    y,
                    marker,
                    markersize=marker_size,
                    color=color,  # Use SYSTEM color
                    markeredgecolor='black',
                    zorder=3,  # Ensure visible
                )
                # Add label slightly offset
                label_text = task_name  # Just START or END
                ha_align = 'right' if task_name == START_NODE else 'left'
                offset = -0.05 if task_name == START_NODE else 0.05
                ax.text(
                    start_num + offset,
                    y,
                    label_text,
                    va='center',
                    ha=ha_align,
                    fontsize=9,
                    fontweight='bold',
                    color='black',
                    zorder=4,
                )
            # --- Regular Task Plotting (Bars or Milestones) ---
            elif total_duration_td > timedelta(0):  # Regular task with duration
                plotted_task_names.add(task_name)  # Mark as plotted
                main_bar_height = 0.5
                bar_total = ax.barh(
                    y,
                    total_duration_td.total_seconds() / (24 * 3600),
                    left=start_num,
                    height=main_bar_height,
                    color=color,
                    edgecolor='k',
                    alpha=0.5,
                    zorder=2,
                )
                if task_url:
                    bar_total[0].set_url(task_url)

                # Draw Progress Bar
                if has_remaining_data and completed_duration_td > timedelta(0):
                    completed_width_days = completed_duration_td.total_seconds() / (
                        24 * 3600
                    )
                    progress_bar_height = 0.1
                    y_progress = (y - main_bar_height / 2) + (progress_bar_height / 2)
                    ax.barh(
                        y_progress,
                        completed_width_days,
                        left=start_num,
                        height=progress_bar_height,
                        color=color,
                        edgecolor=None,
                        alpha=1.0,
                        zorder=3,
                    )

                # Text Label
                task_id = data.get('id', '?')
                resources = data.get('resources', '')
                label_text = f'{task_id} {task_name}'
                if resources:
                    label_text += f' ({resources})'
                text_label = ax.text(
                    start_num + (total_duration_td.total_seconds() / (24 * 3600)) / 2,
                    y,
                    label_text,
                    va='center',
                    ha='center',
                    fontsize=8,
                    color='black',
                    zorder=4,
                )
                if task_url:
                    text_label.set_url(task_url)

                # Add Tags Text
                if task_tags:
                    tags_str = ' '.join([f'#{tag}' for tag in task_tags])
                    ax.text(
                        end_num,
                        y,
                        tags_str,
                        ha='right',
                        va='center',
                        fontsize=6,
                        color='white',
                        zorder=5,
                        bbox=dict(
                            facecolor='black',
                            alpha=0.4,
                            pad=1,
                            boxstyle='round,pad=0.1',
                        ),
                    )
            elif total_duration_td <= timedelta(0):  # Zero Duration Task (Milestone)
                plotted_task_names.add(task_name)  # Mark as plotted
                ax.plot(
                    start_num,  # Position at the start date
                    y,
                    'D',  # Diamond marker
                    markersize=6,
                    color=color,
                    markeredgecolor='black',
                    zorder=3,  # Ensure visible
                )
                # Add label slightly offset from marker
                task_id = data.get('id', '?')
                label_text = f'{task_id} {task_name}'
                ax.text(
                    start_num,
                    y,
                    f' {label_text}',  # Add space for offset
                    va='center',
                    ha='left',  # Align left of the marker point
                    fontsize=8,
                    color='black',
                    zorder=4,
                )
            # --- End Regular Task Plotting ---

        else:
            # Log warning only if it's not one of the potentially added START/END nodes
            # (as they might have valid dates but we handle them separately above)
            is_start_end = add_start_end_nodes and (
                task_name == START_NODE or task_name == END_NODE
            )
            if not is_start_end:
                log.warning(
                    f"Skipping task '{task_name}' due to missing or invalid start/end dates."
                )

    # Draw Dependency Arrows
    arrowprops = dict(
        arrowstyle='->', color='gray', lw=1, connectionstyle='arc3,rad=0.1'
    )
    for u, v in G.edges():
        # Check if edge source/target were actually plotted and have y_levels
        if (
            u not in plotted_task_names
            or v not in plotted_task_names
            or u not in y_levels
            or v not in y_levels
        ):
            log.debug(
                f'Skipping arrow for edge {u}->{v} as one or both tasks were not plotted or lack y-level.'
            )
            continue

        # Ensure tasks exist in the main tasks dictionary to get date info
        # Use tasks_copy here as it contains START/END if they were added
        if u not in tasks_copy or v not in tasks_copy:
            log.warning(
                f"Skipping arrow for edge {u}->{v} due to missing task data in the 'tasks_copy' dictionary."
            )
            continue

        data_u = tasks_copy[u]
        data_v = tasks_copy[v]
        y_level_u = y_levels[u]
        y_level_v = y_levels[v]

        # Check for valid dates before calculating arrow positions
        if isinstance(data_u.get('end'), datetime) and isinstance(
            data_v.get('start'), datetime
        ):
            # Determine start point x-coordinate
            # Use 'start' date for zero-duration tasks (milestones, START/END)
            is_u_zero_dur = data_u.get('total_duration', timedelta(1)) <= timedelta(0)
            is_u_start_node = add_start_end_nodes and u == START_NODE
            x_start_date = (
                data_u['start'] if (is_u_zero_dur or is_u_start_node) else data_u['end']
            )
            x_start = mdates.date2num(x_start_date)

            # Determine end point x-coordinate (always 'start' of the successor)
            x_end = mdates.date2num(data_v['start'])

            y_start = y_level_u
            y_end = y_level_v

            # Avoid drawing zero-length arrows if start/end points are identical
            # Use a small tolerance for floating point comparisons
            if abs(x_start - x_end) > 1e-6 or abs(y_start - y_end) > 1e-6:
                ax.annotate(
                    '',
                    xy=(x_end, y_end),
                    xytext=(x_start, y_start),
                    arrowprops=arrowprops,
                    zorder=1,  # Draw arrows behind bars/markers
                )
        else:
            log.warning(
                f'Warning: Missing valid start/end dates for dependency {u}->{v}. Skipping arrow.'
            )

    # 6. Configure Axes
    ax.set_xlim(plot_start_num, plot_limit_end_num)

    # --- Configure Bottom X-axis (Dates) ---
    if is_synthetic_start_date:
        log.info('Hiding bottom date axis due to synthetic start date.')
        ax.xaxis.set_major_locator(mticker.NullLocator())
        ax.xaxis.set_major_formatter(mticker.NullFormatter())
        ax.set_xlabel('')
    else:
        locator = mdates.AutoDateLocator(minticks=5, maxticks=10)
        formatter = mdates.ConciseDateFormatter(locator)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        ax.set_xlabel('Date')

    # --- Construct and Set Title ---
    title_str = f'{project_name} - Timeline'
    if project_publish_date and not is_synthetic_start_date:
        title_str += f" (Data as of: {project_publish_date.strftime('%Y-%m-%d %H:%M')})"
    ax.set_title(title_str)
    # --- End Title ---

    ax.invert_yaxis()
    ax.grid(True, axis='x', linestyle='--', alpha=0.6)

    # --- Configure Y-axis Ticks ---
    # Filter y_levels to only include tasks that were actually plotted
    plotted_y_levels = {
        task: y for task, y in y_levels.items() if task in plotted_task_names
    }
    if plotted_y_levels:
        unique_plotted_y_values = sorted(list(set(plotted_y_levels.values())))
        ax.set_yticks(unique_plotted_y_values)
        # Use the potentially modified stream_map_copy for labels
        level_to_chain = {lvl: chain for chain, lvl in stream_levels.items()}
        y_tick_labels = [
            level_to_chain.get(-y, f'Level {-y}')  # Get chain name from level
            for y in unique_plotted_y_values
        ]
        ax.set_yticklabels(y_tick_labels)
    else:
        ax.set_yticks([])  # No ticks if nothing was plotted
        ax.set_yticklabels([])
    ax.set_ylabel('Task Chain')
    # --- End Y-axis Ticks ---

    fig.autofmt_xdate(rotation=30, ha='right')

    # --- Add Vertical Line for Publish Date ---
    if project_publish_date and not is_synthetic_start_date:
        publish_date_num = mdates.date2num(project_publish_date)
        if plot_start_num < publish_date_num < plot_limit_end_num:
            ax.axvline(
                x=publish_date_num,
                color='blue',
                linestyle='--',
                linewidth=1.5,
                label=f"Publish Date ({project_publish_date.strftime('%Y-%m-%d')})",
                zorder=10,
            )
            log.info(
                f"Adding vertical line for publish date: {project_publish_date.strftime('%Y-%m-%d')}"
            )
        else:
            log.warning(
                f"Publish date {project_publish_date.strftime('%Y-%m-%d')} is outside the plot range, not drawing line."
            )
    # --- End Vertical Line ---

    # --- Configure Top X-axis (Day Index) ---
    ax2 = ax.twiny()
    lim_min_num, lim_max_num = ax.get_xlim()
    ax2.set_xlim(lim_min_num, lim_max_num)

    bottom_locator = ax.xaxis.get_major_locator()
    if isinstance(bottom_locator, mticker.NullLocator):
        # Use a sensible default locator if bottom is hidden
        days_span = (plot_limit_end_date - plot_start_date).days
        if days_span > 90:  # Example threshold
            interval = 7 * (days_span // 180 + 1)  # Rough scaling for interval
            top_locator = mdates.WeekdayLocator(interval=interval)
        elif days_span > 30:
            top_locator = mdates.WeekdayLocator(interval=1)  # Weekly ticks
        else:
            top_locator = mdates.DayLocator(interval=1)  # Daily ticks
        ax2.xaxis.set_major_locator(top_locator)
    else:
        ax2.xaxis.set_major_locator(bottom_locator)  # Link if bottom has locator

    def day_index_formatter(tick_val, pos):
        day_index_float = tick_val - project_start_num_base
        day_index_int = round(day_index_float)
        return f'{day_index_int}'

    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(day_index_formatter))
    ax2.set_xlabel('Day Index')

    def update_ax2_limits(ax_bottom):
        ax2.set_xlim(ax_bottom.get_xlim())

    ax.callbacks.connect('xlim_changed', update_ax2_limits)
    # --- End Top X-axis ---

    # 7. Add Legend
    handles, labels = (
        ax.get_legend_handles_labels()
    )  # Get handles from axvline if present
    type_legend_handles = []
    # Determine used types from the *actually plotted* tasks in tasks_copy
    used_types = set(
        tasks_copy[task_name]['type']
        for task_name in plotted_task_names
        if task_name in tasks_copy and 'type' in tasks_copy[task_name]
    )
    for task_type in TaskType:
        # Only add legend entry if the type was actually used
        # If START/END nodes were not added, SYSTEM type won't be in used_types
        if task_type in used_types:
            # Special label for SYSTEM type if it was used (meaning START/END were added)
            if task_type == TaskType.SYSTEM and add_start_end_nodes:
                label = 'Start/End Node'
            else:
                label = task_type.name.replace('_', ' ').title()

            color = TASK_COLORS[task_type]
            type_legend_handles.append(mpatches.Patch(color=color, label=label))

    all_handles = type_legend_handles + handles
    if all_handles:
        ax.legend(
            handles=all_handles,
            title='Legend',
            bbox_to_anchor=(1.04, 0.5),
            loc='center left',
            borderaxespad=0.0,
        )
        plt.subplots_adjust(right=0.85)  # Adjust plot to make space for legend

    log.info('Gantt plot generation complete.')

    return fig
