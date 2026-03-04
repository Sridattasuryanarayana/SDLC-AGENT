"""
SDLC Agent Web Interface

A web interface to upload requirements and view generated code results.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from orchestrator import Orchestrator

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Store job history
jobs = []


@app.route('/')
def index():
    """Main page with drag-drop interface."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files')
    uploaded = []
    
    for file in files:
        if file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            uploaded.append(filename)
    
    return jsonify({'uploaded': uploaded, 'count': len(uploaded)})


@app.route('/run', methods=['POST'])
def run_agent():
    """Run the SDLC agent with given requirements."""
    data = request.json
    goal = data.get('goal', 'Build a software project')
    provider = data.get('provider', 'mock')
    
    # Create unique output directory for this run
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], f'run_{timestamp}')
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Initialize config
        config = Config.from_env()
        
        # Get appropriate API key and model based on provider
        api_key = None
        model = None
        base_url = None
        
        if provider == 'openai':
            api_key = config.openai_api_key
            model = config.openai_model
        elif provider == 'anthropic':
            api_key = config.anthropic_api_key
            model = config.anthropic_model
        elif provider == 'waip':
            api_key = config.waip_api_key
            model = config.waip_model
            base_url = config.waip_api_endpoint
        elif provider == 'local':
            base_url = config.local_llm_url
            model = config.local_llm_model
        
        # Run orchestrator with correct parameters
        orchestrator = Orchestrator(
            llm_provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            output_dir=output_dir,
            max_iterations=config.max_iterations,
            debug_mode=config.debug_mode
        )
        result = orchestrator.run(goal)
        
        # Collect generated files
        generated_files = []
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                filepath = os.path.join(root, file)
                relpath = os.path.relpath(filepath, output_dir)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                generated_files.append({
                    'name': relpath,
                    'content': content,
                    'size': len(content)
                })
        
        # Store job info
        job = {
            'id': timestamp,
            'goal': goal,
            'provider': provider,
            'status': 'completed',
            'output_dir': output_dir,
            'files': generated_files,
            'timestamp': datetime.now().isoformat()
        }
        jobs.insert(0, job)
        
        return jsonify({
            'success': True,
            'job_id': timestamp,
            'files': generated_files,
            'summary': result if isinstance(result, dict) else {'status': 'completed'}
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/jobs')
def list_jobs():
    """List all job runs."""
    return jsonify(jobs)


@app.route('/job/<job_id>')
def get_job(job_id):
    """Get details of a specific job."""
    for job in jobs:
        if job['id'] == job_id:
            return jsonify(job)
    return jsonify({'error': 'Job not found'}), 404


@app.route('/files/<path:filename>')
def get_file(filename):
    """Serve generated files."""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)


@app.route('/output')
def list_output():
    """List all files in output directory."""
    output_dir = app.config['OUTPUT_FOLDER']
    all_files = []
    
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            filepath = os.path.join(root, file)
            relpath = os.path.relpath(filepath, output_dir)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except:
                content = '[Binary file]'
            
            all_files.append({
                'name': relpath,
                'content': content,
                'size': os.path.getsize(filepath)
            })
    
    return jsonify(all_files)


if __name__ == '__main__':
    print("\n🚀 Starting SDLC Agent Web Interface...")
    print("📍 Open http://localhost:5000 in your browser\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
