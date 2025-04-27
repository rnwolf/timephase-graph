# Create a Matplotlib Gantt style chart for CCPM project task network

This project provides a Python script using Matplotlib to generate Gantt-style charts visualizing Critical Chain Project Management (CCPM) task networks based on data provided in a JSON file.

The JSON file describes a CCPM project task network (including tasks, dependencies, start/finish/remaining day offsets, types, and project info)

calendar_type: 'standard' (5 day work week) or 'continuous' (7 day work week)

`
{
    "project_info": {
      "start_date": "2025-04-22T21:02:45.466519",
      "calendar": "continuous",
      "hours_per_day": 8,
      "name": "Project ABC",
      "publish_date": "2025-01-01T10:00:00.000000"
    },
    "tasks": [
      {
        "id": 1,
        "name": "T1.1",
        "start": 0,
        "finish": 30,
        "type": "CRITICAL",
        "chain": "critical",
        "resources": "R",
        "predecessors": ""
      },
      {
        "id": 2,
        "name": "T1.2",
        "start": 30,
        "finish": 50,
        "type": "CRITICAL",
        "chain": "critical",
        "resources": "G",
        "predecessors": "1"
      },
}`


## Package Structure


pyganttccpm/
├── pyganttccpm/          # The actual package source code
│   ├── __init__.py
│   ├── config.py         # Enums, constants, colors
│   ├── loader.py         # Data loading and processing
│   ├── graph_utils.py    # Graph manipulation (add start/end)
│   └── plotter.py        # The main plotting function
├── examples/             # Optional: Example usage scripts
│   └── create_chart.py   # Examples of how to use the package
├── tests/                # Tests to make sure package works
│   └── ...
├── .env                  # Environment variable to indicate if reference files to be saved for required tests
├── .gitignore            # What files to ignore from version control
├── pyproject.toml        # Build system configuration
├── README.md             # Updated documentation
└── LICENSE               # Your chosen open-source license



## Development

You can then install your package locally for testing using `pip install -e .` in the root pyganttccpm/ directory (the one containing pyproject.toml). The -e makes it editable, so changes in your source files are reflected immediately.

## Usage

Run the example script (python examples/create_chart.py) to test.

## Publish

Eventually, you can build distribution files (python -m build) and publish to PyPI if desired.