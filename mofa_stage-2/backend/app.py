"""
MoFA_Stage Flask 后端应用
"""
from flask import Flask, jsonify
from flask_cors import CORS
import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 引入路由
from routes.agents import agents_bp
from routes.settings import settings_bp
from routes.terminal import terminal_bp
from routes.webssh import webssh_bp, init_websocket
from routes.ttyd import ttyd_bp
from routes.mermaid import mermaid_bp
from routes.vscode import vscode_bp
from utils.ttyd_manager import start_ttyd, get_ttyd_status, is_ttyd_installed

def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__)
    
    # 配置应用
    app.config.from_pyfile('config.py')
    
    # 启用 CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # 注册蓝图
    app.register_blueprint(agents_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(terminal_bp)
    app.register_blueprint(webssh_bp)
    app.register_blueprint(ttyd_bp, url_prefix='/api/ttyd')
    app.register_blueprint(mermaid_bp)
    app.register_blueprint(vscode_bp)
    
    # 初始化WebSocket
    init_websocket(app)
    
    # 添加系统信息路由
    @app.route('/api/system/info', methods=['GET'])
    def get_system_info():
        """获取系统信息，包括正确的 shell 环境"""
        import platform
        import subprocess
        import getpass
        import socket
        
        try:
            # 获取基本系统信息
            system = platform.system()
            release = platform.release()
            machine = platform.machine()
            
            # 获取用户和主机名
            try:
                username = getpass.getuser()
                hostname = socket.gethostname()
            except Exception:
                username = "user"
                hostname = "localhost"
            
            # 获取当前用户的默认 shell
            current_shell = "bash"  # 默认值
            try:
                # 在 Unix 系统上获取用户的默认 shell
                if system in ['Linux', 'Darwin']:
                    # 方法1：通过 $SHELL 环境变量
                    shell_env = os.environ.get('SHELL', '')
                    if shell_env:
                        current_shell = os.path.basename(shell_env)
                    else:
                        # 方法2：通过 /etc/passwd 文件
                        try:
                            import pwd
                            user_info = pwd.getpwnam(username)
                            current_shell = os.path.basename(user_info.pw_shell)
                        except Exception:
                            # 方法3：通过 dscl 命令 (macOS)
                            if system == 'Darwin':
                                try:
                                    result = subprocess.run(['dscl', '.', 'read', f'/Users/{username}', 'UserShell'], 
                                                          capture_output=True, text=True)
                                    if result.returncode == 0:
                                        shell_line = result.stdout.strip()
                                        if 'UserShell:' in shell_line:
                                            shell_path = shell_line.split('UserShell:')[1].strip()
                                            current_shell = os.path.basename(shell_path)
                                except Exception:
                                    pass
                elif system == 'Windows':
                    current_shell = "cmd"  # Windows 默认使用 cmd
            except Exception as e:
                app.logger.warning(f"Failed to detect shell: {e}")
            
            # 构建平台信息字符串
            platform_info = f"{system} {release} ({machine})"
            
            # 添加更详细的信息
            if system == "Windows":
                platform_info += " - For Windows users, we recommend using WSL for better compatibility"
            elif system == "Linux":
                # 检查是否在 WSL 中运行
                if os.path.exists('/proc/version'):
                    try:
                        with open('/proc/version', 'r') as f:
                            if 'microsoft' in f.read().lower():
                                platform_info += " (Running in Windows Subsystem for Linux)"
                    except Exception:
                        pass
            elif system == "Darwin":
                platform_info += " (macOS)"
            
            # 构建完整的环境信息
            shell_info = f"Default Shell: {current_shell}"
            env_info = f"{username}@{hostname} | {shell_info}"
            
            return jsonify({
                "success": True,
                "platform_info": f"{platform_info} | {env_info}",
                "system_info": {
                    "username": username,
                    "hostname": hostname,
                    "platform": system,
                    "release": release,
                    "machine": machine,
                    "shell": current_shell
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error getting system info: {e}")
            return jsonify({
                "success": False,
                "platform_info": "Error fetching system information",
                "error": str(e)
            }), 500
    
    # 检查并启动ttyd服务
    try:
        # Check if ttyd is installed
        if not is_ttyd_installed():
            app.logger.warning("ttyd is not installed. It will be installed automatically when needed.")
        
        # Check the current status
        status = get_ttyd_status()
        if status['status'] == 'stopped':
            app.logger.info("Starting ttyd service...")
            start_ttyd()
        else:
            app.logger.info(f"ttyd service is already running on PID {status['pid']}")
    except Exception as e:
        app.logger.error(f"Error initializing ttyd service: {e}")
    
    # 主页路由
    @app.route('/')
    def index():
        return jsonify({"message": "MoFA_Stage API", "status": "running"})
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "message": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"success": False, "message": "Internal server error"}), 500
    
    return app

if __name__ == '__main__':
    import argparse
    import threading
    from flask import Flask
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='MoFA_Stage Backend Server')
    parser.add_argument('--port', type=int, default=5002, help='Port to run the server on')
    args = parser.parse_args()
    
    # 创建主应用
    app = create_app()
    
    # 创建WebSSH应用 (端口5001)
    webssh_app = Flask(__name__)
    webssh_app.config.from_pyfile('config.py')
    # 为WebSSH应用注册所有必要的蓝图以处理请求
    CORS(webssh_app, resources={r"/api/*": {"origins": "*"}})
    webssh_app.register_blueprint(settings_bp)
    webssh_app.register_blueprint(terminal_bp)
    webssh_app.register_blueprint(agents_bp)
    webssh_app.register_blueprint(webssh_bp)
    webssh_app.register_blueprint(ttyd_bp, url_prefix='/api/ttyd')
    webssh_app.register_blueprint(mermaid_bp)
    webssh_app.register_blueprint(vscode_bp)
    init_websocket(webssh_app)
    
    # 为 WebSSH 应用也添加系统信息路由
    @webssh_app.route('/api/system/info', methods=['GET'])
    def get_system_info_webssh():
        """获取系统信息，包括正确的 shell 环境 (WebSSH 应用)"""
        import platform
        import subprocess
        import getpass
        import socket
        
        try:
            # 获取基本系统信息
            system = platform.system()
            release = platform.release()
            machine = platform.machine()
            
            # 获取用户和主机名
            try:
                username = getpass.getuser()
                hostname = socket.gethostname()
            except Exception:
                username = "user"
                hostname = "localhost"
            
            # 获取当前用户的默认 shell
            current_shell = "bash"  # 默认值
            try:
                # 在 Unix 系统上获取用户的默认 shell
                if system in ['Linux', 'Darwin']:
                    # 方法1：通过 $SHELL 环境变量
                    shell_env = os.environ.get('SHELL', '')
                    if shell_env:
                        current_shell = os.path.basename(shell_env)
                    else:
                        # 方法2：通过 /etc/passwd 文件
                        try:
                            import pwd
                            user_info = pwd.getpwnam(username)
                            current_shell = os.path.basename(user_info.pw_shell)
                        except Exception:
                            # 方法3：通过 dscl 命令 (macOS)
                            if system == 'Darwin':
                                try:
                                    result = subprocess.run(['dscl', '.', 'read', f'/Users/{username}', 'UserShell'], 
                                                          capture_output=True, text=True)
                                    if result.returncode == 0:
                                        shell_line = result.stdout.strip()
                                        if 'UserShell:' in shell_line:
                                            shell_path = shell_line.split('UserShell:')[1].strip()
                                            current_shell = os.path.basename(shell_path)
                                except Exception:
                                    pass
                elif system == 'Windows':
                    current_shell = "cmd"  # Windows 默认使用 cmd
            except Exception as e:
                webssh_app.logger.warning(f"Failed to detect shell: {e}")
            
            # 构建平台信息字符串
            platform_info = f"{system} {release} ({machine})"
            
            # 添加更详细的信息
            if system == "Windows":
                platform_info += " - For Windows users, we recommend using WSL for better compatibility"
            elif system == "Linux":
                # 检查是否在 WSL 中运行
                if os.path.exists('/proc/version'):
                    try:
                        with open('/proc/version', 'r') as f:
                            if 'microsoft' in f.read().lower():
                                platform_info += " (Running in Windows Subsystem for Linux)"
                    except Exception:
                        pass
            elif system == "Darwin":
                platform_info += " (macOS)"
            
            # 构建完整的环境信息
            shell_info = f"Default Shell: {current_shell}"
            env_info = f"{username}@{hostname} | {shell_info}"
            
            return jsonify({
                "success": True,
                "platform_info": f"{platform_info} | {env_info}",
                "system_info": {
                    "username": username,
                    "hostname": hostname,
                    "platform": system,
                    "release": release,
                    "machine": machine,
                    "shell": current_shell
                }
            })
            
        except Exception as e:
            webssh_app.logger.error(f"Error getting system info: {e}")
            return jsonify({
                "success": False,
                "platform_info": "Error fetching system information",
                "error": str(e)
            }), 500
    
    # 添加错误处理
    @webssh_app.errorhandler(404)
    def not_found_webssh(error):
        return jsonify({"success": False, "message": "Endpoint not found"}), 404
    
    @webssh_app.errorhandler(500)
    def internal_error_webssh(error):
        return jsonify({"success": False, "message": "Internal server error"}), 500
    
    # 启动WebSSH服务器线程
    def run_webssh_server():
        webssh_app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
    
    webssh_thread = threading.Thread(target=run_webssh_server)
    webssh_thread.daemon = True
    webssh_thread.start()
    
    # 启动主应用
    app.run(host='0.0.0.0', port=args.port, debug=True, use_reloader=False)
