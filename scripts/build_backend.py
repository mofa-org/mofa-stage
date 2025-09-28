#!/usr/bin/env python3
"""
Python后端打包脚本
使用PyInstaller将Flask应用打包为可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# 设置UTF-8编码，避免Windows编码问题
if sys.platform.startswith('win'):
    import locale
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

def main():
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    backend_dir = project_root / "backend"
    dist_dir = backend_dir / "dist"
    
    print("Starting Python backend packaging...")
    
    # 确保backend目录存在
    if not backend_dir.exists():
        print("Error: backend directory not found")
        sys.exit(1)
    
    # 检查app.py是否存在
    app_py = backend_dir / "app.py"
    if not app_py.exists():
        print("Error: app.py file not found")
        sys.exit(1)
    
    # 清理之前的构建
    if dist_dir.exists():
        print("Cleaning previous build...")
        shutil.rmtree(dist_dir)
    
    # 创建dist目录
    dist_dir.mkdir(exist_ok=True)
    
    # 构建PyInstaller命令
    cmd = [
        "pyinstaller",
        "--onefile",                    # 打包为单个文件
        "--name=app",                   # 可执行文件名
        "--distpath", str(dist_dir),    # 输出目录
        "--workpath", str(backend_dir / "build"),  # 工作目录
        "--specpath", str(backend_dir), # spec文件目录
        "--clean",                      # 清理缓存
        "--noconfirm",                  # 不询问覆盖
        # 隐藏导入的模块
        "--hidden-import=paramiko",
        "--hidden-import=flask_cors",
        "--hidden-import=flask_sock",
        "--hidden-import=webssh",
        "--hidden-import=psutil",
        "--hidden-import=duckdb",
        # 添加数据文件
        "--add-data", f"{backend_dir}/config.py:.",
        "--add-data", f"{backend_dir}/routes:routes",
        "--add-data", f"{backend_dir}/utils:utils",
        str(app_py)
    ]
    
    try:
        print("Executing PyInstaller packaging...")
        print(f"Command: {' '.join(cmd)}")
        
        # 在backend目录下执行命令
        result = subprocess.run(
            cmd, 
            cwd=backend_dir,
            check=True, 
            capture_output=True, 
            text=True
        )
        
        print("Packaging successful!")
        
        # 检查生成的文件
        if sys.platform == "win32":
            executable = dist_dir / "app.exe"
        else:
            executable = dist_dir / "app"
            
        if executable.exists():
            file_size = executable.stat().st_size / (1024 * 1024)  # MB
            print(f"Generated executable: {executable}")
            print(f"File size: {file_size:.1f} MB")
        else:
            print("Warning: Generated executable not found")
            
    except subprocess.CalledProcessError as e:
        print(f"Packaging failed: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: pyinstaller not found. Please install: pip install pyinstaller")
        sys.exit(1)
    
    # 清理临时文件
    build_dir = backend_dir / "build"
    spec_file = backend_dir / "app.spec"
    
    if build_dir.exists():
        print("Cleaning temporary files...")
        shutil.rmtree(build_dir, ignore_errors=True)
    
    if spec_file.exists():
        spec_file.unlink()
    
    print("Backend packaging completed!")

if __name__ == "__main__":
    main()