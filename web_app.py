"""
SDLC Agent Web Interface

A web interface to upload requirements and view generated code results.
"""

import os
import sys
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from orchestrator import Orchestrator
from core.llm_client import LLMClient
from core.task_tracker import TaskTracker
from core.git_integration import GitHubPRCreator

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Store job history
jobs = []


TEXT_FILE_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.md', '.txt', '.html',
    '.css', '.scss', '.yaml', '.yml', '.toml', '.ini', '.env', '.sql', '.sh',
    '.bat', '.ps1', '.xml', '.csv', '.java', '.cs', '.go', '.rb', '.php',
    '.swift', '.kt', '.rs', '.c', '.cpp', '.h', '.hpp'
}
MAX_CONTEXT_FILES = int(os.getenv("MAX_CONTEXT_FILES", "12"))
MAX_CONTEXT_CHARS_PER_FILE = int(os.getenv("MAX_CONTEXT_CHARS_PER_FILE", "4000"))
MAX_CONTEXT_TOTAL_CHARS = int(os.getenv("MAX_CONTEXT_TOTAL_CHARS", "30000"))
EXCLUDED_OUTPUT_FILENAMES = {"project_memory.json", "summary.json", ".gitkeep"}


def _reset_upload_folder() -> None:
    """Reset upload folder so each new upload set has clean context."""
    upload_root = Path(app.config['UPLOAD_FOLDER'])
    if upload_root.exists():
        shutil.rmtree(upload_root, ignore_errors=True)
    upload_root.mkdir(parents=True, exist_ok=True)


def _extract_zip_archive(zip_path: Path, destination: Path) -> List[str]:
    """Extract ZIP archive safely and return extracted relative file paths."""
    extracted: List[str] = []
    with zipfile.ZipFile(zip_path, 'r') as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue

            relative_path = Path(member.filename)
            if relative_path.is_absolute() or '..' in relative_path.parts:
                continue

            target = destination / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)

            with archive.open(member, 'r') as source, open(target, 'wb') as dest:
                shutil.copyfileobj(source, dest)

            extracted.append(str(relative_path).replace('\\', '/'))

    return extracted


def _store_uploaded_files(files) -> List[str]:
    """Store regular uploads and extract ZIP archives into upload folder."""
    upload_root = Path(app.config['UPLOAD_FOLDER'])
    stored: List[str] = []

    for file in files:
        if not file or not file.filename:
            continue

        filename = secure_filename(file.filename)
        if not filename:
            continue

        target_path = upload_root / filename
        target_path.parent.mkdir(parents=True, exist_ok=True)
        file.save(str(target_path))

        if target_path.suffix.lower() == '.zip':
            try:
                extracted = _extract_zip_archive(target_path, upload_root)
                stored.extend(extracted)
            except (zipfile.BadZipFile, EOFError, RuntimeError, OSError):
                # If archive is invalid or temporarily locked, keep the file and continue.
                stored.append(filename)
            finally:
                if target_path.exists():
                    try:
                        target_path.unlink(missing_ok=True)
                    except OSError:
                        # Ignore transient file locks on Windows/OneDrive/AV scanners.
                        pass
        else:
            stored.append(filename)

    return stored


def _is_likely_text(raw_bytes: bytes) -> bool:
    """Quick heuristic to skip binary files when building code context."""
    if not raw_bytes:
        return True
    return b'\x00' not in raw_bytes


def _collect_uploaded_context() -> List[Dict[str, str]]:
    """Collect uploaded file snippets to provide existing-code context to the agent."""
    upload_root = Path(app.config['UPLOAD_FOLDER'])
    if not upload_root.exists():
        return []

    files = [p for p in upload_root.rglob('*') if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    context_files = []
    remaining_chars = MAX_CONTEXT_TOTAL_CHARS

    for path in files:
        if len(context_files) >= MAX_CONTEXT_FILES or remaining_chars <= 0:
            break

        try:
            suffix = path.suffix.lower()
            if suffix and suffix not in TEXT_FILE_EXTENSIONS:
                preview = path.read_bytes()[:2048]
                if not _is_likely_text(preview):
                    continue

            content = path.read_text(encoding='utf-8', errors='ignore').strip()
            if not content:
                continue

            snippet_size = min(MAX_CONTEXT_CHARS_PER_FILE, remaining_chars)
            snippet = content[:snippet_size]
            remaining_chars -= len(snippet)

            context_files.append({
                'name': str(path.relative_to(upload_root)).replace('\\', '/'),
                'content': snippet,
            })
        except Exception:
            continue

    return context_files


def _build_uploaded_context_text(uploaded_context: List[Dict[str, str]]) -> str:
    """Format uploaded file snippets for prompts."""
    if not uploaded_context:
        return "No uploaded existing code context was found."

    sections = []
    for item in uploaded_context:
        sections.append(
            f"### FILE: {item['name']}\n"
            f"```text\n{item['content']}\n```"
        )

    return "\n\n".join(sections)


def _build_enhanced_goal(
    goal: str,
    mode: str,
    uploaded_context: List[Dict[str, str]],
    task_context: Dict[str, Any] = None,
) -> str:
    """Create a mode-aware goal that includes existing codebase context."""
    task_context = task_context or {}

    # Use RAG-style analysis for enhance mode
    if mode == 'enhance' and uploaded_context:
        return _build_enhancement_prompt(goal, uploaded_context, task_context)

    mode_instructions = {
        'develop': 'Build requested functionality from requirements, using uploaded code context when relevant.',
        'task': 'Execute this Excel task exactly as requested and ensure implementation aligns with task type, priority, and component.',
    }

    return (
        f"Execution mode: {mode}\n"
        f"Mode instruction: {mode_instructions.get(mode, mode_instructions['develop'])}\n\n"
        f"Primary requirement:\n{goal}\n\n"
        f"Task context:\n{json.dumps(task_context, indent=2) if task_context else 'N/A'}\n\n"
        f"Existing codebase context from uploaded files:\n{_build_uploaded_context_text(uploaded_context)}"
    )


def _build_enhancement_prompt(
    goal: str,
    uploaded_context: List[Dict[str, str]],
    task_context: Dict[str, Any] = None,
) -> str:
    """Build RAG-style enhancement prompt with code structure analysis."""
    task_context = task_context or {}
    
    # Extract code structure for RAG-style retrieval
    code_structure = _analyze_code_structure(uploaded_context)
    
    return (
        "You are an expert code enhancer using RAG (Retrieval-Augmented Generation) approach.\n"
        "Analyze the uploaded codebase systematically like a transformer-based code understanding system.\n\n"
        "## ENHANCEMENT APPROACH:\n"
        "1. **Semantic Analysis**: Understand existing code structure, patterns, and architecture\n"
        "2. **Dependency Mapping**: Identify module relationships and integration points\n"
        "3. **Impact Assessment**: Determine which files need modification and potential side effects\n"
        "4. **Minimal Changes**: Preserve existing behavior, make targeted improvements only\n\n"
        "## CODE STRUCTURE SUMMARY (Auto-extracted):\n"
        f"{code_structure}\n\n"
        "## ENHANCEMENT REQUEST:\n"
        f"{goal}\n\n"
        "## REQUIREMENTS:\n"
        "1. **Preserve Compatibility**: Existing functionality must not break\n"
        "2. **Follow Existing Patterns**: Match the codebase's style, naming conventions, and architecture\n"
        "3. **Incremental Changes**: Make minimal, focused modifications\n"
        "4. **Full File Output**: Output complete enhanced files (not patches or diffs)\n"
        "5. **Add Tests**: If the codebase has tests, add tests for new functionality\n\n"
        f"Task context:\n{json.dumps(task_context, indent=2) if task_context else 'N/A'}\n\n"
        f"## FULL CODE CONTEXT:\n{_build_uploaded_context_text(uploaded_context)}"
    )


def _build_explanation_prompt(
    question: str,
    uploaded_context: List[Dict[str, str]],
    task_context: Dict[str, Any] = None,
) -> str:
    """Build RAG-style explanation prompt with code structure analysis."""
    task_context = task_context or {}
    
    # Extract code structure for RAG-style retrieval
    code_structure = _analyze_code_structure(uploaded_context)
    
    return (
        "You are an expert code analyst using RAG (Retrieval-Augmented Generation) approach.\n"
        "Analyze the uploaded codebase systematically like a transformer-based code understanding system.\n\n"
        "## ANALYSIS APPROACH:\n"
        "1. **Semantic Chunking**: Break down code into logical units (functions, classes, modules)\n"
        "2. **Dependency Graph**: Identify imports, exports, and module relationships\n"
        "3. **Control Flow**: Trace execution paths and data transformations\n"
        "4. **Pattern Recognition**: Identify design patterns, anti-patterns, and architectural style\n\n"
        "## CODE STRUCTURE SUMMARY (Auto-extracted):\n"
        f"{code_structure}\n\n"
        "## YOUR TASK:\n"
        f"Question/Focus: {question}\n\n"
        "## REQUIRED OUTPUT:\n"
        "1. **Architecture Overview**: High-level system design and component relationships\n"
        "2. **Module Breakdown**: Each file's purpose, key functions, and responsibilities\n"
        "3. **Data Flow**: How data moves through the system\n"
        "4. **Entry Points**: Main execution paths and API endpoints\n"
        "5. **Dependencies**: External libraries and internal module connections\n"
        "6. **Recommendations**: Potential improvements, refactoring opportunities, or concerns\n\n"
        f"Task context:\n{json.dumps(task_context, indent=2) if task_context else 'N/A'}\n\n"
        f"## FULL CODE CONTEXT:\n{_build_uploaded_context_text(uploaded_context)}"
    )


def _analyze_code_structure(uploaded_context: List[Dict[str, str]]) -> str:
    """Extract code structure for RAG-style retrieval (functions, classes, imports)."""
    import re
    
    structure_parts = []
    
    for item in uploaded_context:
        filename = item['name']
        content = item['content']
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        file_info = [f"**{filename}**:"]
        
        # Python analysis
        if ext == 'py':
            # Classes
            classes = re.findall(r'^class\s+(\w+)(?:\(([^)]*)\))?:', content, re.MULTILINE)
            if classes:
                class_list = [f"{c[0]}({c[1]})" if c[1] else c[0] for c in classes]
                file_info.append(f"  Classes: {', '.join(class_list)}")
            
            # Functions
            funcs = re.findall(r'^(?:async\s+)?def\s+(\w+)\s*\(', content, re.MULTILINE)
            if funcs:
                file_info.append(f"  Functions: {', '.join(funcs[:15])}" + ("..." if len(funcs) > 15 else ""))
            
            # Imports
            imports = re.findall(r'^(?:from\s+(\S+)\s+)?import\s+([^\n]+)', content, re.MULTILINE)
            if imports:
                import_names = [i[0] or i[1].split(',')[0].strip() for i in imports[:10]]
                file_info.append(f"  Imports: {', '.join(import_names)}" + ("..." if len(imports) > 10 else ""))
        
        # JavaScript/TypeScript analysis
        elif ext in ('js', 'ts', 'jsx', 'tsx'):
            # Classes
            classes = re.findall(r'class\s+(\w+)', content)
            if classes:
                file_info.append(f"  Classes: {', '.join(classes)}")
            
            # Functions
            funcs = re.findall(r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\()', content)
            func_names = [f[0] or f[1] for f in funcs if f[0] or f[1]]
            if func_names:
                file_info.append(f"  Functions: {', '.join(func_names[:15])}" + ("..." if len(func_names) > 15 else ""))
            
            # Imports
            imports = re.findall(r"import\s+(?:{[^}]+}|\w+)\s+from\s+['\"]([^'\"]+)['\"]", content)
            if imports:
                file_info.append(f"  Imports: {', '.join(imports[:10])}" + ("..." if len(imports) > 10 else ""))
            
            # Exports
            exports = re.findall(r'export\s+(?:default\s+)?(?:class|function|const)\s+(\w+)', content)
            if exports:
                file_info.append(f"  Exports: {', '.join(exports)}")
        
        # Config/data files
        elif ext in ('json', 'yaml', 'yml', 'toml'):
            file_info.append(f"  Type: Configuration/Data file")
        
        # Markdown/docs
        elif ext in ('md', 'txt', 'rst'):
            file_info.append(f"  Type: Documentation")
        
        if len(file_info) > 1:
            structure_parts.append('\n'.join(file_info))
    
    if not structure_parts:
        return "No parseable code structure detected. Raw files will be analyzed."
    
    return '\n'.join(structure_parts)


def _provider_availability(config: Config) -> Dict[str, Dict[str, Any]]:
    """Return provider availability and configuration state for UI."""
    return {
        'mock': {
            'label': 'Mock (Demo)',
            'configured': True,
            'reason': 'Always available for demo/testing',
        },
        'openai': {
            'label': 'OpenAI',
            'configured': bool(config.openai_api_key),
            'reason': 'OPENAI_API_KEY required',
        },
        'anthropic': {
            'label': 'Anthropic',
            'configured': bool(config.anthropic_api_key),
            'reason': 'ANTHROPIC_API_KEY required',
        },
        'waip': {
            'label': 'WAIP',
            'configured': bool(config.waip_api_key),
            'reason': 'WAIP_API_KEY required',
        },
        'local': {
            'label': 'Local LLM',
            'configured': bool(config.local_llm_url),
            'reason': 'LOCAL_LLM_URL required',
        },
    }


def _is_provider_configured(provider: str, config: Config) -> bool:
    """Check whether selected provider has required configuration."""
    return _provider_availability(config).get(provider, {}).get('configured', False)


def _should_include_output_file(relpath: str) -> bool:
    """Exclude metadata and hidden files from UI output listing."""
    normalized = relpath.replace('\\', '/')
    name = os.path.basename(normalized).lower()

    if name in EXCLUDED_OUTPUT_FILENAMES:
        return False
    if name.startswith('.'):
        return False
    if '/__pycache__/' in f'/{normalized}/':
        return False

    return True


def _sort_output_files(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort output files in a readable order (source files first)."""
    priority = {
        '.py': 1,
        '.ts': 1,
        '.tsx': 1,
        '.js': 1,
        '.jsx': 1,
        '.html': 2,
        '.css': 2,
        '.json': 3,
        '.md': 4,
    }

    def _key(item: Dict[str, Any]) -> Any:
        ext = os.path.splitext(item.get('name', ''))[1].lower()
        return (priority.get(ext, 5), item.get('name', '').lower())

    return sorted(files, key=_key)


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
    _reset_upload_folder()
    uploaded = _store_uploaded_files(files)
    
    return jsonify({'uploaded': uploaded, 'count': len(uploaded)})


@app.route('/run', methods=['POST'])
def run_agent():
    """Run the SDLC agent with given requirements."""
    # Handle both JSON and FormData requests
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()
    
    goal = (data.get('goal') or '').strip()
    provider = data.get('provider', 'mock')
    mode = (data.get('mode') or 'develop').strip().lower()
    task_id = (data.get('task_id') or '').strip()
    
    # Handle file uploads if present; reset context to avoid mixing old projects.
    if 'files' in request.files:
        try:
            uploaded_files = request.files.getlist('files')
            has_named_files = any(f and f.filename for f in uploaded_files)
            if has_named_files:
                _reset_upload_folder()
                _store_uploaded_files(uploaded_files)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Upload processing failed: {str(e)}'
            }), 400

    valid_modes = {'develop', 'enhance', 'explain', 'task'}
    if mode not in valid_modes:
        return jsonify({'success': False, 'error': f'Invalid mode: {mode}'}), 400

    if mode == 'task' and not task_id:
        return jsonify({'success': False, 'error': 'Task mode requires a task_id from Excel'}), 400
    
    # Create unique output directory for this run
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], f'run_{timestamp}')
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Initialize config
        config = Config.from_env()

        # Optional Excel task context
        task_context = None
        if task_id:
            tasks_file = os.getenv('TASKS_FILE', 'tasks/development_tasks.xlsx')
            tracker = TaskTracker(tasks_file)
            task = tracker.get_task(task_id)
            if not task:
                return jsonify({'success': False, 'error': f'Task not found: {task_id}'}), 404

            task_context = task.to_dict()
            if not goal:
                goal = f"{task.title}: {task.description}"

        # Get appropriate API key and model based on provider
        api_key = None
        model = None
        base_url = None

        if not _is_provider_configured(provider, config):
            return jsonify({
                'success': False,
                'error': f"Provider '{provider}' is not configured. Check API key/environment settings."
            }), 400
        
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
        
        uploaded_context = _collect_uploaded_context()

        # Fallback: if no uploaded files, try reading workspace files for context
        if not uploaded_context and mode in ('explain', 'enhance'):
            workspace_root = Path('workspace')
            if workspace_root.exists():
                for p in sorted(workspace_root.rglob('*')):
                    if not p.is_file():
                        continue
                    suffix = p.suffix.lower()
                    if suffix and suffix not in TEXT_FILE_EXTENSIONS:
                        preview = p.read_bytes()[:2048]
                        if not _is_likely_text(preview):
                            continue
                    try:
                        content = p.read_text(encoding='utf-8', errors='ignore').strip()
                        if content:
                            uploaded_context.append({
                                'name': str(p.relative_to(workspace_root)).replace('\\', '/'),
                                'content': content[:MAX_CONTEXT_CHARS_PER_FILE],
                            })
                    except Exception:
                        continue
                    if len(uploaded_context) >= MAX_CONTEXT_FILES:
                        break

        # Explain mode: understand existing codebase and answer user question
        if mode == 'explain':
            if not uploaded_context:
                return jsonify({
                    'success': False,
                    'error': 'No code files found. Upload source files or ensure the workspace/ folder contains code.'
                }), 400

            llm_client = LLMClient(
                provider=provider,
                api_key=api_key,
                model=model,
                base_url=base_url,
            )

            question = goal or 'Explain the uploaded codebase and suggest enhancements based on requirements.'
            explanation = llm_client.chat(
                user_message=_build_explanation_prompt(question, uploaded_context, task_context),
                system_prompt='You are a senior software architect. Explain clearly, with actionable guidance and minimal jargon.',
                temperature=0.2,
            )

            job = {
                'id': timestamp,
                'goal': question,
                'provider': provider,
                'mode': mode,
                'task_id': task_id or None,
                'status': 'completed',
                'output_dir': output_dir,
                'files': [],
                'explanation': explanation,
                'uploaded_context_files': [f['name'] for f in uploaded_context],
                'timestamp': datetime.now().isoformat()
            }
            jobs.insert(0, job)

            return jsonify({
                'success': True,
                'job_id': timestamp,
                'files': [],
                'explanation': explanation,
                'task_id': task_id or None,
                'summary': {
                    'status': 'explained',
                    'mode': mode,
                    'uploaded_context_files': len(uploaded_context)
                }
            })

        # Run orchestrator with mode-aware requirement payload
        enhanced_goal = _build_enhanced_goal(goal, mode, uploaded_context, task_context)
        orchestrator = Orchestrator(
            llm_provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            output_dir=output_dir,
            max_iterations=config.max_iterations,
            debug_mode=config.debug_mode,
            # Git / PR settings from env
            repo_local_path=os.getenv('GIT_LOCAL_PATH', './workspace'),
            repo_url=os.getenv('GIT_REPO_URL', ''),
            main_branch=os.getenv('GIT_MAIN_BRANCH', 'main'),
            github_token=os.getenv('GITHUB_TOKEN'),
            github_owner=os.getenv('GITHUB_OWNER'),
            github_repo=os.getenv('GITHUB_REPO'),
            auto_create_pr=os.getenv('AUTO_CREATE_PR', 'true').lower() == 'true',
        )
        result = orchestrator.run(enhanced_goal)
        
        # Collect generated files
        generated_files = []
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                filepath = os.path.join(root, file)
                relpath = os.path.relpath(filepath, output_dir)
                if not _should_include_output_file(relpath):
                    continue
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                generated_files.append({
                    'name': relpath,
                    'content': content,
                    'size': len(content)
                })
        generated_files = _sort_output_files(generated_files)
        
        # Store job info (including Git/PR details)
        git_info = result.get('git', {})
        pr_info = result.get('pr', {})
        
        job = {
            'id': timestamp,
            'goal': goal,
            'provider': provider,
            'mode': mode,
            'task_id': task_id or None,
            'status': 'completed',
            'output_dir': output_dir,
            'files': generated_files,
            'uploaded_context_files': [f['name'] for f in uploaded_context],
            'git_branch': git_info.get('branch', ''),
            'pr_url': pr_info.get('pr_url', ''),
            'pr_number': pr_info.get('pr_number'),
            'workflow_log': result.get('workflow_log', []),
            'timestamp': datetime.now().isoformat()
        }
        jobs.insert(0, job)
        
        return jsonify({
            'success': True,
            'job_id': timestamp,
            'files': generated_files,
            'task_id': task_id or None,
            'git': {
                'branch': git_info.get('branch', ''),
                'files_committed': git_info.get('files', []),
                'success': git_info.get('success', False),
            },
            'pr': {
                'url': pr_info.get('pr_url', ''),
                'number': pr_info.get('pr_number'),
                'success': pr_info.get('success', False),
            },
            'workflow_log': result.get('workflow_log', []),
            'summary': {k: v for k, v in result.items() if k not in ('git', 'pr', 'workflow_log')}
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/check-pr/<int:pr_number>')
def check_pr_status(pr_number):
    """Check if a PR has been merged (workflow completion check)."""
    token = os.getenv('GITHUB_TOKEN')
    owner = os.getenv('GITHUB_OWNER')
    repo = os.getenv('GITHUB_REPO')
    
    if not all([token, owner, repo]):
        return jsonify({'success': False, 'error': 'GitHub not configured'}), 400
    
    pr_creator = GitHubPRCreator(token=token, owner=owner, repo=repo)
    pr_info = pr_creator.get_pr(pr_number)
    
    if not pr_info.get('success'):
        return jsonify({'success': False, 'error': pr_info.get('error', 'PR not found')}), 404
    
    status = 'merged' if pr_info.get('merged') else pr_info.get('state', 'unknown')
    
    return jsonify({
        'success': True,
        'pr_number': pr_number,
        'status': status,
        'merged': pr_info.get('merged', False),
        'title': pr_info.get('title', ''),
        'url': pr_info.get('url', ''),
        'workflow_complete': pr_info.get('merged', False),
    })


@app.route('/workflow-status')
def workflow_status():
    """Return the latest workflow status with Git/PR info."""
    if not jobs:
        return jsonify({'status': 'idle', 'jobs': []})
    
    latest = jobs[0]
    return jsonify({
        'status': latest.get('status', 'unknown'),
        'latest_job': {
            'id': latest.get('id'),
            'goal': latest.get('goal', ''),
            'mode': latest.get('mode', ''),
            'git_branch': latest.get('git_branch', ''),
            'pr_url': latest.get('pr_url', ''),
            'pr_number': latest.get('pr_number'),
            'timestamp': latest.get('timestamp', ''),
        },
        'total_jobs': len(jobs),
    })


@app.route('/previous-runs')
def get_previous_runs():
    """List all previous runs with their results."""
    output_folder = app.config['OUTPUT_FOLDER']
    runs = []
    
    if not os.path.exists(output_folder):
        return jsonify({'runs': []})
    
    # Get all run directories
    for item in sorted(os.listdir(output_folder), reverse=True):
        if item.startswith('run_'):
            run_path = os.path.join(output_folder, item)
            if os.path.isdir(run_path):
                # Collect all files in this run
                files = []
                for root, dirs, filenames in os.walk(run_path):
                    for filename in filenames:
                        filepath = os.path.join(root, filename)
                        relpath = os.path.relpath(filepath, run_path)
                        if not _should_include_output_file(relpath):
                            continue
                        try:
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            files.append({
                                'name': relpath,
                                'content': content,
                                'size': len(content),
                                'lines': content.count('\n') + 1
                            })
                        except:
                            pass
                
                if files:
                    runs.append({
                        'id': item,
                        'timestamp': item.replace('run_', ''),
                        'file_count': len(files),
                        'files': _sort_output_files(files)
                    })
    
    return jsonify({'runs': runs})


@app.route('/previous-run/<run_id>')
def get_previous_run(run_id):
    """Get details of a specific previous run."""
    run_path = os.path.join(app.config['OUTPUT_FOLDER'], run_id)
    
    if not os.path.exists(run_path):
        return jsonify({'error': 'Run not found'}), 404
    
    # Collect all files in this run
    files = []
    for root, dirs, filenames in os.walk(run_path):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            relpath = os.path.relpath(filepath, run_path)
            if not _should_include_output_file(relpath):
                continue
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                files.append({
                    'name': relpath,
                    'content': content,
                    'size': len(content),
                    'lines': content.count('\n') + 1
                })
            except:
                pass
    
    files = _sort_output_files(files)
    return jsonify({
        'id': run_id,
        'timestamp': run_id.replace('run_', ''),
        'files': files,
        'file_count': len(files),
        'total_size': sum(f['size'] for f in files),
        'total_lines': sum(f['lines'] for f in files)
    })


@app.route('/jobs')
def list_jobs():
    """List all job runs."""
    return jsonify(jobs)


@app.route('/tasks', methods=['GET'])
def list_excel_tasks():
    """List tasks from the configured Excel/JSON task tracker file."""
    try:
        tasks_file = os.getenv('TASKS_FILE', 'tasks/development_tasks.xlsx')
        tracker = TaskTracker(tasks_file)
        tasks = [task.to_dict() for task in tracker.get_all_tasks()]
        tasks.sort(key=lambda t: t.get('created_at') or '', reverse=True)

        return jsonify({
            'success': True,
            'source': tasks_file,
            'count': len(tasks),
            'tasks': tasks,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/capabilities', methods=['GET'])
def capabilities():
    """Expose supported modes and provider availability for UI rendering."""
    config = Config.from_env()
    providers = _provider_availability(config)

    return jsonify({
        'success': True,
        'providers': providers,
        'modes': [
            {
                'id': 'develop',
                'label': 'Build from Requirement',
                'description': 'Create implementation from your requirement prompt.',
            },
            {
                'id': 'enhance',
                'label': 'Enhance Code (RAG)',
                'description': 'RAG-style enhancement: analyzes code structure, preserves patterns, and makes targeted improvements.',
            },
            {
                'id': 'explain',
                'label': 'Explain Code (RAG)',
                'description': 'RAG-style analysis: extracts code structure, dependencies, and provides transformer-level understanding.',
            },
            {
                'id': 'task',
                'label': 'Run Excel Task',
                'description': 'Execute task selected from the tracked Excel sheet.',
            },
        ],
        'task_source': os.getenv('TASKS_FILE', 'tasks/development_tasks.xlsx')
    })


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
            if not _should_include_output_file(relpath):
                continue
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

    return jsonify(_sort_output_files(all_files))


if __name__ == '__main__':
    print("\n🚀 Starting SDLC Agent Web Interface...")
    print("📍 Open http://localhost:5000 in your browser\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
