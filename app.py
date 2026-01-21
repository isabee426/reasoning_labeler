#!/usr/bin/env python3
"""
Enhanced Flask App for Labeling Reasoning Correctness in V11/V10 Results
Allows human reviewers to label whether generated steps are faithful to puzzle tricks
Shows training/test examples visually and allows editing labels
"""

from flask import Flask, render_template, jsonify, request
from pathlib import Path
import json
import sys
from datetime import datetime
from functools import lru_cache
import time

# Import local arc_visualizer (standalone version)
from arc_visualizer import grid_to_image, ARC_COLORS
from PIL import Image
import base64
from io import BytesIO

# Set template folder (relative to app directory)
current_file = Path(__file__).resolve()
app_dir = current_file.parent
template_dir = app_dir / 'templates'

app = Flask(__name__, template_folder=str(template_dir))

# Paths (relative to app directory)
traces_dir = app_dir / "traces"
labels_dir = app_dir / "labels"
labels_dir.mkdir(exist_ok=True)  # Create labels directory if it doesn't exist
labels_file = labels_dir / ".reasoning_labels.json"
cache_file = traces_dir / ".puzzle_metadata_cache.json"

# Cache for puzzle metadata
_puzzle_cache = None
_cache_timestamp = 0
_cache_ttl = 300  # Cache for 5 minutes (much longer since we're only loading one at a time)

def grid_to_base64(grid, cell_size=40):
    """Convert grid to base64 image"""
    img = grid_to_image(grid, cell_size=cell_size)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def load_labels():
    """Load reasoning labels from file"""
    if labels_file.exists():
        try:
            with open(labels_file, 'r') as f:
                data = json.load(f)
                return data
        except:
            return {}
    return {}

def save_labels(labels):
    """Save reasoning labels to file"""
    labels_file.parent.mkdir(parents=True, exist_ok=True)
    with open(labels_file, 'w') as f:
        json.dump(labels, f, indent=2)

def get_analysis_files():
    """Get all v11 and v10 analysis files from traces directory"""
    files = []
    if traces_dir.exists():
        files.extend(traces_dir.rglob("*_v11_analysis*.json"))
        files.extend(traces_dir.rglob("*_v10_analysis*.json"))
        if not files:
            files.extend(traces_dir.rglob("*_analysis.json"))
    files = sorted(set(files), key=lambda x: x.stat().st_mtime, reverse=True)
    return files

def get_puzzle_metadata_cache():
    """Get cached puzzle metadata, reloading if cache is stale
    Uses persistent disk cache to avoid re-reading all files"""
    global _puzzle_cache, _cache_timestamp
    
    current_time = time.time()
    # Check if in-memory cache is still valid
    if _puzzle_cache is not None and (current_time - _cache_timestamp) < _cache_ttl:
        return _puzzle_cache
    
    # Try to load from disk cache first
    if cache_file.exists():
        try:
            cache_mtime = cache_file.stat().st_mtime
            # Use disk cache if it's less than 1 hour old
            if (current_time - cache_mtime) < 3600:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    # Convert file paths back to Path objects
                    puzzle_files = {}
                    if cached_data:  # Only process if cache has data
                        for puzzle_id, file_list in cached_data.items():
                            puzzle_files[puzzle_id] = []
                            for file_data in file_list:
                                file_path = traces_dir / file_data['rel_path']
                                if file_path.exists():
                                    # Check if file was modified since cache
                                    if file_path.stat().st_mtime <= cache_mtime:
                                        puzzle_files[puzzle_id].append({
                                            'file': file_path,
                                            'rel_path': Path(file_data['rel_path']),
                                            'mtime': file_data['mtime'],
                                            'training_accuracy': file_data['training_accuracy'],
                                            'is_v11': file_data['is_v11']
                                        })
                    
                    # Only return cache if it has puzzles
                    if puzzle_files:
                        _puzzle_cache = puzzle_files
                        _cache_timestamp = current_time
                        return puzzle_files
                    else:
                        # Cache is empty, rebuild it
                        print("[INFO] Cache is empty, rebuilding...")
        except Exception:
            # If cache is corrupted, rebuild
            pass
    
    # Rebuild cache - OPTIMIZED: Only read files that might have general_steps
    print("[INFO] Building puzzle metadata cache (this may take a moment)...")
    files = get_analysis_files()
    print(f"[INFO] Found {len(files)} analysis files to process")
    puzzle_files = {}  # puzzle_id -> list of file metadata
    skipped_no_general_steps = 0
    skipped_empty = 0
    skipped_errors = 0
    
    for f in files:
        try:
            # Extract puzzle ID from filename first (no file reading needed)
            name = f.stem
            if "_v11_analysis" in name:
                puzzle_id = name.replace("_v11_analysis", "")
            elif "_v10_analysis" in name:
                puzzle_id = name.replace("_v10_analysis", "")
            else:
                puzzle_id = name.replace("_analysis", "")
            
            # Get basic metadata without reading file
            rel_path = f.relative_to(traces_dir)
            mtime = f.stat().st_mtime
            is_v11 = '_v11' in str(f)
            
            # Read file to check for general_steps and get training_accuracy
            # Note: We parse the full JSON since general_steps might be anywhere in the file
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    
                    # Check for general_steps
                    general_steps = data.get('general_steps', [])
                    if not general_steps or len(general_steps) == 0:
                        skipped_empty += 1
                        continue
                    
                    summary = data.get('summary', {})
                    training_accuracy = summary.get('training_accuracy', 0.0) if summary else 0.0
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                # Skip corrupted files
                skipped_errors += 1
                if skipped_errors <= 5:  # Only log first few errors
                    print(f"[WARNING] JSON error in {f.name}: {e}")
                continue
            except Exception as e:
                skipped_errors += 1
                if skipped_errors <= 5:
                    print(f"[WARNING] Error reading {f.name}: {e}")
                continue
            
            if puzzle_id not in puzzle_files:
                puzzle_files[puzzle_id] = []
            
            puzzle_files[puzzle_id].append({
                'file': f,
                'rel_path': rel_path,
                'mtime': mtime,
                'training_accuracy': training_accuracy,
                'is_v11': is_v11
            })
        except Exception as e:
            # Skip files that can't be processed
            skipped_errors += 1
            print(f"[WARNING] Error processing {f.name}: {e}")
            continue
    
    print(f"[INFO] Processed {len(files)} files: {len(puzzle_files)} puzzles found, {skipped_no_general_steps} skipped (no general_steps), {skipped_empty} skipped (empty), {skipped_errors} skipped (errors)")
    
    # Save to disk cache
    try:
        cache_data = {}
        for puzzle_id, file_list in puzzle_files.items():
            cache_data[puzzle_id] = []
            for file_data in file_list:
                cache_data[puzzle_id].append({
                    'rel_path': str(file_data['rel_path']),
                    'mtime': file_data['mtime'],
                    'training_accuracy': file_data['training_accuracy'],
                    'is_v11': file_data['is_v11']
                })
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        print(f"[INFO] Cache saved with {len(puzzle_files)} puzzles")
    except Exception as e:
        print(f"[WARNING] Failed to save cache: {e}")
    
    _puzzle_cache = puzzle_files
    _cache_timestamp = current_time
    return puzzle_files

def invalidate_cache():
    """Invalidate the puzzle metadata cache (both memory and disk)"""
    global _puzzle_cache, _cache_timestamp
    _puzzle_cache = None
    _cache_timestamp = 0
    # Delete disk cache so it rebuilds
    if cache_file.exists():
        try:
            cache_file.unlink()
        except Exception:
            pass

@app.route('/')
def index():
    """Main labeling interface"""
    return render_template('reasoning_labeler.html')

@app.route('/api/puzzles/unlabeled')
def get_unlabeled_puzzles():
    """Get unlabeled puzzles in batches"""
    from flask import request
    limit = int(request.args.get('limit', 5))
    offset = int(request.args.get('offset', 0))
    
    puzzle_files = get_puzzle_metadata_cache()
    labels = load_labels()
    
    # Get all puzzles first
    all_puzzles = []
    for puzzle_id, file_options in puzzle_files.items():
        label_info = labels.get(puzzle_id, {})
        has_label = label_info.get('label') is not None
        
        for opt in file_options:
            opt['has_label'] = has_label
            opt['label_info'] = label_info
        
        file_options.sort(key=lambda x: (
            not x['has_label'],
            -x['training_accuracy'],
            -x['mtime'],
            not x['is_v11']
        ))
        
        selected = file_options[0]
        num_duplicates = len(file_options) - 1
        
        all_puzzles.append({
            'puzzle_id': puzzle_id,
            'file_path': str(selected['rel_path']).replace('\\', '/'),
            'label': selected['label_info'].get('label', None),
            'reasoning': selected['label_info'].get('reasoning', ''),
            'timestamp': selected['label_info'].get('timestamp', ''),
            'auto_detected': selected['label_info'].get('auto_detected', False),
            'reviewer': selected['label_info'].get('reviewer', 'human'),
            'num_duplicates': num_duplicates
        })
    
    # Filter to unlabeled only (exclude skipped from unlabeled list)
    unlabeled = [p for p in all_puzzles if not p['label']]
    unlabeled.sort(key=lambda x: x['puzzle_id'])
    
    # Apply pagination
    total = len(unlabeled)
    paginated = unlabeled[offset:offset + limit]
    
    return jsonify({
        'puzzles': paginated,
        'total': total,
        'offset': offset,
        'limit': limit,
        'has_more': offset + limit < total
    })

@app.route('/api/puzzles')
def get_puzzles():
    """Get list of all puzzles with their labels (excluding puzzles without general steps)
    Deduplicates: shows only one file per puzzle_id, preferring labeled or more recent files"""
    puzzle_files = get_puzzle_metadata_cache()
    labels = load_labels()
    
    # For each puzzle_id, select the best file:
    # 1. Prefer files that have labels
    # 2. Prefer files with higher training accuracy
    # 3. Prefer more recent files
    # 4. Prefer v11 over v10
    puzzle_list = []
    for puzzle_id, file_options in puzzle_files.items():
        # Get label info for this puzzle
        label_info = labels.get(puzzle_id, {})
        has_label = label_info.get('label') is not None
        
        # Add has_label to each option for sorting
        for opt in file_options:
            opt['has_label'] = has_label
            opt['label_info'] = label_info
        
        # Sort: labeled first, then by training accuracy (higher first), then by mtime (newest first), then v11 before v10
        file_options.sort(key=lambda x: (
            not x['has_label'],  # False (has label) comes before True (no label)
            -x['training_accuracy'],  # Higher training accuracy first
            -x['mtime'],  # Newer files first
            not x['is_v11']  # v11 before v10
        ))
        
        selected = file_options[0]
        num_duplicates = len(file_options) - 1
        
        puzzle_list.append({
            'puzzle_id': puzzle_id,
            'file_path': str(selected['rel_path']).replace('\\', '/'),
            'label': selected['label_info'].get('label', None),
            'reasoning': selected['label_info'].get('reasoning', ''),
            'timestamp': selected['label_info'].get('timestamp', ''),
            'auto_detected': selected['label_info'].get('auto_detected', False),
            'reviewer': selected['label_info'].get('reviewer', 'human'),
            'num_duplicates': num_duplicates  # Show how many other files exist
        })
    
    # Sort puzzle list by puzzle_id for consistent ordering
    puzzle_list.sort(key=lambda x: x['puzzle_id'])
    
    return jsonify(puzzle_list)

@app.route('/api/puzzle/<path:file_path>')
def get_puzzle(file_path):
    """Load puzzle data with enhanced information"""
    try:
        file_path = file_path.replace('\\', '/')
        full_path = traces_dir / file_path
        
        if not full_path.exists():
            return jsonify({'error': f'File not found: {file_path}'}), 404
        
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract puzzle ID
        puzzle_id = data.get('puzzle_id', '')
        
        # Get all duplicate versions of this puzzle
        puzzle_files = get_puzzle_metadata_cache()
        duplicate_versions = []
        if puzzle_id in puzzle_files:
            for file_data in puzzle_files[puzzle_id]:
                rel_path = str(file_data['rel_path']).replace('\\', '/')
                duplicate_versions.append({
                    'file_path': rel_path,
                    'training_accuracy': file_data.get('training_accuracy', 0),
                    'is_v11': file_data.get('is_v11', False),
                    'mtime': file_data.get('mtime', 0)
                })
            # Sort duplicates: labeled first, then by training accuracy, then by mtime, then v11 before v10
            labels = load_labels()
            label_info = labels.get(puzzle_id, {})
            has_label = label_info.get('label') is not None
            duplicate_versions.sort(key=lambda x: (
                not has_label,  # Labeled first
                -x['training_accuracy'],
                -x['mtime'],
                not x['is_v11']
            ))
        
        # Find current index in duplicates
        current_index = -1
        for i, dup in enumerate(duplicate_versions):
            if dup['file_path'] == file_path:
                current_index = i
                break
        
        # Convert grids to base64 images
        puzzle_data = {
            'puzzle_id': puzzle_id,
            'file_path': file_path,
            'analysis': data.get('analysis', {}),
            'general_steps': data.get('general_steps', []),
            'summary': data.get('summary', {}),
            'training_examples': [],
            'test_examples': [],
            'training_booklets': [],
            'test_booklets': []
        }
        
        # Process training examples from analysis
        train_examples = data.get('analysis', {}).get('train_examples', [])
        training_booklets = data.get('training_booklets', [])
        
        for i, ex in enumerate(train_examples):
            # Get prediction from training booklet if available
            prediction_image = None
            prediction_grid = None
            if i < len(training_booklets):
                booklet = training_booklets[i]
                if booklet.get('steps'):
                    final_step = booklet['steps'][-1]
                    final_grid = final_step.get('grid_after') or final_step.get('grid')
                    if final_grid:
                        prediction_grid = final_grid
                        prediction_image = grid_to_base64(final_grid, cell_size=50)
            
            puzzle_data['training_examples'].append({
                'index': i,
                'input': ex.get('input', []),
                'output': ex.get('output', []),
                'input_image': grid_to_base64(ex.get('input', []), cell_size=50),
                'output_image': grid_to_base64(ex.get('output', []), cell_size=50),
                'prediction_image': prediction_image,
                'prediction_grid': prediction_grid
            })
        
        # Process test booklets first to extract test examples
        test_booklets_raw = data.get('test_booklets', [])
        
        # Extract test examples from test_booklets (they contain input/output)
        for i, booklet in enumerate(test_booklets_raw):
            test_input = booklet.get('input') or booklet.get('current_grid')
            test_output = booklet.get('output') or booklet.get('expected_grid')
            predicted_output = booklet.get('predicted_grid') or booklet.get('final_grid')
            
            if test_input:  # Only add if input exists
                puzzle_data['test_examples'].append({
                    'index': i,
                    'input': test_input,
                    'output': test_output,
                    'predicted_output': predicted_output,
                    'input_image': grid_to_base64(test_input, cell_size=50),
                    'output_image': grid_to_base64(test_output, cell_size=50) if test_output else None,
                    'predicted_image': grid_to_base64(predicted_output, cell_size=50) if predicted_output else None
                })
        
        # Also check for test_examples in analysis (fallback)
        if not puzzle_data['test_examples']:
            test_examples = data.get('analysis', {}).get('test_examples', [])
            if not test_examples:
                test_examples = data.get('test_examples', [])
            
            for i, ex in enumerate(test_examples):
                if ex.get('input'):  # Only add if input exists
                    puzzle_data['test_examples'].append({
                        'index': i,
                        'input': ex.get('input', []),
                        'output': ex.get('output', []),
                        'input_image': grid_to_base64(ex.get('input', []), cell_size=50),
                        'output_image': grid_to_base64(ex.get('output', []), cell_size=50) if ex.get('output') else None
                    })
        
        # Process training booklets (for detailed step visualization)
        training_booklets = data.get('training_booklets', [])
        for i, booklet in enumerate(training_booklets):
            final_grid = None
            steps_data = []
            if booklet.get('steps'):
                for step in booklet.get('steps', []):
                    grid_before = step.get('grid_before') or step.get('grid')
                    grid_after = step.get('grid_after') or step.get('grid')
                    visual_count = sum([
                        1 if grid_before else 0,
                        1 if grid_after else 0,
                        1 if step.get('grid') else 0
                    ])
                    steps_data.append({
                        'step_number': step.get('step_number', ''),
                        'general_step': step.get('general_step', ''),
                        'object_substep': step.get('object_substep', ''),
                        'instruction': step.get('instruction', ''),
                        'substep_reasoning': step.get('substep_reasoning', ''),
                        'tool_used': step.get('tool_used', ''),
                        'tool_params': step.get('tool_params', {}),
                        'bbox': step.get('bbox', None),
                        'object_num': step.get('object_num', None),
                        'grid_before': grid_before,
                        'grid_after': grid_after,
                        'grid_before_image': grid_to_base64(grid_before, cell_size=30) if grid_before else None,
                        'grid_after_image': grid_to_base64(grid_after, cell_size=30) if grid_after else None,
                        'visual_count': visual_count
                    })
                final_step = booklet['steps'][-1]
                final_grid = final_step.get('grid_after') or final_step.get('grid')
            
            puzzle_data['training_booklets'].append({
                'index': i,
                'num_steps': len(booklet.get('steps', [])),
                'final_grid': final_grid,
                'final_grid_image': grid_to_base64(final_grid, cell_size=40) if final_grid else None,
                'steps': steps_data
            })
        
        # Process test booklets (use the raw data we already loaded)
        for i, booklet in enumerate(test_booklets_raw):
            final_grid = None
            steps_data = []
            if booklet.get('steps'):
                for step in booklet.get('steps', []):
                    grid_before = step.get('grid_before') or step.get('grid')
                    grid_after = step.get('grid_after') or step.get('grid')
                    visual_count = sum([
                        1 if grid_before else 0,
                        1 if grid_after else 0,
                        1 if step.get('grid') else 0
                    ])
                    steps_data.append({
                        'step_number': step.get('step_number', ''),
                        'grid_before': grid_before,
                        'grid_after': grid_after,
                        'grid_before_image': grid_to_base64(grid_before, cell_size=30) if grid_before else None,
                        'grid_after_image': grid_to_base64(grid_after, cell_size=30) if grid_after else None,
                        'visual_count': visual_count
                    })
                final_step = booklet['steps'][-1]
                final_grid = final_step.get('grid_after') or final_step.get('grid')
            
            # Get predicted/expected output from booklet
            predicted_grid = booklet.get('predicted_grid') or booklet.get('final_grid') or final_grid
            expected_grid = booklet.get('output') or booklet.get('expected_grid')
            
            puzzle_data['test_booklets'].append({
                'index': i,
                'num_steps': len(booklet.get('steps', [])),
                'final_grid': predicted_grid,
                'expected_grid': expected_grid,
                'final_grid_image': grid_to_base64(predicted_grid, cell_size=40) if predicted_grid else None,
                'expected_grid_image': grid_to_base64(expected_grid, cell_size=40) if expected_grid else None,
                'steps': steps_data,
                'is_correct': booklet.get('is_correct', False),
                'accuracy': booklet.get('accuracy', 0.0)
            })
        
        # Count visuals per general step
        general_steps = puzzle_data.get('general_steps', [])
        for step in general_steps:
            visual_count = 0
            # Count visuals from training booklets
            for booklet in puzzle_data['training_booklets']:
                if booklet.get('steps'):
                    for s in booklet['steps']:
                        step_num = str(s.get('step_number', '')).split('.')[0]  # Get general step number
                        if step_num == str(step.get('step_number', '')):
                            visual_count += s.get('visual_count', 0)
            # Count visuals from test booklets
            for booklet in puzzle_data['test_booklets']:
                if booklet.get('steps'):
                    for s in booklet['steps']:
                        step_num = str(s.get('step_number', '')).split('.')[0]
                        if step_num == str(step.get('step_number', '')):
                            visual_count += s.get('visual_count', 0)
            step['visual_count'] = visual_count
        
        # Get label if exists
        labels = load_labels()
        if puzzle_id in labels:
            label_data = labels[puzzle_id]
            puzzle_data['current_label'] = label_data.get('label')
            puzzle_data['current_reasoning'] = label_data.get('reasoning', '')
            puzzle_data['label_timestamp'] = label_data.get('timestamp', '')
            puzzle_data['failure_modes'] = label_data.get('failure_modes', [])
            puzzle_data['auto_detected'] = label_data.get('auto_detected', False)
            puzzle_data['auto_detected_modes'] = label_data.get('auto_detected_modes', [])
            puzzle_data['manual_overrides'] = label_data.get('manual_overrides', [])
            puzzle_data['reviewer'] = label_data.get('reviewer', 'human')
        else:
            puzzle_data['current_label'] = None
            puzzle_data['current_reasoning'] = ''
            puzzle_data['label_timestamp'] = ''
            puzzle_data['failure_modes'] = []
            puzzle_data['auto_detected'] = False
            puzzle_data['auto_detected_modes'] = []
            puzzle_data['manual_overrides'] = []
            puzzle_data['reviewer'] = 'human'
        
        # Add duplicate version information
        puzzle_data['duplicate_versions'] = duplicate_versions
        puzzle_data['current_duplicate_index'] = current_index
        puzzle_data['num_duplicates'] = len(duplicate_versions) - 1 if len(duplicate_versions) > 1 else 0
        
        return jsonify(puzzle_data)
    except Exception as e:
        import traceback
        print(f"[ERROR] Exception loading puzzle: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/puzzle/<path:file_path>/training_predicted_input/<int:example_index>')
def get_training_predicted_input(file_path, example_index):
    """Get predicted input for a specific training example (lazy loading)"""
    try:
        file_path = file_path.replace('\\', '/')
        full_path = traces_dir / file_path
        
        if not full_path.exists():
            return jsonify({'error': f'File not found: {file_path}'}), 404
        
        with open(full_path, 'r') as f:
            data = json.load(f)
        
        training_booklets = data.get('training_booklets', [])
        if example_index >= len(training_booklets):
            return jsonify({'error': f'Training example {example_index} not found'}), 404
        
        booklet = training_booklets[example_index]
        predicted_input_grid = None
        predicted_input_image = None
        
        # Get initial grid from first step
        if booklet.get('steps') and len(booklet['steps']) > 0:
            first_step = booklet['steps'][0]
            predicted_input_grid = first_step.get('grid') or first_step.get('grid_before')
            if predicted_input_grid:
                predicted_input_image = grid_to_base64(predicted_input_grid, cell_size=50)
        
        if predicted_input_grid is None:
            return jsonify({'error': 'No predicted input found for this training example'}), 404
        
        return jsonify({
            'predicted_input_grid': predicted_input_grid,
            'predicted_input_image': predicted_input_image
        })
    except Exception as e:
        import traceback
        print(f"[ERROR] Exception loading predicted input: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/label', methods=['POST'])
def save_label():
    """Save reasoning label (allows editing existing labels)"""
    try:
        data = request.get_json()
        puzzle_id = data.get('puzzle_id')
        label = data.get('label')  # 'correct' or 'incorrect'
        reasoning = data.get('reasoning', '')
        file_path = data.get('file_path', '')
        failure_modes = data.get('failure_modes', [])  # List of failure mode codes
        
        if not puzzle_id or not label:
            return jsonify({'error': 'Missing puzzle_id or label'}), 400
        
        if label not in ['correct', 'incorrect', 'skipped']:
            return jsonify({'error': 'Label must be "correct", "incorrect", or "skipped"'}), 400
        
        # Validate failure modes (allowed for both correct and incorrect labels)
        valid_modes = ['A1', 'A2', 'A3', 'B1', 'B2', 'C1', 'C2', 'C3']
        if failure_modes:
            invalid_modes = [m for m in failure_modes if m not in valid_modes]
            if invalid_modes:
                return jsonify({'error': f'Invalid failure modes: {invalid_modes}'}), 400
        
        labels = load_labels()
        
        # Check if this is an edit (label already exists)
        is_edit = puzzle_id in labels
        existing_label = labels.get(puzzle_id, {})
        
        # Preserve auto-detection info if it exists
        auto_detected = existing_label.get('auto_detected', False)
        auto_detected_modes = existing_label.get('auto_detected_modes', [])
        
        # Track manual overrides (modes that differ from auto-detected)
        manual_overrides = []
        if auto_detected:
            # If user changes failure modes from auto-detected, track the difference
            if set(failure_modes) != set(auto_detected_modes):
                manual_overrides = failure_modes
        
        labels[puzzle_id] = {
            'label': label,
            'reasoning': reasoning,
            'file_path': file_path,
            'failure_modes': failure_modes,  # Store failure modes for both correct and incorrect labels
            'auto_detected': auto_detected,
            'auto_detected_modes': auto_detected_modes if auto_detected else [],
            'manual_overrides': manual_overrides,
            'timestamp': datetime.now().isoformat(),
            'reviewer': 'human',
            'edited': is_edit  # Track if this was edited
        }
        save_labels(labels)
        invalidate_cache()  # Invalidate cache when labels change
        
        return jsonify({
            'success': True, 
            'puzzle_id': puzzle_id, 
            'label': label,
            'failure_modes': failure_modes,
            'is_edit': is_edit
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/label/<puzzle_id>', methods=['DELETE'])
def delete_label(puzzle_id):
    """Delete a label (allows unlabeling)"""
    try:
        labels = load_labels()
        if puzzle_id in labels:
            del labels[puzzle_id]
            save_labels(labels)
            invalidate_cache()  # Invalidate cache when labels change
            return jsonify({'success': True, 'puzzle_id': puzzle_id})
        else:
            return jsonify({'error': 'Label not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get labeling statistics with accuracy and failure mode breakdown"""
    labels = load_labels()
    
    total_labeled = len(labels)
    correct_count = sum(1 for v in labels.values() if v.get('label') == 'correct')
    incorrect_count = sum(1 for v in labels.values() if v.get('label') == 'incorrect')
    skipped_count = sum(1 for v in labels.values() if v.get('label') == 'skipped')
    
    # Use cached puzzle metadata to count total puzzles
    puzzle_files = get_puzzle_metadata_cache()
    total_puzzles = len(puzzle_files)
    
    unlabeled = total_puzzles - total_labeled
    
    # Calculate accuracy rate (only for non-skipped puzzles)
    non_skipped_labeled = correct_count + incorrect_count
    accuracy_rate = (correct_count / non_skipped_labeled * 100) if non_skipped_labeled > 0 else 0
    
    # Count failure modes
    failure_mode_counts = {
        'A1': 0, 'A2': 0, 'A3': 0,
        'B1': 0, 'B2': 0,
        'C1': 0, 'C2': 0, 'C3': 0
    }
    
    for label_data in labels.values():
        if label_data.get('label') == 'incorrect':
            failure_modes = label_data.get('failure_modes', [])
            for mode in failure_modes:
                if mode in failure_mode_counts:
                    failure_mode_counts[mode] += 1
    
    return jsonify({
        'total_puzzles': total_puzzles,
        'total_labeled': total_labeled,
        'unlabeled': unlabeled,
        'correct': correct_count,
        'incorrect': incorrect_count,
        'skipped': skipped_count,
        'completion_rate': (total_labeled / total_puzzles * 100) if total_puzzles > 0 else 0,
        'accuracy_rate': accuracy_rate,
        'failure_modes': failure_mode_counts
    })

if __name__ == '__main__':
    print(f"[OK] Reasoning Labeler App starting...")
    print(f"[INFO] Traces directory: {traces_dir}")
    print(f"[INFO] Labels file: {labels_file}")
    app.run(debug=True, host='0.0.0.0', port=5001)

