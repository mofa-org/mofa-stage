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

def main():
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    backend_dir = project_root / "backend"
    dist_dir = backend_dir / "dist"
    
    print("🚀 开始打包Python后端...")
    
    # 确保backend目录存在
    if not backend_dir.exists():
        print("❌ 错误：backend目录不存在")
        sys.exit(1)
    
    # 检查app.py是否存在
    app_py = backend_dir / "app.py"
    if not app_py.exists():
        print("❌ 错误：app.py文件不存在")
        sys.exit(1)
    
    # 清理之前的构建
    if dist_dir.exists():
        print("🧹 清理之前的构建...")
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
        print("📦 执行PyInstaller打包...")
        print(f"命令: {' '.join(cmd)}")
        
        # 在backend目录下执行命令
        result = subprocess.run(
            cmd, 
            cwd=backend_dir,
            check=True, 
            capture_output=True, 
            text=True
        )
        
        print("✅ 打包成功！")
        
        # 检查生成的文件
        if sys.platform == "win32":
            executable = dist_dir / "app.exe"
        else:
            executable = dist_dir / "app"
            
        if executable.exists():
            file_size = executable.stat().st_size / (1024 * 1024)  # MB
            print(f"📁 生成的可执行文件：{executable}")
            print(f"📏 文件大小：{file_size:.1f} MB")
        else:
            print("⚠️  警告：未找到生成的可执行文件")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 打包失败：{e}")
        print(f"错误输出：{e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ 错误：未找到pyinstaller。请安装：pip install pyinstaller")
        sys.exit(1)
    
    # 清理临时文件
    build_dir = backend_dir / "build"
    spec_file = backend_dir / "app.spec"
    
    if build_dir.exists():
        print("🧹 清理临时文件...")
        shutil.rmtree(build_dir, ignore_errors=True)
    
    if spec_file.exists():
        spec_file.unlink()
    
    print("🎉 后端打包完成！")

if __name__ == "__main__":
    main()