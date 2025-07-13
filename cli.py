#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MoFA-Stage CLI工具
提供简单的命令行接口来管理MoFA-Stage服务
"""

import click
import os
import sys
import subprocess
import shutil
from pathlib import Path
try:
    from importlib.resources import files
except ImportError:
    # Fallback for Python < 3.9
    import pkg_resources

@click.group()
@click.version_option()
def main():
    """MoFA-Stage - Web-based development tool for MoFA framework"""
    pass

@main.command()
@click.option('--path', default='.', help='Installation path (default: current directory)')
@click.option('--force', is_flag=True, help='Force overwrite existing files')
def init(path, force):
    """Initialize MoFA-Stage project"""
    target_path = Path(path).resolve()
    
    if target_path.exists() and any(target_path.iterdir()) and not force:
        click.echo(f"❌ Directory {target_path} is not empty, use --force to overwrite")
        return
    
    click.echo(f"🚀 Initializing MoFA-Stage project at: {target_path}")
    
    try:
        # 获取包数据路径 (Python 3.9+)
        try:
            package_files = files('mofa_stage')
            package_path = str(package_files)
        except NameError:
            # Fallback for older Python versions
            package_path = pkg_resources.resource_filename('mofa_stage', '')
        
        # 复制文件
        for item in ['backend', 'frontend', 'install', 'run', 'README.md', 'README_cn.md']:
            src = os.path.join(package_path, item)
            dst = target_path / item
            
            if os.path.exists(src):
                if os.path.isdir(src):
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                    # 给脚本添加执行权限
                    if item in ['install', 'run']:
                        os.chmod(dst, 0o755)
                        
        click.echo("✅ Project initialized successfully!")
        click.echo("\n🔧 Next steps:")
        click.echo(f"   cd {target_path}")
        click.echo("   mofa-stage install  # Install dependencies")
        click.echo("   mofa-stage start    # Start services")
        
    except Exception as e:
        click.echo(f"❌ Initialization failed: {e}")
        sys.exit(1)

@main.command()
@click.option('--mode', type=click.Choice(['local', 'docker']), help='Installation mode')
def install(mode):
    """Install MoFA-Stage dependencies"""
    install_script = Path('./install')
    
    if not install_script.exists():
        click.echo("❌ Install script not found, ensure you're in MoFA-Stage project directory")
        click.echo("   or run 'mofa-stage init' to initialize project")
        return
    
    click.echo("🔧 Installing dependencies...")
    
    # 设置环境变量传递给install脚本
    env = os.environ.copy()
    if mode:
        env['MOFA_INSTALL_MODE'] = 'docker' if mode == 'docker' else 'local'
    
    try:
        # 直接调用install脚本，保持交互性
        subprocess.run(['bash', str(install_script)], env=env, check=True)
        click.echo("✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Installation failed: {e}")
        sys.exit(1)

@main.command()
@click.option('--mode', type=click.Choice(['local', 'docker']), help='Run mode')
@click.option('--lang', type=click.Choice(['zh', 'en']), help='Language setting')
def start(mode, lang):
    """Start MoFA-Stage services"""
    run_script = Path('./run')
    
    if not run_script.exists():
        click.echo("❌ Run script not found, ensure you're in MoFA-Stage project directory")
        click.echo("   or run 'mofa-stage init' to initialize project")
        return
    
    click.echo("🚀 Starting MoFA-Stage services...")
    
    # 设置环境变量传递给run脚本
    env = os.environ.copy()
    if mode:
        env['MOFA_RUN_MODE'] = 'docker' if mode == 'docker' else 'local'
    if lang:
        env['MOFA_LANG'] = '1' if lang == 'zh' else '2'
    
    try:
        # 直接调用run脚本，保持交互性
        subprocess.run(['bash', str(run_script)], env=env, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Startup failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n👋 Services stopped")

@main.command()
def status():
    """Check MoFA-Stage service status"""
    import requests
    
    services = [
        ('Backend API', 'http://localhost:5002/api/system/info'),
        ('Frontend', 'http://localhost:3000'),
        ('WebSSH', 'http://localhost:5001'),
        ('ttyd', 'http://localhost:7681'),
    ]
    
    click.echo("🔍 Checking service status:")
    
    for name, url in services:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                click.echo(f"  ✅ {name}: Running")
            else:
                click.echo(f"  ❌ {name}: Error (status code: {response.status_code})")
        except requests.exceptions.RequestException:
            click.echo(f"  ❌ {name}: Not running")

@main.command()
def stop():
    """Stop MoFA-Stage services"""
    import psutil
    
    ports = [3000, 5001, 5002, 7681]
    stopped = []
    
    for port in ports:
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.info['connections'] or []:
                    if conn.laddr.port == port:
                        proc.terminate()
                        stopped.append(port)
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    if stopped:
        click.echo(f"✅ Stopped services on ports: {', '.join(map(str, stopped))}")
    else:
        click.echo("ℹ️  No running services found")

if __name__ == '__main__':
    main()