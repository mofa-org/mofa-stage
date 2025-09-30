import os
import sys
import platform
import subprocess
import signal
import json
import time
import logging
import tempfile
import shutil
import atexit
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ttyd_manager')

# Global variables
ttyd_process = None
pid_file = os.path.join(tempfile.gettempdir(), 'mofa_ttyd.pid')
log_file = os.path.join(tempfile.gettempdir(), 'mofa_ttyd.log')
ALLOW_ORIGIN_FLAG_SUPPORTED = {}

# Common locations where ttyd/brew binaries usually live when launched from a GUI app
COMMON_BINARY_DIRS = [
    '/usr/local/bin',
    '/opt/homebrew/bin',
    '/usr/bin',
    '/bin'
]


def build_search_path(extra_paths=None):
    """Compose a PATH string that covers brew/GUI launch scenarios."""
    paths = []
    current = os.environ.get('PATH', '')
    if current:
        paths.extend(current.split(os.pathsep))

    paths.extend(COMMON_BINARY_DIRS)

    if extra_paths:
        if isinstance(extra_paths, str):
            extra_paths = [extra_paths]
        paths.extend(extra_paths)

    # Preserve order but drop duplicates/empties
    seen = set()
    ordered = []
    for entry in paths:
        if not entry:
            continue
        if entry not in seen:
            seen.add(entry)
            ordered.append(entry)

    return os.pathsep.join(ordered)


def resolve_ttyd_binary(settings=None):
    """Locate the ttyd executable, considering GUI PATH limitations."""
    search_path = build_search_path()
    settings = settings or {}

    # Highest priority: explicit path from settings.json
    custom_path = settings.get('ttyd_binary_path') if isinstance(settings, dict) else None
    if custom_path and os.path.isfile(custom_path) and os.access(custom_path, os.X_OK):
        return custom_path

    # Fall back to PATH lookup (augmented with brew dirs)
    candidate = shutil.which('ttyd', path=search_path)
    if candidate:
        return candidate

    # As a final fallback, probe the common directories directly
    for directory in COMMON_BINARY_DIRS:
        candidate = os.path.join(directory, 'ttyd')
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def ttyd_supports_allow_origin(settings=None):
    """Detect whether the ttyd binary understands --allow-origin (cached per binary)."""
    ttyd_binary = resolve_ttyd_binary(settings)

    if not ttyd_binary:
        return False

    if ttyd_binary in ALLOW_ORIGIN_FLAG_SUPPORTED:
        return ALLOW_ORIGIN_FLAG_SUPPORTED[ttyd_binary]

    try:
        env = os.environ.copy()
        env['PATH'] = build_search_path()
        result = subprocess.run(
            [ttyd_binary, '--help'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            env=env
        )
        ALLOW_ORIGIN_FLAG_SUPPORTED[ttyd_binary] = '--allow-origin' in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        logger.debug('Unable to determine ttyd --allow-origin support: %s', exc)
        ALLOW_ORIGIN_FLAG_SUPPORTED[ttyd_binary] = False

    return ALLOW_ORIGIN_FLAG_SUPPORTED[ttyd_binary]

def is_ttyd_installed():
    """Check if ttyd is installed and available in PATH"""
    settings = get_settings()
    ttyd_binary = resolve_ttyd_binary(settings)
    if not ttyd_binary:
        return False

    try:
        # Run ttyd --version to check if it's available
        result = subprocess.run(
            [ttyd_binary, '--version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, 'PATH': build_search_path()}
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_ttyd():
    """Install ttyd based on the current platform"""
    system = platform.system().lower()
    
    if system == 'linux':
        # Detect package manager
        if os.path.exists('/usr/bin/apt-get') or os.path.exists('/usr/bin/apt'):
            logger.info("Detected Debian/Ubuntu, installing ttyd using apt...")
            try:
                # Install dependencies
                subprocess.run(['sudo', 'apt-get', 'update'], check=True)
                subprocess.run([
                    'sudo', 'apt-get', 'install', '-y', 
                    'build-essential', 'cmake', 'git', 
                    'libjson-c-dev', 'libwebsockets-dev'
                ], check=True)
                
                # Create temporary directory for build
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Clone ttyd repository
                    subprocess.run([
                        'git', 'clone', 'https://github.com/tsl0922/ttyd.git', tmpdir
                    ], check=True)
                    
                    # Build and install ttyd
                    build_dir = os.path.join(tmpdir, 'build')
                    os.makedirs(build_dir, exist_ok=True)
                    
                    subprocess.run(['cmake', '..'], cwd=build_dir, check=True)
                    subprocess.run(['make'], cwd=build_dir, check=True)
                    subprocess.run(['sudo', 'make', 'install'], cwd=build_dir, check=True)
                
                logger.info("ttyd installed successfully!")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install ttyd: {e}")
                return False
        else:
            logger.error("Unsupported Linux distribution. Please install ttyd manually.")
            return False
    
    elif system == 'darwin':  # macOS
        try:
            logger.info("Detected macOS, installing ttyd using brew...")
            # Check if Homebrew is installed
            brew_env = {**os.environ, 'PATH': build_search_path()}
            try:
                subprocess.run(['brew', '--version'], check=True, stdout=subprocess.PIPE, env=brew_env)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error("Homebrew not found. Please install Homebrew first: https://brew.sh/")
                return False
            
            # Install ttyd using Homebrew
            subprocess.run(['brew', 'install', 'ttyd'], check=True, env=brew_env)
            logger.info("ttyd installed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install ttyd: {e}")
            return False
    
    else:
        logger.error(f"Unsupported operating system: {system}. Please install ttyd manually.")
        return False

def get_settings():
    """Load settings from settings.json"""
    try:
        settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'settings.json')
        with open(settings_path, 'r') as f:
            settings = json.load(f)
        return settings
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        # Return default settings
        return {
            "ttyd_port": 7681,
            "mofa_dir": os.path.expanduser("~"),
        }

def get_pid_from_file():
    """Get the ttyd process ID from the PID file, if it exists"""
    try:
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            return pid
        return None
    except Exception as e:
        logger.error(f"Error reading PID file: {e}")
        return None

def is_process_running(pid):
    """Check if a process with the given PID is running"""
    if pid is None:
        return False
    
    try:
        os.kill(pid, 0)  # Send signal 0 to check if process exists
        return True
    except OSError:
        return False

def stop_ttyd(force=False):
    """Stop the ttyd process if it's running
    
    Args:
        force (bool): If True, forcefully stop any ttyd process.
                     If False, only stop if started by this session.
    """
    global ttyd_process
    
    if force:
        # Force stop any existing ttyd process
        pid = get_pid_from_file()
        
        if pid and is_process_running(pid):
            logger.info(f"Force stopping ttyd process (PID: {pid})...")
            try:
                os.kill(pid, signal.SIGTERM)
                # Wait for the process to terminate
                for _ in range(10):  # Wait up to 5 seconds
                    if not is_process_running(pid):
                        break
                    time.sleep(0.5)
                else:
                    # Force kill if it didn't terminate
                    os.kill(pid, signal.SIGKILL)
                
                logger.info("ttyd process force stopped.")
            except OSError as e:
                logger.error(f"Failed to force stop ttyd process: {e}")
    
    # Always clean up our own process if it exists
    if ttyd_process and ttyd_process.poll() is None:
        logger.info("Terminating ttyd process started by this session...")
        try:
            ttyd_process.terminate()
            # Wait for graceful termination
            try:
                ttyd_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                ttyd_process.kill()  # Force kill if timeout
            ttyd_process = None
        except Exception as e:
            logger.error(f"Error terminating own ttyd process: {e}")
    
    # Remove PID file only if force stopping
    if force and os.path.exists(pid_file):
        os.remove(pid_file)

def start_ttyd():
    """Start the ttyd service with configured settings"""
    global ttyd_process
    
    # First, ensure ttyd is installed
    if not is_ttyd_installed():
        logger.warning("ttyd is not installed. Skipping startup until user installs it.")
        return False
    
    # Stop any existing ttyd process (force stop)
    stop_ttyd(force=True)
    
    # Get settings
    settings = get_settings()
    ttyd_port = settings.get('ttyd_port', 7681)
    mofa_dir = settings.get('mofa_dir', os.path.expanduser("~"))
    
    # Determine working directory priority:
    # 1. mofa_dir/python if exists
    # 2. mofa_dir if exists  
    # 3. parent directory of current stage project
    # 4. home directory as fallback
    working_dir = None
    
    if mofa_dir and os.path.exists(mofa_dir):
        # Check if mofa_dir/python exists
        mofa_python_dir = os.path.join(mofa_dir, 'python')
        if os.path.exists(mofa_python_dir):
            working_dir = mofa_python_dir
            logger.info(f"Using mofa/python directory: {working_dir}")
        else:
            working_dir = mofa_dir
            logger.info(f"Using mofa directory: {working_dir}")
    else:
        # Fallback to parent of current stage directory
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend parent
        stage_parent = os.path.dirname(current_dir)  # stage parent
        if os.path.exists(stage_parent):
            working_dir = stage_parent
            logger.info(f"Using stage parent directory: {working_dir}")
        else:
            working_dir = os.path.expanduser("~")
            logger.warning(f"All preferred directories not found, using home directory: {working_dir}")
    
    # Final check
    if not os.path.exists(working_dir):
        logger.warning(f"Determined working directory '{working_dir}' doesn't exist. Using home directory instead.")
        working_dir = os.path.expanduser("~")
    
    ttyd_binary = resolve_ttyd_binary(settings)
    if not ttyd_binary:
        logger.error('ttyd executable not found. Please install ttyd or set ttyd_binary_path in settings.')
        return False

    # Get shell command from settings, fallback to zsh
    shell_cmd = settings.get('ttyd_command', 'zsh')

    allow_origin_value = settings.get('ttyd_allow_origin', '*')
    allow_origin_supported = ttyd_supports_allow_origin(settings)

    # Prepare ttyd command with proper settings
    cmd = [
        ttyd_binary,
        '-p', str(ttyd_port),
        '-W',  # Allow write access
        '-w', working_dir  # Set working directory
        # '-t', 'fontSize=14',
        # '-t', "fontFamily='Courier New',monospace",
        # '-t', 'theme={"background":"#1e1e1e","foreground":"#d4d4d4"}',
    ]

    if allow_origin_value and allow_origin_supported:
        cmd.extend(['--allow-origin', allow_origin_value])
        logger.debug("Using ttyd --allow-origin %s", allow_origin_value)
    elif allow_origin_value and not allow_origin_supported:
        logger.debug("ttyd binary does not support --allow-origin; skipping header override")

    cmd.append(shell_cmd)
    
    logger.info(f"Starting ttyd with command: {' '.join(cmd)}")
    logger.info(f"Working directory: {working_dir}")
    
    try:
        env = os.environ.copy()
        env['PATH'] = build_search_path()

        # Start ttyd process - exactly like manual command
        ttyd_process = subprocess.Popen(
            cmd,
            cwd=working_dir,
            start_new_session=True,  # Detach from parent process
            env=env
        )
        
        # Write PID to file
        with open(pid_file, 'w') as f:
            f.write(str(ttyd_process.pid))
        
        logger.info(f"ttyd started with PID {ttyd_process.pid} on port {ttyd_port}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to start ttyd: {e}")
        return False

def start_ttyd_with_command(working_dir, command):
    """Start ttyd with a specific command to execute"""
    global ttyd_process
    
    # First, ensure ttyd is installed
    if not is_ttyd_installed():
        logger.warning("ttyd is not installed. Skipping startup until user installs it.")
        return False
    
    # Stop any existing ttyd process (force stop)
    stop_ttyd(force=True)
    
    # Get settings
    settings = get_settings()
    ttyd_port = settings.get('ttyd_port', 7681)
    
    # Validate working directory
    if not os.path.exists(working_dir):
        logger.error(f"Working directory does not exist: {working_dir}")
        return False
    
    # Prepare ttyd command with the specific command to run
    # We'll wrap the command in a shell that will keep the terminal open
    wrapped_command = f'bash -c "echo Starting dataflow...; {command}; echo; echo Command finished. Press any key to continue...; read -n 1"'
    
    ttyd_binary = resolve_ttyd_binary(settings)
    if not ttyd_binary:
        logger.error('ttyd executable not found. Please install ttyd or set ttyd_binary_path in settings.')
        return False

    allow_origin_value = settings.get('ttyd_allow_origin', '*')
    allow_origin_supported = ttyd_supports_allow_origin(settings)

    cmd = [
        ttyd_binary,
        '-p', str(ttyd_port),
        '-W',  # Allow write access
        '-w', working_dir  # Set working directory
    ]

    if allow_origin_value and allow_origin_supported:
        cmd.extend(['--allow-origin', allow_origin_value])
        logger.debug("Using ttyd --allow-origin %s", allow_origin_value)
    elif allow_origin_value and not allow_origin_supported:
        logger.debug("ttyd binary does not support --allow-origin; skipping header override")

    cmd.extend(['bash', '-c', wrapped_command])
    
    logger.info(f"Starting ttyd with command: {' '.join(cmd)}")
    logger.info(f"Working directory: {working_dir}")
    logger.info(f"Executing: {command}")
    
    try:
        env = os.environ.copy()
        env['PATH'] = build_search_path()

        # Start ttyd process - exactly like manual command
        ttyd_process = subprocess.Popen(
            cmd,
            cwd=working_dir,
            start_new_session=True,
            env=env
        )
        
        # Write PID to file
        with open(pid_file, 'w') as f:
            f.write(str(ttyd_process.pid))
        
        logger.info(f"ttyd started with PID {ttyd_process.pid} on port {ttyd_port}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to start ttyd with command: {e}")
        return False

def restart_ttyd():
    """Restart the ttyd service"""
    stop_ttyd(force=True)
    return start_ttyd()

def get_ttyd_status():
    """Get the current status of the ttyd service"""
    pid = get_pid_from_file()
    
    if pid and is_process_running(pid):
        settings = get_settings()
        port = settings.get('ttyd_port', 7681)
        return {
            'status': 'running',
            'pid': pid,
            'port': port,
            'log_file': log_file
        }
    else:
        return {
            'status': 'stopped',
            'pid': None,
            'port': None,
            'log_file': log_file
        }

# No automatic cleanup - let ttyd run independently like old version
# Users can manually stop ttyd using the stop command or API

# Command-line interface for manual testing/control
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage ttyd service')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status', 'install'],
                        help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'start':
        start_ttyd()
    elif args.action == 'stop':
        stop_ttyd(force=True)
    elif args.action == 'restart':
        restart_ttyd()
    elif args.action == 'status':
        status = get_ttyd_status()
        print(f"ttyd status: {status['status']}")
        if status['pid']:
            print(f"PID: {status['pid']}")
            print(f"Port: {status['port']}")
    elif args.action == 'install':
        if is_ttyd_installed():
            print("ttyd is already installed.")
        else:
            print("Installing ttyd...")
            if install_ttyd():
                print("ttyd installed successfully!")
            else:
                print("Failed to install ttyd.") 
