# ARC Reasoning Labeler

A Flask-based web application for labeling the correctness of reasoning steps in ARC puzzle solutions. This tool allows human annotators to review puzzle-solving steps and label them as correct, incorrect, or skipped.

## Features

- **Visual Puzzle Display**: View training and test examples with side-by-side input/output grids
- **Step-by-Step Review**: Examine generated reasoning steps with detailed instructions
- **Interactive Labeling**: Large, easy-to-click buttons for labeling (✓ Correct, ✗ Incorrect, ⏭ Skip)
- **Failure Mode Tracking**: Select specific failure modes (A1-A3, B1-B2, C1-C3) for incorrect reasoning
- **Progress Tracking**: Real-time statistics showing labeling progress
- **Duplicate Version Navigation**: Handle multiple analysis files for the same puzzle
- **Auto-save**: Labels are automatically saved to JSON files

## Documentation

- **[README.md](README.md)** - This file: Setup and usage instructions
- **[FAILURE_MODE_GUIDE.md](FAILURE_MODE_GUIDE.md)** - **Detailed guide on identifying failure modes** - Read this before labeling!
- **[SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md)** - Quick setup guide for second annotator

## Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone or download this repository**

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   
   **Windows (PowerShell):**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   
   **Windows (Command Prompt):**
   ```cmd
   venv\Scripts\activate.bat
   ```
   
   **Linux/Mac:**
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Directory Structure

```
reasoning_labeler_repo/
├── app.py                          # Main Flask application
├── arc_visualizer.py               # Grid visualization utilities
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── templates/
│   └── reasoning_labeler.html      # Web interface template
├── traces/                         # Puzzle analysis files directory
│   └── (your puzzle JSON files go here)
└── labels/                         # Label storage directory (auto-created)
    └── .reasoning_labels.json      # Labels file (auto-created)
```

## Usage

### 1. Prepare Your Puzzle Files

Place your puzzle analysis JSON files in the `traces/` directory. The app looks for files matching these patterns:
- `*_v11_analysis*.json`
- `*_v10_analysis*.json`
- `*_analysis.json`

**Expected JSON structure:**
```json
{
  "puzzle_id": "abc123",
  "general_steps": [...],
  "training_examples": [...],
  "test_examples": [...],
  "training_booklets": [...],
  "test_booklets": [...],
  "summary": {
    "training_accuracy": 1.0,
    "test_accuracy": 0.0,
    "num_general_steps": 5
  }
}
```

### 2. Run the Application

**Windows:**
```bash
python app.py
```

**Linux/Mac:**
```bash
python3 app.py
```

The app will start on `http://localhost:5001`

### 3. Open in Browser

Navigate to `http://localhost:5001` in your web browser.

## How to Label Puzzles

1. **Select a Puzzle**: Click on a puzzle from the left sidebar, or the app will automatically load the next unlabeled puzzle.

2. **Review the Puzzle**:
   - View training examples (input → expected output → prediction)
   - View test examples (input → expected output → generated output)
   - Read through the generated reasoning steps

3. **Label the Puzzle**:
   - Click **✓** (green checkmark) if the reasoning is correct
   - Click **✗** (red X) if the reasoning is incorrect
   - Click **⏭ Skip** if there's not enough information to make a judgment

4. **Select Failure Modes** (for incorrect reasoning):
   - **Category A**: Accuracy failures (A1: Complete failure, A2: Partial failure, A3: Training failure)
   - **Category B**: Step count issues (B1: Too many steps, B2: Too few steps)
   - **Category C**: Visual fidelity issues (C1: Grid mismatch, C2: Bbox misalignment, C3: Description mismatch)
   - You can select multiple failure modes
   - **See [FAILURE_MODE_GUIDE.md](FAILURE_MODE_GUIDE.md) for detailed explanations and examples**

5. **Add Notes** (optional): Enter reasoning notes in the text area

6. **Submit**: Click "Submit & Move to Next Puzzle" to save and move to the next unlabeled puzzle

## Label Storage

Labels are saved to `labels/.reasoning_labels.json` in the following format:

```json
{
  "puzzle_id": {
    "label": "correct" | "incorrect" | "skipped",
    "reasoning": "Optional notes...",
    "failure_modes": ["B1", "C2"],
    "file_path": "path/to/file.json",
    "timestamp": "2024-01-15T10:30:00",
    "reviewer": "human",
    "edited": false
  }
}
```

## Sending Labels to Another Annotator

After completing your labeling session:

1. **Copy the labels file:**
   ```bash
   # The labels file is at:
   labels/.reasoning_labels.json
   ```

2. **Send the labels file** to the other annotator (via email, shared drive, etc.)

3. **The other annotator should:**
   - Place the labels file in their `labels/` directory
   - Run the app and continue labeling
   - Labels will merge automatically (existing labels won't be overwritten unless edited)

## Statistics

The stats bar at the top shows:
- **Total Puzzles**: All puzzles found in traces directory
- **Labeled**: Number of puzzles with labels
- **Correct**: Number labeled as correct
- **Incorrect**: Number labeled as incorrect
- **Skipped**: Number skipped
- **Completion**: Percentage of puzzles labeled

## Troubleshooting

### Port Already in Use

If port 5001 is already in use, edit `app.py` and change:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```
to a different port (e.g., `port=5002`)

### No Puzzles Found

- Check that puzzle JSON files are in the `traces/` directory
- Ensure files match the expected naming pattern (`*_analysis.json`)
- Verify JSON files contain `general_steps` field

### Labels Not Saving

- Check that the `labels/` directory exists and is writable
- Check file permissions
- Look for error messages in the terminal

### Cache Issues

If puzzles aren't showing up after adding new files:
- Delete `traces/.puzzle_metadata_cache.json` to force a cache rebuild
- Restart the application

## API Endpoints

- `GET /` - Main labeling interface
- `GET /api/puzzles` - List all puzzles with labels
- `GET /api/puzzles/unlabeled` - Get unlabeled puzzles (paginated)
- `GET /api/puzzle/<file_path>` - Get puzzle data
- `POST /api/label` - Save/update label
- `DELETE /api/label/<puzzle_id>` - Delete label
- `GET /api/stats` - Get labeling statistics

## Keyboard Shortcuts

- Use the sidebar to navigate between puzzles
- Click puzzle items to load them
- Use the large buttons (✓, ✗, ⏭) for quick labeling

## Notes for Second Annotator

1. **Before starting:**
   - **📖 Read [FAILURE_MODE_GUIDE.md](FAILURE_MODE_GUIDE.md) first!** This explains how to identify each failure mode with examples
   - Make sure you have the latest puzzle files in `traces/`
   - If you received labels from another annotator, place `reasoning_labels.json` in the `labels/` directory

2. **During labeling:**
   - The app will automatically load unlabeled puzzles
   - You can see which puzzles are already labeled in the sidebar
   - Labels are saved automatically when you click the label buttons
   - **Keep [FAILURE_MODE_GUIDE.md](FAILURE_MODE_GUIDE.md) open** as a reference when selecting failure modes

3. **After completing:**
   - Send the `labels/.reasoning_labels.json` file back
   - Include any notes about edge cases or questions

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the error messages in the terminal
3. Ensure all dependencies are installed correctly

## License

This tool is provided as-is for ARC puzzle reasoning analysis.

