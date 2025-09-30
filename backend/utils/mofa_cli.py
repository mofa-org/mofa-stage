"""
封装对 MoFA CLI 命令的调用
"""
import os
import subprocess
import json
import shutil
import time
from pathlib import Path
import sys
import re
import ast
import datetime
from itertools import islice

import requests
import toml
import yaml

from utils.node_index import NodeKnowledgeIndex

class MofaCLI:
    def __init__(self, settings=None):
        import sys
        import os
        # 添加项目根目录到 Python 路径
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config import (
            DEFAULT_MOFA_ENV, DEFAULT_MOFA_DIR, USE_SYSTEM_MOFA,
            DEFAULT_AGENT_HUB_PATH, DEFAULT_EXAMPLES_PATH,
            CUSTOM_AGENT_HUB_PATH, CUSTOM_EXAMPLES_PATH,
            AGENT_HUB_PATH, EXAMPLES_PATH,
            DEFAULT_MOFA_MODE, DEFAULT_DOCKER_CONTAINER
        )
        
        self.settings = settings or {}
        self.mofa_env_path = self.settings.get('mofa_env_path', DEFAULT_MOFA_ENV)
        # 先取 mofa_mode，之后才能根据它设置 mofa_dir 默认值
        self.mofa_mode = self.settings.get('mofa_mode', DEFAULT_MOFA_MODE)
        self.mofa_dir = self.settings.get('mofa_dir', DEFAULT_MOFA_DIR)
        if self.mofa_mode == 'docker' and not self.mofa_dir:
            # 默认容器内MoFA根目录
            self.mofa_dir = "/app/mofa"
        
        # 兼容旧字段 use_system_mofa（布尔）
        if 'use_system_mofa' in self.settings:
            legacy_system = self.settings.get('use_system_mofa', USE_SYSTEM_MOFA)
            if self.mofa_mode == DEFAULT_MOFA_MODE and legacy_system is not None:
                # 如果用户只设置了旧字段，则推断 mode
                self.mofa_mode = 'system' if legacy_system else 'venv'

        self.use_system_mofa = True if self.mofa_mode == 'system' else False
        # docker模式时，也把use_system_mofa设为True 以复用原有系统分支，但后续会替换 mofa_cmd
        if self.mofa_mode == 'docker':
            self.use_system_mofa = True
        
        # 设置原子化Agent（agent-hub）存储路径
        use_default_agent_hub = self.settings.get('use_default_agent_hub_path', True)
        if use_default_agent_hub:
            # 如果使用默认路径，应该是mofa_dir/python/agent-hub
            self.agent_hub_dir = os.path.join(self.mofa_dir, AGENT_HUB_PATH)
        else:
            custom_agent_hub = self.settings.get('custom_agent_hub_path', '')
            self.agent_hub_dir = custom_agent_hub if custom_agent_hub else DEFAULT_AGENT_HUB_PATH
        
        # 设置示例组合（examples）存储路径
        use_default_examples = self.settings.get('use_default_examples_path', True)
        if use_default_examples:
            # 如果使用默认路径，应该是mofa_dir/python/examples
            self.examples_dir = os.path.join(self.mofa_dir, EXAMPLES_PATH)
        else:
            custom_examples = self.settings.get('custom_examples_path', '')
            self.examples_dir = custom_examples if custom_examples else DEFAULT_EXAMPLES_PATH
            
        if self.mofa_mode != 'docker':
            try:
                agent_hub_parent = os.path.dirname(self.agent_hub_dir)
                examples_parent = os.path.dirname(self.examples_dir)
                if use_default_agent_hub or use_default_examples:
                    python_dir = os.path.join(self.mofa_dir, 'python')
                    if not os.path.exists(python_dir):
                        os.makedirs(python_dir, exist_ok=True)

                if os.path.exists(agent_hub_parent):
                    os.makedirs(self.agent_hub_dir, exist_ok=True)
                else:
                    print(f"Warning: Parent directory for agent_hub_dir does not exist: {agent_hub_parent}")
                    self.agent_hub_dir = os.path.join(os.path.dirname(__file__), '../temp/agent-hub')
                    os.makedirs(self.agent_hub_dir, exist_ok=True)

                if os.path.exists(examples_parent):
                    os.makedirs(self.examples_dir, exist_ok=True)
                else:
                    print(f"Warning: Parent directory for examples_dir does not exist: {examples_parent}")
                    self.examples_dir = os.path.join(os.path.dirname(__file__), '../temp/examples')
                    os.makedirs(self.examples_dir, exist_ok=True)
            except Exception as e:
                print(f"Error creating directories: {e}")
                temp_dir = os.path.join(os.path.dirname(__file__), '../temp')
                os.makedirs(temp_dir, exist_ok=True)
                self.agent_hub_dir = os.path.join(temp_dir, 'agent-hub')
                self.examples_dir = os.path.join(temp_dir, 'examples')
                os.makedirs(self.agent_hub_dir, exist_ok=True)
                os.makedirs(self.examples_dir, exist_ok=True)
        
        # 存储正在运行的进程信息
        self._running_processes = {}

        # 节点索引缓存
        self._node_index = NodeKnowledgeIndex()
        self._cached_nodes = []
        
        # 分别存储hub和example类型的额外目录
        self.additional_hub_dirs = []
        self.additional_example_dirs = []
        
        # 添加设置中的额外hub目录
        additional_hub_dirs = self.settings.get('additional_hub_dirs', [])
        for additional_dir in additional_hub_dirs:
            if additional_dir and os.path.exists(additional_dir):
                self.additional_hub_dirs.append(additional_dir)
        
        # 添加设置中的额外example目录
        additional_example_dirs = self.settings.get('additional_example_dirs', [])
        for additional_dir in additional_example_dirs:
            if additional_dir and os.path.exists(additional_dir):
                self.additional_example_dirs.append(additional_dir)
        
        # 合并所有扫描目录
        self.all_scan_dirs = [
            self.agent_hub_dir,
            self.examples_dir,
        ] + self.additional_hub_dirs + self.additional_example_dirs
        
        # 过滤掉None值和重复项
        self.all_scan_dirs = list(set([d for d in self.all_scan_dirs if d is not None]))
        
        # Agent位置缓存 - 记录每个agent的实际路径
        self.agent_location_cache = {}  # agent_name -> 实际完整路径的映射
        
        # 原有的目录定义，保持兼容性
        self.agent_dirs = [self.agent_hub_dir]  # agent-hub目录
        self.example_dirs = [self.examples_dir]  # examples目录
        
        # 兼容旧版本的代码，保留agents_dir和possible_agent_dirs属性
        self.agents_dir = self.agent_hub_dir
        self.possible_agent_dirs = [self.agent_hub_dir, self.examples_dir]
        
        # 根据运行模式设置命令
        if self.mofa_mode == 'system':
            self.mofa_cmd = "mofa"
            self.activate_cmd = ""
        elif self.mofa_mode == 'venv':
            self.activate_cmd = f"source {self.mofa_env_path}/bin/activate"
            self.mofa_cmd = "mofa"
        elif self.mofa_mode == 'docker':
            # Docker执行：docker exec -i -w <workdir> <container> mofa
            self.docker_container = self.settings.get('docker_container_name', DEFAULT_DOCKER_CONTAINER)
            if not self.docker_container:
                print("警告: docker模式但未指定container name, 将使用'mofa'")
                self.docker_container = 'mofa'
            # 使用双引号包裹工作目录，避免空格问题
            workdir_flag = f"-w \"{self.mofa_dir}\"" if self.mofa_dir else ""
            self.mofa_cmd = f"docker exec -i {workdir_flag} {self.docker_container} mofa"
            self.activate_cmd = ""
            
        if not os.path.exists(self.mofa_dir):
            print(f"警告: 指定的MoFA目录不存在: {self.mofa_dir}")
            
        # 检查mofa命令是否可用
        if self.mofa_mode == 'system':
            if not shutil.which("mofa"):
                print("警告: 系统中找不到mofa命令，请确保已安装")
    
    def _run_command(self, command, cwd=None):
        """运行shell命令并返回输出"""
        # 替换命令中的mofa为正确的命令
        command = command.replace("mofa", self.mofa_cmd)
        
        # docker模式直接执行并返回，避免进入后续system/venv逻辑
        if self.mofa_mode == 'docker':
            try:
                print(f"使用 Docker 执行: {command}")
                result = subprocess.run(
                    command,
                    shell=True,
                    executable="/bin/bash",
                    check=False,
                    text=True,
                    capture_output=True,
                    cwd=None  # 不指定cwd，避免本地主机路径不存在
                )
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    print(f"docker exec 命令失败，返回码: {result.returncode}")
                    print(f"错误输出: {result.stderr}")
                    return ""
            except Exception as e:
                print(f"执行docker命令时出错: {e}")
                return ""
        
        try:
            # 使用系统安装的MOFA
            if self.use_system_mofa:
                print(f"使用系统MOFA执行: {command}")
                result = subprocess.run(
                    command,
                    shell=True,
                    executable="/bin/bash",
                    check=False,
                    text=True,
                    capture_output=True,
                    cwd=cwd if cwd else (self.mofa_dir if self.mofa_dir else None)
                )
                
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    print(f"系统命令执行失败，返回码: {result.returncode}")
                    print(f"错误输出: {result.stderr}")
            
            # 如果使用虚拟环境或者系统命令失败，尝试虚拟环境方式
            if not self.use_system_mofa or result.returncode != 0:
                # 方法1: 使用bash执行source命令
                full_cmd = f"{self.activate_cmd} && {command}" if self.activate_cmd else command
                print(f"执行虚拟环境命令: {full_cmd}")
                
                venv_result = subprocess.run(
                    full_cmd,
                    shell=True,
                    executable="/bin/bash",  # 明确使用bash而不是sh
                    check=False,
                    text=True,
                    capture_output=True,
                    cwd=cwd if cwd else (self.mofa_dir if self.mofa_dir else None)
                )
                
                if venv_result.returncode == 0:
                    return venv_result.stdout.strip()
                else:
                    print(f"虚拟环境命令执行失败，返回码: {venv_result.returncode}")
                    print(f"错误输出: {venv_result.stderr}")
                    
                    # 方法2: 直接使用虚拟环境中的Python解释器
                    python_executable = os.path.join(self.mofa_env_path, "bin", "python")
                    if os.path.exists(python_executable):
                        mofa_mod_cmd = command.replace(self.mofa_cmd, "-m mofa.cli")
                        alt_cmd = f"{python_executable} {mofa_mod_cmd}"
                        print(f"执行替代命令: {alt_cmd}")
                        
                        py_result = subprocess.run(
                            alt_cmd,
                            shell=True,
                            check=False,
                            text=True, 
                            capture_output=True,
                            cwd=cwd if cwd else (self.mofa_dir if self.mofa_dir else None)
                        )
                        
                        if py_result.returncode == 0:
                            return py_result.stdout.strip()
                        else:
                            print(f"替代命令也失败了，返回码: {py_result.returncode}")
                            print(f"错误输出: {py_result.stderr}")
            
            # 所有方法都失败，返回空字符串
            print("所有方法都失败，将尝试使用文件系统操作")
            return ""
        except Exception as e:
            print(f"执行命令时出错: {e}")
            return ""
    
    def list_agents(self):
        """获取所有 agent 列表，分别从 agent-hub 和 examples 目录扫描"""
        try:
            # Docker 模式：直接列举容器内目录并返回，跳过宿主机扫描
            if self.mofa_mode == 'docker':
                hub_agents_list = sorted(self._docker_ls(self.agent_hub_dir))
                example_agents_list = sorted(self._docker_ls(self.examples_dir))
                return {
                    "hub_agents": hub_agents_list,
                    "example_agents": example_agents_list
                }

            # 非 docker 模式继续原有流程
            print(f"Current agent_hub_dir = {self.agent_hub_dir}")
            print(f"Current examples_dir = {self.examples_dir}")
            print(f"Current settings: use_system_mofa = {self.use_system_mofa}, mofa_dir = {self.mofa_dir}")
            
            # 创建两个集合分别存储不同来源的agents
            hub_agents = set()  # agent-hub目录的agents（原子化单位）
            example_agents = set()  # examples目录的agents
            cli_success = False
            
            # 1. 先尝试使用 mofa CLI 命令，但不直接使用结果，因为我们需要知道每个agent的来源
            try:
                output = self._run_command("mofa agent-list")
                if output:
                    for line in output.split("\n"):
                        if line.startswith("[") and line.endswith("]"):
                            agents_text = line.strip("[]").replace("'", "").replace(" ", "")
                            cli_agents = [agent for agent in agents_text.split(",") if agent]
                            cli_success = True
                            print(f"CLI 命令成功获取到 {len(cli_agents)} 个 agents: {cli_agents}")
                            break
            except Exception as cli_err:
                print(f"CLI 命令出错: {cli_err}")
            
            # 2. 扫描所有配置的目录并构建位置缓存
            print(f"开始扫描所有目录: {self.all_scan_dirs}")
            self.agent_location_cache.clear()  # 清空缓存，重新构建
            
            for scan_dir in self.all_scan_dirs:
                if os.path.exists(scan_dir) and os.path.isdir(scan_dir):
                    try:
                        print(f"扫描目录: {scan_dir}")
                        for item in os.listdir(scan_dir):
                            item_path = os.path.join(scan_dir, item)
                            if os.path.isdir(item_path) and not item.startswith('.'):
                                # 记录agent的实际位置
                                self.agent_location_cache[item] = item_path
                                
                                # 根据目录位置分类到不同集合
                                if scan_dir == self.agent_hub_dir:
                                    hub_agents.add(item)
                                elif scan_dir == self.examples_dir:
                                    example_agents.add(item)
                                else:
                                    # 其他目录的agent，根据配置分类
                                    if scan_dir in self.additional_hub_dirs:
                                        hub_agents.add(item)
                                    elif scan_dir in self.additional_example_dirs:
                                        example_agents.add(item)
                                    else:
                                        # 默认归类为hub_agents
                                        hub_agents.add(item)
                                    
                        print(f"从 {scan_dir} 目录读取到 {len(os.listdir(scan_dir) if os.path.exists(scan_dir) else 0)} 项")
                    except Exception as dir_err:
                        print(f"读取目录 {scan_dir} 时出错: {dir_err}")
                else:
                    print(f"目录不存在或无法访问: {scan_dir}")
            
            print(f"构建完成位置缓存，共 {len(self.agent_location_cache)} 个agent")
            print(f"agent-hub类型: {len(hub_agents)} 个, examples类型: {len(example_agents)} 个")
            
            if self.mofa_mode == 'docker':
                # 分别列举 container 内的两级目录
                hub_agents_list = sorted(self._docker_ls(self.agent_hub_dir))
                example_agents_list = sorted(self._docker_ls(self.examples_dir))
                print(f"Docker 模式列出 {len(hub_agents_list)} 个hub agents, {len(example_agents_list)} 个dataflows")
            else:
                # 将集合转为列表并排序
                hub_agents_list = sorted(list(hub_agents))
                example_agents_list = sorted(list(example_agents))
                print(f"最终找到 {len(hub_agents_list)} 个原子化Agent和 {len(example_agents_list)} 个dataflow示例")

            # 如果都没有找到，提供占位示例
            if not hub_agents_list and not example_agents_list:
                print("未找到任何 agent，返回默认示例")
                return {
                    "hub_agents": ["hello_world", "reasoner"],
                    "example_agents": ["memory", "rag"]
                }
            
            return {
                "hub_agents": hub_agents_list,
                "example_agents": example_agents_list
            }
            
        except Exception as e:
            import traceback
            print(f"Error listing agents: {e}")
            print(traceback.format_exc())
            # 在出错时返回一些默认的 agent 示例
            return {
                "hub_agents": ["hello_world", "reasoner"],
                "example_agents": ["memory", "rag"]
            }
    
    def get_agent_details(self, agent_name, agent_type=None):
        """获取 agent 的详细信息
        
        Args:
            agent_name: agent名称
            agent_type: 'agent-hub' 或 'examples'，如果为None则自动查找
        """
        try:
            if self.mofa_mode == 'docker':
                # Determine agent root inside container
                candidate_paths = [
                    os.path.join(self.agent_hub_dir, agent_name),
                    os.path.join(self.examples_dir, agent_name)
                ]
                agent_path = None
                for p in candidate_paths:
                    test_cmd = f"docker exec -i {self.docker_container} bash -c 'test -d \"{p}\"'"
                    if subprocess.run(test_cmd, shell=True, executable="/bin/bash").returncode == 0:
                        agent_path = p
                        break
                if not agent_path:
                    return None

                files = self._docker_find(agent_path)
                return {
                    "name": agent_name,
                    "path": agent_path,
                    "files": self._file_dict_list(agent_path, files)
                }

            # 根据agent_type参数明确查找对应目录
            if agent_type == 'agent-hub':
                # 明确指定要查找hub目录
                hub_path = os.path.join(self.agent_hub_dir, agent_name)
                if os.path.exists(hub_path):
                    agent_path = hub_path
                    print(f"Found agent '{agent_name}' in agent-hub directory: {agent_path}")
                else:
                    print(f"Agent '{agent_name}' not found in agent-hub directory")
                    return None
            elif agent_type == 'examples':
                # 明确指定要查找examples目录
                examples_path = os.path.join(self.examples_dir, agent_name)
                if os.path.exists(examples_path):
                    agent_path = examples_path
                    print(f"Found agent '{agent_name}' in examples directory: {agent_path}")
                else:
                    print(f"Agent '{agent_name}' not found in examples directory")
                    return None
            else:
                # 如果没有指定agent_type，则按优先级查找（examples优先）
                examples_path = os.path.join(self.examples_dir, agent_name)
                if os.path.exists(examples_path):
                    agent_path = examples_path
                    print(f"Found agent '{agent_name}' in examples directory: {agent_path}")
                else:
                    # 然后检查agent-hub目录
                    hub_path = os.path.join(self.agent_hub_dir, agent_name)
                    if os.path.exists(hub_path):
                        agent_path = hub_path
                        print(f"Found agent '{agent_name}' in agent-hub directory: {agent_path}")
                    else:
                        print(f"Agent '{agent_name}' not found in either examples or agent-hub directories")
                        return None
            
            # 获取 agent 的基本信息
            details = {
                "name": agent_name,
                "path": agent_path,
                "files": self._get_agent_files(agent_path),
            }
            
            # 尝试读取 README.md 获取描述
            readme_path = os.path.join(agent_path, "README.md")
            if os.path.exists(readme_path):
                with open(readme_path, "r") as f:
                    details["description"] = f.read()
            
            return details
        except Exception as e:
            import traceback
            print(f"Error getting agent details: {e}")
            print(traceback.format_exc())
            return None
    
    def _get_agent_files(self, agent_path):
        """递归获取 agent 目录下的所有文件"""
        if self.mofa_mode == 'docker':
            return self._file_dict_list(agent_path, self._docker_find(agent_path))
        files_list = []
        for root, _, filenames in os.walk(agent_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, agent_path)
                files_list.append({
                    "name": filename,
                    "path": rel_path,
                    "type": os.path.splitext(filename)[1][1:] or "txt"
                })
        return files_list
    
    def create_agent(self, agent_name, version="0.0.1", authors="MoFA_Stage User", agent_type="agent-hub", template_name=None):
        """创建一个新的 agent
        
        Args:
            agent_name: Agent 的名称
            version: Agent 的版本号
            authors: Agent 的作者
            agent_type: Agent 的类型，可以是 'agent-hub'（原子 agent）或 'examples'（组合示例）
        """
        try:
            # 根据 agent_type 选择输出目录
            if agent_type == "agent-hub":
                output_dir = self.agent_hub_dir
                template_default = "hello-world"
                template_dirs = [self.agent_hub_dir] + self.additional_hub_dirs
            elif agent_type == "examples":
                output_dir = self.examples_dir
                template_default = "hello_world"
                template_dirs = [self.examples_dir] + self.additional_example_dirs
            else:
                return {"success": False, "message": f"Invalid agent_type: {agent_type}. Must be 'agent-hub' or 'examples'"}

            print(f"创建 {agent_type} 类型的 Agent: {agent_name} 到目录: {output_dir}")

            # 确保目录存在
            os.makedirs(output_dir, exist_ok=True)

            selected_template = template_name or template_default
            template_path = None
            fallback_template_path = None

            for directory in template_dirs:
                if not directory:
                    continue
                candidate = os.path.join(directory, selected_template)
                if os.path.isdir(candidate):
                    template_path = candidate
                    break
                # capture default fallback if different from selected
                default_candidate = os.path.join(directory, template_default)
                if os.path.isdir(default_candidate):
                    fallback_template_path = default_candidate

            if not template_path:
                template_path = fallback_template_path

            agent_dir = os.path.join(output_dir, agent_name)
            result = None

            if template_path and os.path.isdir(template_path):
                if os.path.exists(agent_dir):
                    return {"success": False, "message": f"Agent directory already exists: {agent_dir}"}

                import shutil
                shutil.copytree(template_path, agent_dir)

                template_name_actual = os.path.basename(template_path)
                self._update_agent_name_in_files(agent_dir, template_name_actual, agent_name)

                readme_path = os.path.join(agent_dir, "README.md")
                if os.path.exists(readme_path):
                    with open(readme_path, "r") as f:
                        content = f.read()
                    content = content.replace(template_name_actual, agent_name)
                    content = content.replace("# " + template_name_actual, "# " + agent_name)
                    with open(readme_path, "w") as f:
                        f.write(content)
                else:
                    with open(readme_path, "w") as f:
                        f.write(f"# {agent_name} Agent\n\nCreated by {authors}\nVersion: {version}\n\nThis is a {agent_type} agent.")

                pyproject_path = os.path.join(agent_dir, "pyproject.toml")
                if os.path.exists(pyproject_path):
                    self._update_pyproject(agent_dir, agent_name, version, authors)

                if agent_type == "examples":
                    self._rename_examples_files(agent_dir, template_name_actual, agent_name)

                result = f"Created {agent_type} agent '{agent_name}' from template '{template_name_actual}'"
            else:
                warn_template = template_path or selected_template
                print(f"警告: 模板路径不存在: {warn_template}，将尝试使用 mofa new-agent 命令")
                cmd = f"mofa new-agent {agent_name} --version {version} --output {output_dir} --authors \"{authors}\""
                command_result = self._run_command(cmd)
                if command_result:
                    return {"success": True, "message": f"Agent '{agent_name}' created via mofa new-agent"}
        
            if not result:
                # 命令失败，尝试手动创建一个基本agent目录
                print(f"尝试手动创建基本agent目录: {agent_name}")
                agent_dir = os.path.join(output_dir, agent_name)
                
                if not os.path.exists(agent_dir):
                    os.makedirs(agent_dir, exist_ok=True)
                    
                    # 创建一个基本的README.md
                    readme_path = os.path.join(agent_dir, "README.md")
                    with open(readme_path, "w") as f:
                        f.write(f"# {agent_name} Agent\n\nCreated by {authors}\nVersion: {version}\n\nThis is a {agent_type} agent.")
                    
                    # 创建一个基本的dataflow配置
                    dataflow_path = os.path.join(agent_dir, f"{agent_name}_dataflow.yml")
                    with open(dataflow_path, "w") as f:
                        f.write(f"# {agent_name} Agent Dataflow Configuration\n\nname: {agent_name}\nversion: {version}\n\nnodes: []\n\nlinks: []")
                        
                    return {"success": True, "message": f"Created basic {agent_type} agent structure for {agent_name}"}
                else:
                    return {"success": False, "message": f"Agent directory already exists: {agent_name}"}
            
            return {"success": True, "message": result}
        except Exception as e:
            import traceback
            trace = traceback.format_exc()
            print(f"创建 Agent 时出错: {str(e)}\n{trace}")
            return {"success": False, "message": str(e)}
    
    def run_agent(self, agent_name, timeout=5):
        """运行指定的原子化agent（非阻塞方式）
        这个方法专门用于运行 agent-hub 中的原子化agent
        """
        try:
            # 使用缓存查找agent的实际路径
            agent_path = self._find_agent_path(agent_name)
            if not agent_path:
                return {
                    "success": False, 
                    "message": f"Agent {agent_name} not found in any configured directory. If this is an example, use run_example instead."
                }
            print(f"找到 agent {agent_name} 在路径: {agent_path}")
            
            # 使用适合原子化agent的命令运行
            cmd = f"cd {self.mofa_dir} && mofa run --agent-name {agent_name}"
            # 在后台运行，以便不阻塞 API 响应
            process = subprocess.Popen(
                cmd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 仅等待 timeout 秒，然后返回进程 ID
            return {
                "success": True, 
                "message": f"Atomic agent {agent_name} started", 
                "process_id": process.pid,
                "agent_type": "atomic"
            }
        except Exception as e:
            return {"success": False, "message": str(e)}
            
    def run_example(self, example_name, timeout=5):
        """运行指定的dataflow示例（非阻塞方式）
        这个方法专门用于运行 examples 目录中的dataflow示例
        dataflow示例可能需要不同的启动参数或环境设置
        
        新的运行方式：使用 dora 命令运行 dataflow
        1. cd 到示例目录
        2. dora up
        3. dora build xxx_dataflow.yml
        4. dora start xxx_dataflow.yml
        """
        print(f"\n\n===== 开始运行 example: {example_name} =====")
        try:
            # 使用缓存查找示例的实际路径
            example_path = self._find_agent_path(example_name)
            if not example_path:
                return {
                    "success": False, 
                    "message": f"Example {example_name} not found in any configured directory. If this is an atomic agent, use run_agent instead."
                }
            print(f"找到 example {example_name} 在路径: {example_path}")
            
            # 查找 dataflow 配置文件
            dataflow_files = [f for f in os.listdir(example_path) if f.endswith('_dataflow.yml') or f.endswith('.yml')]
            if not dataflow_files:
                return {
                    "success": False,
                    "message": f"No dataflow configuration file found in {example_name}"
                }
            
            # 选择第一个找到的 dataflow 文件
            dataflow_file = dataflow_files[0]
            print(f"使用 dataflow 文件: {dataflow_file}")
            
            # 新的运行方式：使用单个命令执行所有 dora 操作
            print(f"Running dora commands in {example_path}...")
            
            # 使用标准的dora四步命令（与TtydTerminal保持一致）
            dora_cmd = f"cd {example_path} && dora up && dora build {dataflow_file} && dora start {dataflow_file}"
            
            # 初始化输出行列表
            output_lines = [
                f"Starting dataflow example: {example_name}",
                f"Working directory: {example_path}",
                f"Dataflow file: {dataflow_file}",
                f"Command: cd {example_path} && dora up && dora build {dataflow_file} && dora start {dataflow_file}",
                "=" * 60
            ]
            
            # 在后台运行 dora 命令
            process = subprocess.Popen(
                dora_cmd,
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,  # 将stderr重定向到stdout，统一处理
                text=True,
                bufsize=0,  # 无缓冲
                universal_newlines=True,
                cwd=example_path  # 设置工作目录
            )
            
            # 保存进程信息，以便后续获取输出
            self._running_processes[example_name] = {
                "process": process,
                "start_time": time.time(),
                "output_lines": output_lines,  # 已经有了前面命令的输出
                "type": "example"
            }
            
            # 返回结果
            return {
                "success": True, 
                "message": f"Example {example_name} started with dora", 
                "process_id": process.pid,
                "agent_type": "example",
                "dataflow_file": dataflow_file
            }
            
            # 旧的运行方式（注释掉）
            '''
            # 使用适合组合式示例的命令运行
            cmd = f"cd {self.mofa_dir} && mofa run --agent-name {example_name} --example"
            # 在后台运行，以便不阻塞 API 响应
            process = subprocess.Popen(
                cmd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 仅等待 timeout 秒，然后返回进程 ID
            return {
                "success": True, 
                "message": f"Example {example_name} started", 
                "process_id": process.pid,
                "agent_type": "example"
            }
            '''
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def stop_agent(self, process_id):
        """停止正在运行的 agent 进程"""
        try:
            cmd = f"kill {process_id}"
            self._run_command(cmd)
            return {"success": True, "message": f"Agent process {process_id} stopped"}
        except Exception as e:
            return {"success": False, "message": str(e)}
            
    def get_process_output(self, agent_name):
        """获取正在运行的进程的输出
        
        Args:
            agent_name: Agent 的名称
            
        Returns:
            包含进程输出的字典
        """
        try:
            if agent_name not in self._running_processes:
                return {
                    "success": False,
                    "message": f"No running process found for {agent_name}"
                }
                
            process_info = self._running_processes[agent_name]
            process = process_info["process"]
            
            # 读取新的输出
            new_output = []
            
            # 非阻塞地读取stdout输出
            try:
                # 将文件描述符设置为非阻塞模式
                import fcntl
                import os
                fd = process.stdout.fileno()
                fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
                
                # 尝试读取所有可用的输出
                while True:
                    try:
                        line = process.stdout.readline()
                        if not line:
                            break
                        line = line.strip()
                        if line:  # 只添加非空行
                            new_output.append(line)
                    except Exception:
                        break
            except Exception as e:
                new_output.append(f"Error reading output: {str(e)}")
            
            # 将新输出添加到累积输出中
            process_info["output_lines"].extend(new_output)
            
            # 调试信息
            if new_output:
                print(f"读取到新输出 ({len(new_output)} 行): {new_output[:3]}...")  # 只打印前3行
            
            # 检查进程是否已经结束
            is_running = process.poll() is None
            
            # 调试信息
            total_lines = len(process_info["output_lines"])
            print(f"Agent {agent_name}: 运行状态={is_running}, 总输出行数={total_lines}, 新输出行数={len(new_output)}")
            
            return {
                "success": True,
                "is_running": is_running,
                "new_output": new_output,
                "output": "\n".join(process_info["output_lines"]),  # 添加完整输出字符串
                "all_output": process_info["output_lines"],
                "process_type": process_info["type"],
                "start_time": process_info["start_time"],
                "elapsed_time": time.time() - process_info["start_time"]
            }
        except Exception as e:
            import traceback
            trace = traceback.format_exc()
            print(f"获取进程输出时出错: {str(e)}\n{trace}")
            return {"success": False, "message": str(e)}
    
    def delete_agent(self, agent_name):
        """删除指定的 agent
        
        会自动检查 agent-hub 和 examples 目录
        """
        try:
            # 使用缓存查找agent的实际路径
            agent_path = self._find_agent_path(agent_name)
            if not agent_path:
                return {"success": False, "message": f"Agent {agent_name} not found in any configured directory"}
            
            # 根据路径判断类型
            if self.agent_hub_dir in agent_path:
                agent_type = "agent-hub"
            elif self.examples_dir in agent_path:
                agent_type = "examples"
            else:
                agent_type = "custom"
            
            # 递归删除目录
            import shutil
            print(f"删除 {agent_type} 类型的 Agent: {agent_name} 路径: {agent_path}")
            shutil.rmtree(agent_path)
            
            # 从缓存中移除
            if agent_name in self.agent_location_cache:
                del self.agent_location_cache[agent_name]
                
            return {"success": True, "message": f"{agent_type} Agent {agent_name} deleted"}
        except Exception as e:
            import traceback
            trace = traceback.format_exc()
            print(f"删除 Agent 时出错: {str(e)}\n{trace}")
            return {"success": False, "message": str(e)}
    
    def copy_agent(self, source_agent, target_agent, agent_type=None):
        """复制一个 agent 作为新的 agent
        
        Args:
            source_agent: 源 Agent 的名称
            target_agent: 目标 Agent 的名称
            agent_type: Agent 的类型，可以是 'agent-hub'（原子 agent）或 'examples'（组合示例）
                       如果为 None，则会自动检测源 Agent 的类型
        """
        try:
            # 输出日志以便于调试
            print(f"尝试复制 Agent {source_agent} 到 {target_agent}")
            
            # 首先检查源 Agent 的类型，如果没有指定 agent_type
            if agent_type is None:
                # 检查在 agent-hub 目录中
                if os.path.exists(os.path.join(self.agent_hub_dir, source_agent)):
                    agent_type = "agent-hub"
                    source_path = os.path.join(self.agent_hub_dir, source_agent)
                # 检查在 examples 目录中
                elif os.path.exists(os.path.join(self.examples_dir, source_agent)):
                    agent_type = "examples"
                    source_path = os.path.join(self.examples_dir, source_agent)
                else:
                    # 尝试在其他可能的目录中查找
                    print(f"在默认目录中找不到源 Agent: {source_agent}")
                    source_path = None
                    other_locations = []
                    
                    # 导入配置文件中的AGENT_STORAGE_OPTIONS
                    import sys
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    from config import AGENT_STORAGE_OPTIONS
                    
                    for key, rel_path in AGENT_STORAGE_OPTIONS.items():
                        other_path = os.path.join(self.mofa_dir, rel_path, source_agent)
                        other_locations.append(other_path)
                        if os.path.exists(other_path):
                            print(f"在其他位置找到了源 Agent: {other_path}")
                            source_path = other_path
                            # 根据路径判断 agent 类型
                            if "agent-hub" in other_path:
                                agent_type = "agent-hub"
                            elif "examples" in other_path:
                                agent_type = "examples"
                            else:
                                # 默认使用 agent-hub
                                agent_type = "agent-hub"
                            break
                    
                    if source_path is None:
                        return {"success": False, "message": f"Source agent '{source_agent}' not found. Searched in agent-hub, examples, and {other_locations}"}
            else:
                # 根据指定的 agent_type 选择源路径
                if agent_type == "agent-hub":
                    source_path = os.path.join(self.agent_hub_dir, source_agent)
                elif agent_type == "examples":
                    source_path = os.path.join(self.examples_dir, source_agent)
                else:
                    return {"success": False, "message": f"Invalid agent_type: {agent_type}. Must be 'agent-hub' or 'examples'"}
            
            # 根据 agent_type 选择目标路径
            if agent_type == "agent-hub":
                target_path = os.path.join(self.agent_hub_dir, target_agent)
            else:  # examples
                target_path = os.path.join(self.examples_dir, target_agent)
            
            print(f"source_path = {source_path}")
            print(f"target_path = {target_path}")
            print(f"agent_type = {agent_type}")
            
            # 检查源路径是否存在
            if not os.path.exists(source_path):
                return {"success": False, "message": f"Source agent '{source_agent}' not found at {source_path}"}
            
            # 检查目标路径是否已存在
            if os.path.exists(target_path):
                return {"success": False, "message": f"Target agent '{target_agent}' already exists at {target_path}"}
            
            # 创建目标目录的父目录（如果不存在）
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # 复制目录
            import shutil
            print(f"正在复制 {agent_type} agent: {source_path} -> {target_path}")
            shutil.copytree(source_path, target_path)
            
            # 更新配置文件中的名称
            self._update_agent_name_in_files(target_path, source_agent, target_agent)
            
            return {"success": True, "message": f"{agent_type} agent '{source_agent}' successfully copied to '{target_agent}'"}
        except Exception as e:
            import traceback
            trace = traceback.format_exc()
            print(f"复制 Agent 时出错: {str(e)}\n{trace}")
            return {"success": False, "message": f"Failed to copy agent: {str(e)}"}
    
    def get_agent_logs(self, agent_name):
        """获取指定agent的运行日志
        尝试从以下位置获取日志：
        1. agent目录下的logs子目录
        2. agent目录下的out目录及其子目录
        3. MoFA目录下的logs子目录中与agent相关的日志
        4. 系统临时目录中可能的日志文件
        5. 各种可能的log文件夹和子文件夹
        """
        try:
            # 首先检查agent是否存在于任何可能的目录中
            agent_paths = []
            
            # 检查主要agent目录
            primary_agent_path = os.path.join(self.agents_dir, agent_name)
            if os.path.exists(primary_agent_path):
                agent_paths.append(primary_agent_path)
            
            # 检查所有可能的agent目录
            for possible_dir in self.possible_agent_dirs:
                possible_path = os.path.join(possible_dir, agent_name)
                if os.path.exists(possible_path) and possible_path not in agent_paths:
                    agent_paths.append(possible_path)
            
            # 如果没有找到agent，尝试在examples目录中查找
            if not agent_paths:
                for example_dir in self.example_dirs:
                    example_path = os.path.join(example_dir, agent_name)
                    if os.path.exists(example_path):
                        agent_paths.append(example_path)
            
            if not agent_paths:
                return f"未找到名为 {agent_name} 的Agent。请检查名称是否正确。"
            
            # 可能的日志位置
            log_locations = []
            
            # 为每个找到的agent路径添加可能的日志位置
            for agent_path in agent_paths:
                # 1. agent目录下的logs子目录
                log_locations.append(os.path.join(agent_path, "logs"))
                # 2. agent目录下直接的log文件
                log_locations.append(os.path.join(agent_path, f"{agent_name}.log"))
                # 3. agent目录下的log子目录
                log_locations.append(os.path.join(agent_path, "log"))
                # 4. agent目录下的output子目录
                log_locations.append(os.path.join(agent_path, "output"))
            
            # 5. MoFA目录下的logs子目录
            log_locations.append(os.path.join(self.mofa_dir, "logs", f"{agent_name}.log"))
            # 6. MoFA目录下的通用logs目录
            log_locations.append(os.path.join(self.mofa_dir, "logs"))
            # 7. MoFA目录下的log子目录
            log_locations.append(os.path.join(self.mofa_dir, "log"))
            
            logs_content = []
            
            # 检查所有agent路径下的out目录
            for agent_path in agent_paths:
                out_dir = os.path.join(agent_path, "out")
                if os.path.exists(out_dir) and os.path.isdir(out_dir):
                    # 检查dora-daemon.txt文件
                    daemon_log = os.path.join(out_dir, "dora-daemon.txt")
                    if os.path.exists(daemon_log) and os.path.isfile(daemon_log):
                        try:
                            with open(daemon_log, "r") as f:
                                # 只读取最后200行，避免文件过大
                                lines = f.readlines()
                                content = "".join(lines[-200:] if len(lines) > 200 else lines)
                                if content:
                                    logs_content.append(f"=== Dora Daemon 日志 ({os.path.basename(agent_path)}) ===\n{content}\n")
                        except Exception as e:
                            logs_content.append(f"无法读取Dora Daemon日志: {str(e)}")
                    
                    # 检查dora-coordinator.txt文件
                    coordinator_log = os.path.join(out_dir, "dora-coordinator.txt")
                    if os.path.exists(coordinator_log) and os.path.isfile(coordinator_log):
                        try:
                            with open(coordinator_log, "r") as f:
                                # 只读取最后200行，避免文件过大
                                lines = f.readlines()
                                content = "".join(lines[-200:] if len(lines) > 200 else lines)
                                if content:
                                    logs_content.append(f"=== Dora Coordinator 日志 ({os.path.basename(agent_path)}) ===\n{content}\n")
                        except Exception as e:
                            logs_content.append(f"无法读取Dora Coordinator日志: {str(e)}")
                
                    # 检查out目录下的其他日志文件
                    for file in os.listdir(out_dir):
                        file_path = os.path.join(out_dir, file)
                        # 只处理文件，不处理目录
                        if os.path.isfile(file_path) and file != "dora-daemon.txt" and file != "dora-coordinator.txt":
                            # 检查是否是日志文件（有文本扩展名或包含"log"或"日志"字样）
                            if file.endswith(".txt") or file.endswith(".log") or "log" in file.lower() or "日志" in file:
                                try:
                                    with open(file_path, "r") as f:
                                        # 只读取最后100行，避免文件过大
                                        lines = f.readlines()
                                        content = "".join(lines[-100:] if len(lines) > 100 else lines)
                                        if content:
                                            logs_content.append(f"=== {file} ({os.path.basename(agent_path)}/out) ===\n{content}\n")
                                except Exception as e:
                                    logs_content.append(f"无法读取日志文件 {file}: {str(e)}")
                
                    # 查找运行实例目录（UUID格式的目录）
                    instance_dirs = []
                    for item in os.listdir(out_dir):
                        item_path = os.path.join(out_dir, item)
                        # 检查是否是目录且看起来像UUID（包含连字符且长度合适）
                        if os.path.isdir(item_path) and "-" in item and len(item) > 30:
                            instance_dirs.append(item_path)
                    
                    # 按修改时间排序，最新的排在前面
                    instance_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    
                    # 处理所有实例目录
                    for instance_dir in instance_dirs:
                        # 查找agent日志文件
                        agent_log_pattern = f"log_{agent_name}*.txt"
                        agent_logs = []
                        
                        # 使用glob模式查找匹配的日志文件
                        for root, _, files in os.walk(instance_dir):
                            for file in files:
                                if file.startswith(f"log_{agent_name}") or file.startswith("log_") and "agent" in file.lower():
                                    agent_logs.append(os.path.join(root, file))
                                # 添加更多日志文件模式
                                elif file.endswith(".txt") or file.endswith(".log") or "log" in file.lower() or "日志" in file:
                                    agent_logs.append(os.path.join(root, file))
                        
                        # 处理找到的日志文件
                        for log_file in agent_logs:
                            try:
                                with open(log_file, "r") as f:
                                    # 只读取最后100行，避免文件过大
                                    lines = f.readlines()
                                    content = "".join(lines[-100:] if len(lines) > 100 else lines)
                                    if content:
                                        instance_name = os.path.basename(instance_dir)
                                        file_name = os.path.basename(log_file)
                                        logs_content.append(f"=== 运行实例 {instance_name} - {file_name} ({os.path.basename(agent_path)}) ===\n{content}\n")
                            except Exception as e:
                                logs_content.append(f"无法读取实例日志 {log_file}: {str(e)}")
            
            # 遍历所有可能的日志位置
            for location in log_locations:
                if os.path.exists(location):
                    if os.path.isdir(location):
                        # 如果是目录，查找与agent相关的所有日志文件
                        log_files = []
                        for file in os.listdir(location):
                            # 扩展匹配条件，包括更多可能的日志文件
                            if (file.endswith(".log") or file.endswith(".txt") or "log" in file.lower() or "日志" in file) and \
                               (agent_name in file or "agent" in file.lower() or "mofa" in file.lower()):
                                log_files.append(os.path.join(location, file))
                        
                        # 按修改时间排序，最新的日志排在前面
                        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                        
                        # 读取最新的几个日志文件
                        for log_file in log_files[:5]:  # 增加到最多读取5个最新的日志文件
                            try:
                                with open(log_file, "r") as f:
                                    # 只读取最后200行，避免文件过大
                                    lines = f.readlines()
                                    content = "".join(lines[-200:] if len(lines) > 200 else lines)
                                    if content:
                                        logs_content.append(f"=== {os.path.basename(log_file)} ({os.path.basename(os.path.dirname(log_file))}) ===\n{content}\n")
                            except Exception as e:
                                logs_content.append(f"无法读取日志文件 {log_file}: {str(e)}")
                        
                        # 递归查找子目录中的日志文件
                        for root, dirs, files in os.walk(location):
                            if root != location:  # 跳过已处理的顶级目录
                                log_files = []
                                for file in files:
                                    if (file.endswith(".log") or file.endswith(".txt") or "log" in file.lower() or "日志" in file) and \
                                       (agent_name in file or "agent" in file.lower() or "mofa" in file.lower()):
                                        log_files.append(os.path.join(root, file))
                                
                                # 按修改时间排序，最新的日志排在前面
                                log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                                
                                # 读取最新的几个日志文件
                                for log_file in log_files[:3]:  # 最多读取3个最新的日志文件
                                    try:
                                        with open(log_file, "r") as f:
                                            # 只读取最后100行，避免文件过大
                                            lines = f.readlines()
                                            content = "".join(lines[-100:] if len(lines) > 100 else lines)
                                            if content:
                                                rel_path = os.path.relpath(log_file, location)
                                                logs_content.append(f"=== {rel_path} ===\n{content}\n")
                                    except Exception as e:
                                        logs_content.append(f"无法读取日志文件 {log_file}: {str(e)}")
                    else:
                        # 如果是文件，直接读取
                        try:
                            with open(location, "r") as f:
                                # 只读取最后200行，避免文件过大
                                lines = f.readlines()
                                content = "".join(lines[-200:] if len(lines) > 200 else lines)
                                if content:
                                    logs_content.append(f"=== {os.path.basename(location)} ===\n{content}")
                        except Exception as e:
                            # 不记录错误，因为很多路径可能不存在
                            pass
            
            # 尝试读取所有正在运行的进程，替代使用self.runningAgents
            if not logs_content:
                try:
                    # 尝试查找与agent相关的正在运行的进程
                    cmd = f"ps aux | grep -v grep | grep mofa | grep {agent_name} | head -n 1"
                    process_info = self._run_command(cmd)
                    
                    if process_info:
                        logs_content.append(f"当前运行进程信息:\n{process_info}\n")
                        
                        # 提取进程ID
                        process_parts = process_info.split()
                        if len(process_parts) > 1:
                            process_id = process_parts[1]  # 第二列通常是进程ID
                            
                            # 尝试获取进程最近的输出
                            cmd = f"tail -n 50 /proc/{process_id}/fd/1 2>/dev/null || echo '无法读取进程输出'"
                            process_output = self._run_command(cmd)
                            if process_output and process_output != '无法读取进程输出':
                                logs_content.append(f"进程输出:\n{process_output}")
                except Exception as e:
                    logs_content.append(f"无法获取进程信息: {str(e)}")
            
            # 如果仍然没有找到日志，返回一个默认消息
            if not logs_content:
                logs_content.append(f"未找到 {agent_name} 的日志文件。可能是该Agent还未运行过。")
            
            return "\n\n".join(logs_content)
        except Exception as e:
            print(f"获取agent日志时出错: {e}")
            return f"获取日志时发生错误: {str(e)}"
    
    def _find_agent_path(self, agent_name):
        """查找agent的实际路径，优先从缓存查找，缓存没有则实时查找"""
        # 1. 优先从缓存中查找
        if agent_name in self.agent_location_cache:
            cached_path = self.agent_location_cache[agent_name]
            # 验证缓存的路径是否还存在
            if os.path.exists(cached_path):
                return cached_path
            else:
                # 缓存失效，从缓存中移除
                del self.agent_location_cache[agent_name]
        
        # 2. 缓存中没有，实时在所有目录中查找
        for scan_dir in self.all_scan_dirs:
            if os.path.exists(scan_dir):
                candidate_path = os.path.join(scan_dir, agent_name)
                if os.path.exists(candidate_path) and os.path.isdir(candidate_path):
                    # 找到了，更新缓存并返回
                    self.agent_location_cache[agent_name] = candidate_path
                    return candidate_path
        
        # 3. 都没找到，返回None
        return None
    
    def _update_agent_name_in_files(self, agent_path, old_name, new_name):
        """在复制的 agent 文件中更新名称"""
        for root, _, filenames in os.walk(agent_path):
            for filename in filenames:
                if filename.endswith(('.py', '.yml', '.yaml', '.toml', '.md')):
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                        
                        # 替换名称
                        content = content.replace(old_name, new_name)
                        
                        with open(file_path, 'w') as f:
                            f.write(content)
                    except Exception as e:
                        print(f"Error updating file {file_path}: {e}")
    
    def read_file(self, agent_name, file_path, agent_type=None):
        """读取 agent 文件内容
        
        Args:
            agent_name: agent名称
            file_path: 文件路径
            agent_type: 'agent-hub' 或 'examples'，如果为None则自动查找
        """
        if self.mofa_mode == 'docker':
            # 尝试 hub 目录
            candidate_paths = [
                os.path.join(self.agent_hub_dir, agent_name, file_path),
                os.path.join(self.examples_dir, agent_name, file_path)
            ]
            for p in candidate_paths:
                cmd = f"docker exec -i {self.docker_container} bash -c 'test -f \"{p}\"'"
                if subprocess.run(cmd, shell=True, executable="/bin/bash").returncode == 0:
                    # 文件存在，读取
                    cat_cmd = f"docker exec -i {self.docker_container} bash -c 'cat \"{p}\"'"
                    result = subprocess.run(cat_cmd, shell=True, executable="/bin/bash", text=True, capture_output=True)
                    if result.returncode == 0:
                        return {"success": True, "content": result.stdout}
                    else:
                        return {"success": False, "message": result.stderr}
            return {"success": False, "message": f"File {file_path} not found in container"}

        # ---- 本地模式：根据agent_type参数明确查找对应目录 ----
        if agent_type == 'agent-hub':
            # 明确指定要在hub目录中查找
            hub_file_path = os.path.join(self.agent_hub_dir, agent_name, file_path)
            if os.path.exists(hub_file_path):
                try:
                    with open(hub_file_path, 'r') as f:
                        content = f.read()
                    return {"success": True, "content": content}
                except Exception as e:
                    return {"success": False, "message": str(e)}
            else:
                return {"success": False, "message": f"File {file_path} not found in agent-hub agent {agent_name}"}
        elif agent_type == 'examples':
            # 明确指定要在examples目录中查找
            examples_file_path = os.path.join(self.examples_dir, agent_name, file_path)
            if os.path.exists(examples_file_path):
                try:
                    with open(examples_file_path, 'r') as f:
                        content = f.read()
                    return {"success": True, "content": content}
                except Exception as e:
                    return {"success": False, "message": str(e)}
            else:
                return {"success": False, "message": f"File {file_path} not found in examples agent {agent_name}"}
        else:
            # 如果没有指定agent_type，则按优先级查找（examples优先）
            # 首先检查examples目录
            examples_file_path = os.path.join(self.examples_dir, agent_name, file_path)
            if os.path.exists(examples_file_path):
                try:
                    with open(examples_file_path, 'r') as f:
                        content = f.read()
                    return {"success": True, "content": content}
                except Exception as e:
                    return {"success": False, "message": str(e)}
            
            # 然后检查agent-hub目录
            hub_file_path = os.path.join(self.agent_hub_dir, agent_name, file_path)
            if os.path.exists(hub_file_path):
                try:
                    with open(hub_file_path, 'r') as f:
                        content = f.read()
                    return {"success": True, "content": content}
                except Exception as e:
                    return {"success": False, "message": str(e)}
            
            return {"success": False, "message": f"File {file_path} not found in agent {agent_name}"}
    
    def write_file(self, agent_name, file_path, content):
        """写入 agent 文件内容"""
        if self.mofa_mode == 'docker':
            # 选择写入到 agent-hub 目录（若存在），否则 examples
            base_path = os.path.join(self.agent_hub_dir, agent_name)
            test_cmd = f"docker exec -i {self.docker_container} bash -c 'test -d \"{base_path}\"'"
            if subprocess.run(test_cmd, shell=True, executable="/bin/bash").returncode != 0:
                base_path = os.path.join(self.examples_dir, agent_name)

            full_path = os.path.join(base_path, file_path)
            dir_path = os.path.dirname(full_path)

            # 确保目录存在
            mkdir_cmd = f"docker exec -i {self.docker_container} bash -c 'mkdir -p \"{dir_path}\"'"
            subprocess.run(mkdir_cmd, shell=True, executable="/bin/bash")

            # 通过 stdin 写入文件
            write_cmd = f"docker exec -i {self.docker_container} bash -c 'cat > \"{full_path}\"'"
            result = subprocess.run(write_cmd, shell=True, executable="/bin/bash", text=True, input=content)
            if result.returncode == 0:
                return {"success": True, "message": f"File {file_path} saved"}
            else:
                return {"success": False, "message": result.stderr}

        # ---- 本地模式：明确区分agent类型，不进行跨目录查找 ----
        # 首先检查examples目录中是否存在agent
        examples_agent_path = os.path.join(self.examples_dir, agent_name)
        if os.path.exists(examples_agent_path):
            agent_path = examples_agent_path
        else:
            # 然后检查agent-hub目录
            hub_agent_path = os.path.join(self.agent_hub_dir, agent_name)
            if os.path.exists(hub_agent_path):
                agent_path = hub_agent_path
            else:
                # 如果两个目录都不存在，默认在examples目录中创建
                agent_path = examples_agent_path
                os.makedirs(agent_path, exist_ok=True)

        full_path = os.path.join(agent_path, file_path)
        dir_path = os.path.dirname(full_path)
        try:
            os.makedirs(dir_path, exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
            return {"success": True, "message": f"File {file_path} saved"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ------------------------------ Docker Helpers ------------------------------
    def _docker_ls(self, directory):
        """Return list of subdirectories (one level) inside given directory of container."""
        try:
            cmd = f"docker exec -i {self.docker_container} bash -c 'ls -1 {directory} 2>/dev/null'"
            result = subprocess.run(cmd, shell=True, executable="/bin/bash", text=True, capture_output=True)
            if result.returncode == 0:
                items = [item.strip() for item in result.stdout.split("\n") if item.strip()]
                return items
            else:
                return []
        except Exception:
            return []

    def _docker_find(self, directory):
        """Return list of all files (relative paths) under directory inside container."""
        try:
            cmd = f"docker exec -i {self.docker_container} bash -c 'cd \"{directory}\" 2>/dev/null && find . -type f'"
            result = subprocess.run(cmd, shell=True, executable="/bin/bash", text=True, capture_output=True)
            if result.returncode == 0:
                files = [line.lstrip('./') for line in result.stdout.split("\n") if line.strip()]
                return files
            return []
        except Exception:
            return []

    def _file_dict_list(self, base_path, rel_paths):
        """Helper: given list of relative paths, return list of dicts like original."""
        result = []
        for rel in rel_paths:
            name = os.path.basename(rel)
            ext = os.path.splitext(name)[1][1:] or "txt"
            result.append({"name": name, "path": rel, "type": ext})
        return result

    def _read_text_file(self, file_path, max_chars=5000):
        """Read a text file safely with a sensible size limit."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(max_chars)
            return content
        except Exception:
            return ""

    def _first_meaningful_paragraph(self, text):
        """Extract the first non-heading paragraph from markdown/text."""
        if not text:
            return ""

        paragraphs = re.split(r"\n\s*\n", text)
        for paragraph in paragraphs:
            cleaned = paragraph.strip()
            if not cleaned:
                continue
            # Remove markdown heading markers/bullets
            cleaned = re.sub(r"^[#>\-*\s]+", "", cleaned)
            cleaned = cleaned.strip()
            if len(cleaned) >= 24:
                return re.sub(r"\s+", " ", cleaned)
        return ""

    def _extract_python_docstrings(self, node_path, max_files=6):
        """Collect top-level docstrings from python files close to the root."""
        docstrings = []
        visited = 0
        for root, dirs, files in os.walk(node_path):
            depth = root.count(os.sep) - node_path.count(os.sep)
            if depth > 1:
                # Skip deeply nested files to keep things light-weight
                dirs[:] = []
                continue

            for file in files:
                if not file.endswith(".py"):
                    continue
                file_path = os.path.join(root, file)
                text = self._read_text_file(file_path)
                if not text:
                    continue
                try:
                    module = ast.parse(text)
                    docstring = ast.get_docstring(module)
                except Exception:
                    docstring = None

                if not docstring:
                    # Fallback to the first comment block at the top of the file
                    head = text.split("\n\n", 1)[0]
                    comment_lines = []
                    for line in head.splitlines():
                        stripped = line.strip()
                        if stripped.startswith("#"):
                            comment_lines.append(stripped.lstrip("# "))
                        else:
                            break
                    if comment_lines:
                        docstring = " ".join(comment_lines)

                if docstring:
                    docstrings.append(re.sub(r"\s+", " ", docstring.strip()))

                visited += 1
                if visited >= max_files:
                    break
            if visited >= max_files:
                break

        return docstrings

    def _parse_pyproject_metadata(self, pyproject_path):
        """Extract description, entry points, dependencies, and keywords from pyproject."""
        if not os.path.exists(pyproject_path):
            return {}

        metadata = {}
        try:
            data = toml.load(pyproject_path)
        except Exception:
            return {}

        project_table = {}
        if "project" in data:
            project_table = data.get("project", {})
        elif data.get("tool", {}).get("poetry"):
            project_table = data["tool"]["poetry"]

        if project_table:
            if project_table.get("description"):
                metadata["description"] = project_table.get("description", "")
            if project_table.get("keywords"):
                metadata["keywords"] = project_table.get("keywords", [])

        # Entry points / scripts
        entry_points = []
        poetry_scripts = data.get("tool", {}).get("poetry", {}).get("scripts", {})
        project_scripts = data.get("project", {}).get("scripts", {})
        scripts = {**poetry_scripts, **project_scripts}
        for name, target in scripts.items():
            entry_points.append(f"{name} -> {target}")
        if entry_points:
            metadata["entry_points"] = entry_points

        # Dependencies
        dependencies = []
        raw_dependencies = data.get("project", {}).get("dependencies")
        if raw_dependencies:
            dependencies.extend(self._format_dependency_list(raw_dependencies))

        poetry_dependencies = data.get("tool", {}).get("poetry", {}).get("dependencies")
        if poetry_dependencies:
            dependencies.extend(self._format_dependency_dict(poetry_dependencies))

        if dependencies:
            # Remove duplicates while preserving order
            seen = set()
            ordered = []
            for dep in dependencies:
                if dep not in seen:
                    ordered.append(dep)
                    seen.add(dep)
            metadata["dependencies"] = ordered

        return metadata

    def _format_dependency_list(self, dependencies):
        formatted = []
        if isinstance(dependencies, list):
            for dep in dependencies:
                if isinstance(dep, str):
                    formatted.append(dep)
        elif isinstance(dependencies, dict):
            formatted.extend(self._format_dependency_dict(dependencies))
        return formatted

    def _format_dependency_dict(self, dependencies):
        formatted = []
        if not isinstance(dependencies, dict):
            return formatted

        for name, value in dependencies.items():
            if name.lower() == "python":
                continue
            if isinstance(value, dict):
                version = value.get("version") or value.get("path") or value.get("url")
            else:
                version = value
            if version and version != "*":
                formatted.append(f"{name} ({version})")
            else:
                formatted.append(str(name))
        return formatted

    def _collect_config_files(self, node_path, max_files=5):
        configs = []
        try:
            for root, dirs, files in os.walk(node_path):
                depth = root.count(os.sep) - node_path.count(os.sep)
                if depth > 1:
                    dirs[:] = []
                    continue
                for file in files:
                    if file.endswith((".yaml", ".yml", ".json")):
                        rel_path = os.path.relpath(os.path.join(root, file), node_path)
                        configs.append(rel_path)
                        if len(configs) >= max_files:
                            return configs
        except Exception:
            return configs
        return configs

    def _collect_primary_files(self, node_path, max_files=6):
        primary = []
        try:
            for root, dirs, files in os.walk(node_path):
                depth = root.count(os.sep) - node_path.count(os.sep)
                if depth > 1:
                    dirs[:] = []
                    continue
                for file in files:
                    if file.endswith(".py") and file != "__init__.py":
                        rel_path = os.path.relpath(os.path.join(root, file), node_path)
                        primary.append(rel_path)
                        if len(primary) >= max_files:
                            return primary
        except Exception:
            return primary
        return primary

    def _collect_node_metadata(self, node_path):
        """Gather multiple contextual signals about a node."""
        metadata = {}

        readme_candidates = [
            "README.md",
            "README.MD",
            "README_cn.md",
            "README_CN.md",
        ]

        description_candidates = []
        for filename in readme_candidates:
            text = self._read_text_file(os.path.join(node_path, filename))
            summary = self._first_meaningful_paragraph(text)
            if summary:
                description_candidates.append(("readme", summary))

        pyproject_metadata = self._parse_pyproject_metadata(os.path.join(node_path, "pyproject.toml"))
        if pyproject_metadata.get("description"):
            description_candidates.append(("pyproject", pyproject_metadata["description"]))

        docstrings = self._extract_python_docstrings(node_path)
        if docstrings:
            for doc in docstrings:
                description_candidates.append(("code", doc))
            metadata["doc_highlights"] = [doc.split("\n")[0] for doc in docstrings[:3]]

        context_snippets = []
        if readme_candidates:
            for filename in readme_candidates:
                file_path = os.path.join(node_path, filename)
                if os.path.exists(file_path):
                    text = self._read_text_file(file_path, max_chars=1200)
                    if text:
                        context_snippets.append({
                            "path": filename,
                            "type": "readme",
                            "snippet": text[:400]
                        })

        config_files = self._collect_config_files(node_path)
        if config_files:
            metadata["config_files"] = config_files
            for rel_path in config_files[:3]:
                absolute_path = os.path.join(node_path, rel_path)
                parser = None
                if rel_path.endswith((".yaml", ".yml")):
                    parser = lambda text: yaml.safe_load(text)
                elif rel_path.endswith(".json"):
                    parser = lambda text: json.loads(text)

                if not parser:
                    continue

                try:
                    raw_text = self._read_text_file(absolute_path, max_chars=8000)
                    config_data = parser(raw_text) if raw_text else None
                except Exception:
                    config_data = None

                if isinstance(config_data, dict):
                    for key in ("description", "summary", "details"):
                        value = config_data.get(key)
                        if isinstance(value, str):
                            cleaned = self._first_meaningful_paragraph(value)
                            if cleaned:
                                description_candidates.append(("config", cleaned))
                                break
                
                raw_preview = self._read_text_file(absolute_path, max_chars=800)
                if raw_preview:
                    context_snippets.append({
                        "path": rel_path,
                        "type": "config",
                        "snippet": raw_preview[:400]
                    })
        selected_description = ""
        priority = ["pyproject", "readme", "config", "code"]
        for source in priority:
            for candidate_source, candidate_text in description_candidates:
                if candidate_source == source and candidate_text:
                    selected_description = candidate_text.strip()
                    break
            if selected_description:
                break

        if not selected_description and description_candidates:
            selected_description = description_candidates[0][1]

        if selected_description:
            selected_description = re.sub(r"\s+", " ", selected_description).strip()
            if len(selected_description) > 200:
                selected_description = selected_description[:197].rstrip() + "..."

        if pyproject_metadata.get("entry_points"):
            metadata["entry_points"] = pyproject_metadata["entry_points"]

        if pyproject_metadata.get("dependencies"):
            metadata["dependencies"] = pyproject_metadata["dependencies"]

        if pyproject_metadata.get("keywords"):
            metadata["keywords"] = pyproject_metadata["keywords"]

        primary_files = self._collect_primary_files(node_path)
        if primary_files:
            metadata["primary_files"] = primary_files
            for rel_path in primary_files[:3]:
                absolute = os.path.join(node_path, rel_path)
                preview = self._read_text_file(absolute, max_chars=1000)
                if preview:
                    context_snippets.append({
                        "path": rel_path,
                        "type": "code",
                        "snippet": preview[:400]
                    })

        tests_dir = os.path.join(node_path, "tests")
        if os.path.isdir(tests_dir):
            try:
                test_files = []
                for root, _, files in os.walk(tests_dir):
                    depth = root.count(os.sep) - tests_dir.count(os.sep)
                    if depth > 1:
                        continue
                    for file in files:
                        if file.endswith((".py", ".yaml", ".yml")):
                            rel = os.path.relpath(os.path.join(root, file), node_path)
                            test_files.append(rel)
                            if len(test_files) >= 5:
                                break
                    if len(test_files) >= 5:
                        break
                if test_files:
                    metadata["tests"] = test_files
                    sample = test_files[0]
                    sample_path = os.path.join(node_path, sample)
                    preview = self._read_text_file(sample_path, max_chars=600)
                    if preview:
                        context_snippets.append({
                            "path": sample,
                            "type": "test",
                            "snippet": preview[:400]
                        })
            except Exception:
                pass

        metadata["has_configs"] = bool(metadata.get("config_files"))
        metadata["has_tests"] = bool(metadata.get("tests"))

        agent_pkg_path = os.path.join(node_path, "agent")
        metadata["has_agent_package"] = os.path.isdir(agent_pkg_path)

        dataflow_files = [path for path in metadata.get("config_files", []) if path.lower().endswith((".yml", ".yaml")) and "dataflow" in path.lower()]
        if dataflow_files:
            metadata["dataflows"] = dataflow_files
            metadata["has_dataflow"] = True

        # Clean empty values
        if context_snippets:
            metadata["context_snippets"] = context_snippets

        metadata = {k: v for k, v in metadata.items() if v}

        return {
            "description": selected_description,
            "metadata": metadata
        }

    def _list_templates_for_dir(self, base_dir):
        templates = []
        if not base_dir or not os.path.isdir(base_dir):
            return templates

        try:
            for entry in sorted(os.listdir(base_dir)):
                if entry.startswith('.') or entry.startswith('__'):
                    continue
                template_path = os.path.join(base_dir, entry)
                if not os.path.isdir(template_path):
                    continue

                metadata = self._collect_node_metadata(template_path)
                templates.append({
                    "name": entry,
                    "description": metadata.get("description") or f"Template: {entry}",
                    "metadata": metadata.get("metadata", {})
                })
        except Exception as exc:
            print(f"Error listing templates in {base_dir}: {exc}")

        return templates

    def list_agent_templates(self):
        """Gather available templates for agent creation."""
        try:
            hub_dirs = [self.agent_hub_dir] + self.additional_hub_dirs
            example_dirs = [self.examples_dir] + self.additional_example_dirs

            hub_templates = []
            for directory in hub_dirs:
                hub_templates.extend(self._list_templates_for_dir(directory))

            example_templates = []
            for directory in example_dirs:
                example_templates.extend(self._list_templates_for_dir(directory))

            # Remove duplicates by name while preserving order
            def deduplicate(items):
                seen = set()
                unique = []
                for item in items:
                    name = item.get("name")
                    if name in seen:
                        continue
                    seen.add(name)
                    unique.append(item)
                return unique

            return {
                "success": True,
                "templates": {
                    "agent-hub": deduplicate(hub_templates),
                    "examples": deduplicate(example_templates)
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "templates": {
                    "agent-hub": [],
                    "examples": []
                }
            }

    def search_repository(self, query, file_globs=None, max_results=120):
        """Search MoFA-related directories using ripgrep."""
        if not query or len(query.strip()) < 2:
            return {
                "success": False,
                "message": "Query must be at least 2 characters"
            }

        search_dirs = []
        candidates = [
            self.agent_hub_dir,
            self.examples_dir,
            self.mofa_dir,
        ] + self.additional_hub_dirs + self.additional_example_dirs

        for directory in candidates:
            if directory and os.path.isdir(directory):
                search_dirs.append(os.path.abspath(directory))

        # Deduplicate while preserving order
        seen = set()
        unique_dirs = []
        for directory in search_dirs:
            if directory not in seen:
                seen.add(directory)
                unique_dirs.append(directory)

        if not unique_dirs:
            return {
                "success": False,
                "message": "No searchable directories configured"
            }

        rg_command = [
            "rg",
            "--json",
            "--line-number",
            "--max-columns", "240",
            "--max-count", str(max_results),
            query
        ] + unique_dirs

        if file_globs:
            if isinstance(file_globs, str):
                file_globs = [file_globs]
            for pattern in file_globs:
                rg_command.extend(["--glob", pattern])

        try:
            process = subprocess.run(
                rg_command,
                capture_output=True,
                text=True,
                check=False
            )
        except FileNotFoundError:
            return {
                "success": False,
                "message": "ripgrep (rg) is not installed."
            }

        if process.returncode not in (0, 1):
            return {
                "success": False,
                "message": process.stderr.strip() or "ripgrep execution failed"
            }

        results = []
        for line in process.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue

            if payload.get("type") != "match":
                continue

            data = payload.get("data", {})
            path_text = data.get("path", {}).get("text")
            if not path_text:
                continue

            lines = data.get("lines", {}).get("text", "")
            line_number = data.get("line_number")

            # Normalize path relative to base directory
            relative_path = path_text
            for base_dir in unique_dirs:
                if path_text.startswith(base_dir):
                    relative_path = os.path.relpath(path_text, base_dir)
                    break

            results.append({
                "file": path_text,
                "relative_file": relative_path,
                "line": line_number,
                "preview": lines.strip()
            })

            if len(results) >= max_results:
                break

        return {
            "success": True,
            "results": results,
            "count": len(results)
        }

    def get_available_nodes(self):
        """获取所有可用的nodes列表及其描述"""
        try:
            nodes = []
            
            # 遍历agent-hub目录中的所有节点
            if os.path.exists(self.agent_hub_dir):
                for node_name in os.listdir(self.agent_hub_dir):
                    node_path = os.path.join(self.agent_hub_dir, node_name)
                    if os.path.isdir(node_path):
                        enriched = self._collect_node_metadata(node_path)

                        node_info = {
                            "name": node_name,
                            "type": "agent-hub",
                            "path": node_path,
                            "description": enriched.get("description") or f"Agent node: {node_name}"
                        }

                        metadata = enriched.get("metadata")
                        if metadata:
                            node_info["metadata"] = metadata

                        nodes.append(node_info)
            
            sorted_nodes = sorted(nodes, key=lambda x: x["name"])
            self._cached_nodes = sorted_nodes
            self._node_index.build(sorted_nodes)

            return {
                "success": True,
                "nodes": sorted_nodes
            }
        except Exception as e:
            print(f"获取可用nodes时出错: {e}")
            return {"success": False, "message": str(e)}

    def suggest_nodes(self, flow_description, limit=5):
        """提供基于描述的节点推荐"""
        if not flow_description or not flow_description.strip():
            return {
                "success": False,
                "message": "flow_description is required"
            }

        if not self._cached_nodes:
            available = self.get_available_nodes()
            if not available.get("success"):
                return available

        suggestions = self._node_index.search(flow_description, limit=limit or 5)
        if not suggestions:
            return {
                "success": True,
                "suggestions": []
            }

        node_lookup = {node.get("name"): node for node in self._cached_nodes}
        enriched = []
        for suggestion in suggestions:
            node = node_lookup.get(suggestion["name"], {})
            enriched.append({
                "name": suggestion["name"],
                "score": suggestion["score"],
                "description": node.get("description"),
                "metadata": node.get("metadata", {})
            })

        return {
            "success": True,
            "suggestions": enriched
        }

    def get_node_details(self, node_name):
        """返回指定节点的详细上下文信息"""
        if not node_name:
            return {"success": False, "message": "node_name is required"}

        if not self._cached_nodes:
            available = self.get_available_nodes()
            if not available.get("success"):
                return available

        for node in self._cached_nodes:
            if node.get("name") == node_name:
                return {"success": True, "node": node}

        return {"success": False, "message": f"Node {node_name} not found"}

    def _ensure_node_cache(self):
        """Return a lookup dict for cached nodes, refreshing if necessary."""
        if not self._cached_nodes:
            result = self.get_available_nodes()
            if not result.get("success"):
                return {}
        return {node.get("name"): node for node in self._cached_nodes}

    def _summarize_node_for_prompt(self, node_name, node_lookup):
        node = node_lookup.get(node_name, {})
        metadata = node.get("metadata", {}) or {}
        summary = {
            "name": node_name,
            "description": node.get("description", ""),
            "entry_points": metadata.get("entry_points", [])[:3],
            "dependencies": metadata.get("dependencies", [])[:5],
            "primary_files": metadata.get("primary_files", [])[:4],
            "config_files": metadata.get("config_files", [])[:4],
            "tests": metadata.get("tests", [])[:3],
            "doc_highlights": metadata.get("doc_highlights", [])[:3]
        }

        snippets = []
        for snippet in metadata.get("context_snippets", [])[:3]:
            snippet_text = snippet.get("snippet", "")
            if not snippet_text:
                continue
            snippets.append({
                "path": snippet.get("path"),
                "type": snippet.get("type"),
                "excerpt": snippet_text.strip()
            })

        if snippets:
            summary["context_snippets"] = snippets

        return summary

    def _fallback_dataflow(self, selected_nodes, flow_description, flow_name, node_lookup):
        """Construct a deterministic YAML when LLM generation is unavailable."""
        if not selected_nodes:
            return "", "No nodes provided"

        dataflow_nodes = []

        # Terminal input node anchors the flow
        dataflow_nodes.append({
            "id": "terminal-input",
            "build": "pip install -e ../../node-hub/terminal-input",
            "path": "dynamic",
            "outputs": ["data"],
            "inputs": {}
        })

        previous_output = "terminal-input/data"

        for index, node_name in enumerate(selected_nodes):
            node_id = node_name
            build_path = f"pip install -e ../../agent-hub/{node_name}"
            path = node_name

            metadata = node_lookup.get(node_name, {}).get("metadata", {}) if node_lookup else {}

            env = {"WRITE_LOG": True}
            if index == len(selected_nodes) - 1:
                env["IS_DATAFLOW_END"] = True

            node_entry = {
                "id": node_id,
                "build": build_path,
                "path": path,
                "outputs": [f"{node_id}_output"],
                "inputs": {
                    "input": previous_output
                },
                "env": env
            }

            if metadata.get("config_files"):
                node_entry["configs"] = metadata["config_files"][:2]

            dataflow_nodes.append(node_entry)
            previous_output = f"{node_id}/{node_id}_output"

        structure = {
            "name": flow_name or "generated_flow",
            "description": flow_description or "Generated via fallback",
            "version": "0.0.1",
            "nodes": dataflow_nodes
        }

        try:
            yaml_content = yaml.safe_dump(structure, sort_keys=False, allow_unicode=True)
        except Exception:
            yaml_content = ""

        message = "使用内置模板生成了基础 dataflow，请根据节点实际输入输出进行完善。"
        return yaml_content, message


    
    def generate_dataflow_with_gemini(self, selected_nodes, flow_description, flow_name):
        """使用Gemini API基于选择的nodes和描述生成dataflow"""
        try:
            node_lookup = self._ensure_node_cache()

            from routes.settings import get_settings
            settings = get_settings()
            api_key = settings.get('gemini_api_key')
            api_endpoint = settings.get('gemini_api_endpoint', 'https://generativelanguage.googleapis.com/v1beta')

            highlighted_nodes = [self._summarize_node_for_prompt(node, node_lookup) for node in selected_nodes]

            if not api_key:
                yaml_content, message = self._fallback_dataflow(selected_nodes, flow_description, flow_name, node_lookup)
                return {
                    "success": True if yaml_content else False,
                    "message": "Gemini API 未配置，已使用内置模板生成基础 dataflow。" if yaml_content else message,
                    "yaml_content": yaml_content,
                    "dataflow_path": None,
                    "source": "fallback"
                }

            node_context_json = json.dumps(highlighted_nodes, ensure_ascii=False, indent=2)

            prompt = f"""
你是 MoFA Stage 的系统架构师，需要根据用户需求和节点上下文生成工业级 dataflow。

用户需求: {flow_description}
目标 dataflow 名称: {flow_name}

候选节点上下文:
{node_context_json}

生成要求:
- 输出纯 YAML，可直接保存为 `*_dataflow.yml`。
- 首个节点必须是 `terminal-input` 并暴露 `data` 输出。
- 其余节点按照上下文推断 `build`, `path`, `inputs`, `outputs`；若信息不足可使用占位符但需在注释或 env 中标注待确认内容。
- 末节点需声明 `env.IS_DATAFLOW_END = true`，所有节点默认包含 `env.WRITE_LOG = true`。
- 若节点包含测试、配置或关键文件，请在 YAML 中体现为 `configs` 或注释，以指导后续完善。
- 结构示例：
```yaml
name: {flow_name}
version: 0.0.1
description: <简短概述>
nodes:
  - id: terminal-input
    build: pip install -e ../../node-hub/terminal-input
    path: dynamic
    outputs: [data]
  - id: <another-node>
    build: pip install -e ../../agent-hub/<another-node>
    path: <path>
    inputs:
      <input_key>: terminal-input/data
    outputs:
      - <output_key>
    env:
      WRITE_LOG: true
      # IS_DATAFLOW_END: true  # 仅在最后节点设置
```

仅输出最终 YAML，不要附加解释文字。
"""

            ai_model = settings.get('ai_model', 'gemini-2.0-flash')
            url = f"{api_endpoint}/models/{ai_model}:generateContent"
            headers = {'Content-Type': 'application/json'}
            payload = {
                "safetySettings": [
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ],
                "contents": [{"parts": [{"text": prompt}]}]
            }

            response = requests.post(
                f"{url}?key={api_key}",
                headers=headers,
                data=json.dumps(payload)
            )

            if response.status_code != 200:
                yaml_content, message = self._fallback_dataflow(selected_nodes, flow_description, flow_name, node_lookup)
                return {
                    "success": True if yaml_content else False,
                    "message": f"Gemini API调用失败 ({response.status_code})，{message}",
                    "yaml_content": yaml_content,
                    "dataflow_path": None,
                    "source": "fallback"
                }

            result = response.json()

            if 'candidates' not in result or len(result['candidates']) == 0:
                yaml_content, message = self._fallback_dataflow(selected_nodes, flow_description, flow_name, node_lookup)
                return {
                    "success": True if yaml_content else False,
                    "message": f"Gemini API 未返回结果，{message}",
                    "yaml_content": yaml_content,
                    "dataflow_path": None,
                    "source": "fallback"
                }

            generated_content = result['candidates'][0]['content']['parts'][0]['text']
            yaml_content = generated_content
            if '```yaml' in yaml_content:
                yaml_content = yaml_content.split('```yaml', 1)[1]
                if '```' in yaml_content:
                    yaml_content = yaml_content.split('```', 1)[0]

            yaml_content = yaml_content.strip()

            if not yaml_content:
                yaml_content, message = self._fallback_dataflow(selected_nodes, flow_description, flow_name, node_lookup)
                return {
                    "success": True if yaml_content else False,
                    "message": f"生成内容为空，{message}",
                    "yaml_content": yaml_content,
                    "dataflow_path": None,
                    "source": "fallback"
                }

            dataflow_dir = os.path.join(self.examples_dir, flow_name)
            os.makedirs(dataflow_dir, exist_ok=True)
            dataflow_file_path = os.path.join(dataflow_dir, f"{flow_name}_dataflow.yml")

            if os.path.exists(dataflow_file_path):
                timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                dataflow_file_path = os.path.join(
                    dataflow_dir,
                    f"{flow_name}_dataflow_{timestamp}.yml"
                )

            with open(dataflow_file_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)

            return {
                "success": True,
                "message": f"Dataflow '{flow_name}' generated successfully",
                "dataflow_path": dataflow_dir,
                "yaml_content": yaml_content,
                "source": "gemini",
                "nodes_used": highlighted_nodes
            }
        except Exception as e:
            yaml_content, message = self._fallback_dataflow(selected_nodes, flow_description, flow_name, self._ensure_node_cache())
            return {
                "success": True if yaml_content else False,
                "message": f"生成dataflow失败: {str(e)}。{message}",
                "yaml_content": yaml_content,
                "dataflow_path": None,
                "source": "fallback"
            }
