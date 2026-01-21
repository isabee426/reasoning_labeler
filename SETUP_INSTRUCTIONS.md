# Setup Instructions for Second Annotator

## Quick Start

1. **Download/Clone this repository**

2. **Run the setup script:**
   
   **Windows:**
   ```bash
   start_app.bat
   ```
   
   **Linux/Mac:**
   ```bash
   chmod +x start_app.sh
   ./start_app.sh
   ```

3. **Place puzzle files:**
   - Put your puzzle analysis JSON files in the `traces/` directory
   - Files should match pattern: `*_analysis.json` or `*_v11_analysis.json`

4. **If you received labels from another annotator:**
   - Copy the `reasoning_labels.json` file to `labels/.reasoning_labels.json`
   - Your labels will merge with existing ones

5. **Open browser:**
   - Navigate to `http://localhost:5001`
   - Start labeling!

## Manual Setup (if scripts don't work)

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate virtual environment:**
   
   Windows:
   ```bash
   venv\Scripts\activate
   ```
   
   Linux/Mac:
   ```bash
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**
   ```bash
   python app.py
   ```

## Directory Structure

```
reasoning_labeler_repo/
├── app.py                    # Main application
├── arc_visualizer.py         # Visualization utilities
├── requirements.txt          # Dependencies
├── README.md                 # Full documentation
├── templates/                # Web interface
│   └── reasoning_labeler.html
├── traces/                   # PUT YOUR PUZZLE FILES HERE
│   └── (puzzle JSON files)
└── labels/                   # Labels storage (auto-created)
    └── .reasoning_labels.json
```

## Sending Labels Back

After completing your labeling session:

1. **Find the labels file:**
   - Location: `labels/.reasoning_labels.json`

2. **Send this file** to the main annotator

3. **The file contains all your labels** in JSON format

## Troubleshooting

- **Port 5001 in use?** Edit `app.py` and change `port=5001` to a different port
- **No puzzles showing?** Check that files are in `traces/` and match `*_analysis.json` pattern
- **Import errors?** Make sure you activated the virtual environment and installed requirements

