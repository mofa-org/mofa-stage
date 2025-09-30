from flask import Blueprint, jsonify, request, Response
import os
import sys
import logging
import requests
from werkzeug.exceptions import BadRequest

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ttyd_manager import (
    start_ttyd, stop_ttyd, restart_ttyd, get_ttyd_status, is_ttyd_installed, install_ttyd, start_ttyd_with_command
)

# Configure logging
logger = logging.getLogger('ttyd_routes')

ttyd_bp = Blueprint('ttyd', __name__)

@ttyd_bp.route('/status', methods=['GET'])
def status():
    """Get the current status of the ttyd service"""
    status = get_ttyd_status()
    
    # Add installation status
    status['installed'] = is_ttyd_installed()
    
    return jsonify(status)

@ttyd_bp.route('/start', methods=['POST'])
def start():
    """Start the ttyd service"""
    result = start_ttyd()
    
    if result:
        status = get_ttyd_status()
        return jsonify({
            'success': True,
            'message': 'ttyd service started successfully',
            'status': status
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to start ttyd service'
        }), 500

@ttyd_bp.route('/stop', methods=['POST'])
def stop():
    """Stop the ttyd service"""
    stop_ttyd()
    
    status = get_ttyd_status()
    return jsonify({
        'success': True,
        'message': 'ttyd service stopped successfully',
        'status': status
    })

@ttyd_bp.route('/restart', methods=['POST'])
def restart():
    """Restart the ttyd service"""
    result = restart_ttyd()
    
    if result:
        status = get_ttyd_status()
        return jsonify({
            'success': True,
            'message': 'ttyd service restarted successfully',
            'status': status
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to restart ttyd service'
        }), 500

@ttyd_bp.route('/start-with-command', methods=['POST'])
def start_with_command():
    """Start ttyd with a specific command to execute"""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'Request body must be JSON'
        }), 400
    
    working_dir = data.get('working_dir')
    command = data.get('command')
    
    if not working_dir or not command:
        return jsonify({
            'success': False,
            'message': 'working_dir and command are required'
        }), 400
    
    result = start_ttyd_with_command(working_dir, command)
    
    if result:
        status = get_ttyd_status()
        return jsonify({
            'success': True,
            'message': 'ttyd started with command successfully',
            'status': status
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to start ttyd with command'
        }), 500

@ttyd_bp.route('/install', methods=['POST'])
def install():
    """Install ttyd if not already installed"""
    if is_ttyd_installed():
        return jsonify({
            'success': True,
            'message': 'ttyd is already installed',
            'installed': True
        })
    
    result = install_ttyd()
    
    if result:
        return jsonify({
            'success': True,
            'message': 'ttyd installed successfully',
            'installed': True
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to install ttyd',
            'installed': False
        }), 500

@ttyd_bp.route('/proxy', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
@ttyd_bp.route('/proxy/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def proxy(path=''):
    """Proxy requests to ttyd service to avoid CORS issues in Electron"""
    # Handle WebSocket upgrade requests
    if request.headers.get('Upgrade', '').lower() == 'websocket':
        return jsonify({
            'success': False,
            'message': 'WebSocket connections need direct access to ttyd',
            'redirect_url': f'ws://localhost:7681/{path}' if path else 'ws://localhost:7681'
        }), 400
    
    # Get ttyd port from status or settings
    try:
        status = get_ttyd_status()
        ttyd_port = status.get('port')
        if not ttyd_port:
            # Fallback to default port from settings
            from .settings import get_settings
            settings = get_settings()
            ttyd_port = settings.get('ttyd_port', 7681)
    except Exception:
        # Fallback to default port
        ttyd_port = 7681
    
    # Build the target URL
    target_url = f'http://localhost:{ttyd_port}'
    if path:
        target_url = f'{target_url}/{path}'
    
    # Forward query parameters
    if request.query_string:
        target_url = f'{target_url}?{request.query_string.decode()}'
    
    try:
        # Forward the request with the same method
        method = request.method.lower()
        headers = dict(request.headers)
        
        # Remove host header to avoid conflicts
        headers.pop('Host', None)
        
        if method == 'get':
            resp = requests.get(target_url, headers=headers, stream=True, timeout=30)
        elif method == 'post':
            resp = requests.post(target_url, data=request.data, headers=headers, stream=True, timeout=30)
        elif method == 'put':
            resp = requests.put(target_url, data=request.data, headers=headers, stream=True, timeout=30)
        elif method == 'delete':
            resp = requests.delete(target_url, headers=headers, stream=True, timeout=30)
        else:  # OPTIONS
            resp = requests.options(target_url, headers=headers, timeout=30)
        
        # Create response
        response = Response(
            resp.content,
            status=resp.status_code,
            headers=dict(resp.headers)
        )
        
        # Remove problematic headers that might cause issues in Electron
        response.headers.pop('transfer-encoding', None)
        response.headers.pop('content-encoding', None)
        
        # Add CORS headers for Electron
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
        
    except requests.exceptions.RequestException as e:
        logger.error(f'Failed to proxy ttyd request: {e}')
        return jsonify({
            'success': False,
            'message': 'Failed to connect to ttyd service',
            'error': str(e)
        }), 503 