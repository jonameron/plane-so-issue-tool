# Plane.so Issue Tool

## Overview
This tool automates the creation of modules and issues in Plane.so from a JSON-based work breakdown structure.

## Setup

1. Create and activate Python virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file with your Plane.so credentials:
```env
PLANE_API_KEY=your-api-key
PLANE_WORKSPACE_SLUG=your-workspace-slug
PLANE_PROJECT_ID=your-project-id
PLANE_HOST=https://api.plane.so
```

## Usage

1. Prepare your work breakdown structure in JSON format (see example in `docs/feature_mvp.md`)
2. Run the tool:
```bash
python main.py --input work_packages.json
```

Optional flags:
- `--dry-run`: Simulate the process without making API calls

## Project Structure
- `main.py`: Main application entry point
- `src/`: Source code directory
  - `api/`: API client implementation
  - `models/`: Data models
  - `utils/`: Utility functions
- `tests/`: Test directory
- `docs/`: Documentation
- `instructions/`: Project documentation and changelog 