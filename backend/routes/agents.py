"""
Agent 相关的 API 路由
"""
from flask import Blueprint, request, jsonify, send_file
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.mofa_cli import MofaCLI
from utils.file_ops import read_file, write_file, get_file_type, delete_path, rename_path
from routes.settings import get_settings

agents_bp = Blueprint('agents', __name__, url_prefix='/api/agents')

# 从设置中获取配置参数初始化MofaCLI
def get_mofa_cli():
    settings = get_settings()
    return MofaCLI(settings)

@agents_bp.route('/', methods=['GET'])
def get_agents():
    """获取所有 agents 列表，按来源分类"""
    mofa_cli = get_mofa_cli()
    agents_data = mofa_cli.list_agents()
    return jsonify({
        "success": True, 
        "hub_agents": agents_data["hub_agents"],
        "example_agents": agents_data["example_agents"]
    })

@agents_bp.route('/<agent_name>', methods=['GET'])
def get_agent_details(agent_name):
    """获取指定 agent 的详细信息"""
    mofa_cli = get_mofa_cli()
    details = mofa_cli.get_agent_details(agent_name)
    if details:
        return jsonify({"success": True, "agent": details})
    else:
        return jsonify({"success": False, "message": f"Agent {agent_name} not found"}), 404

@agents_bp.route('/', methods=['POST'])
def create_agent():
    """创建新的 agent"""
    data = request.json
    agent_name = data.get('name')
    version = data.get('version', '0.0.1')
    authors = data.get('authors', 'MoFA_Stage User')
    agent_type = data.get('agent_type', 'agent-hub')  # 默认为 agent-hub 类型
    
    if not agent_name:
        return jsonify({"success": False, "message": "Agent name is required"}), 400
    
    # 验证 agent_type 是否有效
    if agent_type not in ['agent-hub', 'examples']:
        return jsonify({"success": False, "message": "Invalid agent_type. Must be 'agent-hub' or 'examples'"}), 400
    
    mofa_cli = get_mofa_cli()
    result = mofa_cli.create_agent(agent_name, version, authors, agent_type)
    return jsonify(result)

@agents_bp.route('/copy', methods=['POST'])
def copy_agent():
    """复制现有 agent"""
    data = request.json
    source_agent = data.get('source')
    target_agent = data.get('target')
    agent_type = data.get('agent_type')  # 可以是 None，这样会自动检测源 Agent 的类型
    
    if not source_agent or not target_agent:
        return jsonify({"success": False, "message": "Source and target agent names are required"}), 400
    
    # 如果指定了 agent_type，验证其是否有效
    if agent_type is not None and agent_type not in ['agent-hub', 'examples']:
        return jsonify({"success": False, "message": "Invalid agent_type. Must be 'agent-hub' or 'examples'"}), 400
    
    mofa_cli = get_mofa_cli()
    result = mofa_cli.copy_agent(source_agent, target_agent, agent_type)
    return jsonify(result)

@agents_bp.route('/<agent_name>', methods=['DELETE'])
def delete_agent(agent_name):
    """删除指定 agent"""
    mofa_cli = get_mofa_cli()
    result = mofa_cli.delete_agent(agent_name)
    return jsonify(result)

@agents_bp.route('/<agent_name>/run', methods=['POST'])
def run_agent(agent_name):
    """运行指定的 agent或示例"""
    data = request.json
    timeout = data.get('timeout', 5)  # 默认超时5秒
    agent_type = data.get('agent_type', 'auto')  # 默认自动检测类型
    
    mofa_cli = get_mofa_cli()
    
    # 根据类型或自动检测运行不同的agent
    if agent_type == 'example':
        # 明确指定为示例，直接运行示例
        result = mofa_cli.run_example(agent_name, timeout)
    elif agent_type == 'atomic':
        # 明确指定为原子化agent，直接运行原子化agent
        result = mofa_cli.run_agent(agent_name, timeout)
    else:
        # 自动检测类型
        # 首先检查是否为原子化agent
        agent_path = os.path.join(mofa_cli.agent_hub_dir, agent_name)
        if os.path.exists(agent_path) and os.path.isdir(agent_path):
            result = mofa_cli.run_agent(agent_name, timeout)
        else:
            # 检查是否为示例
            example_path = os.path.join(mofa_cli.examples_dir, agent_name)
            if os.path.exists(example_path) and os.path.isdir(example_path):
                result = mofa_cli.run_example(agent_name, timeout)
            else:
                # 都不存在，返回错误
                result = {
                    "success": False,
                    "message": f"Agent or example '{agent_name}' not found in either agent-hub or examples directory"
                }
    
    return jsonify(result)

@agents_bp.route('/<agent_name>/logs', methods=['GET'])
def get_agent_logs(agent_name):
    """获取指定agent的运行日志"""
    try:
        mofa_cli = get_mofa_cli()
        logs = mofa_cli.get_agent_logs(agent_name)
        
        # 即使日志为None也返回空字符串而不是404
        if logs is None:
            logs = f"未找到 {agent_name} 的日志文件。可能是该Agent还未运行过。"
        
        return jsonify({"success": True, "logs": logs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "logs": "获取日志时出错"})

@agents_bp.route('/<agent_name>/process-output', methods=['GET'])
def get_process_output(agent_name):
    """获取正在运行的进程的输出"""
    mofa_cli = get_mofa_cli()
    result = mofa_cli.get_process_output(agent_name)
    return jsonify(result)

@agents_bp.route('/stop/<process_id>', methods=['POST'])
def stop_agent(process_id):
    """停止正在运行的 agent"""
    mofa_cli = get_mofa_cli()
    result = mofa_cli.stop_agent(process_id)
    return jsonify(result)

@agents_bp.route('/<agent_name>/files', methods=['GET'])
def get_agent_files(agent_name):
    """获取 agent 的所有文件"""
    agent_type = request.args.get('agent_type')  # 获取agent类型参数
    mofa_cli = get_mofa_cli()
    details = mofa_cli.get_agent_details(agent_name, agent_type)
    if not details:
        return jsonify({"success": False, "message": f"Agent {agent_name} not found"}), 404
    
    return jsonify({"success": True, "files": details.get('files', [])})

@agents_bp.route('/<agent_name>/files/<path:file_path>', methods=['GET'])
def get_file_content(agent_name, file_path):
    """获取文件内容"""
    agent_type = request.args.get('agent_type')  # 获取agent类型参数
    
    # 检查是否为图片或视频文件
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico']
    video_extensions = ['.mp4', '.webm', '.ogg', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp']
    is_image = any(file_path.lower().endswith(ext) for ext in image_extensions)
    is_video = any(file_path.lower().endswith(ext) for ext in video_extensions)
    
    if is_image or is_video:
        # 对于图片或视频文件，直接返回二进制数据
        mofa_cli = get_mofa_cli()
        # 确定文件的完整路径
        candidate_dirs = [mofa_cli.agent_hub_dir, mofa_cli.examples_dir]
        full_path = None
        
        for base_dir in candidate_dirs:
            potential_path = os.path.join(base_dir, agent_name, file_path)
            if os.path.exists(potential_path) and os.path.isfile(potential_path):
                full_path = potential_path
                break
        
        if full_path:
            try:
                return send_file(full_path, as_attachment=False)
            except Exception as e:
                return jsonify({"success": False, "message": str(e)}), 500
        else:
            file_type = "Video" if is_video else "Image"
            return jsonify({"success": False, "message": f"{file_type} file not found"}), 404
    else:
        # 对于文本文件，使用原有逻辑
        mofa_cli = get_mofa_cli()
        result = mofa_cli.read_file(agent_name, file_path, agent_type)
        if result.get('success'):
            file_type = get_file_type(file_path)
            return jsonify({
                "success": True, 
                "content": result.get('content'),
                "type": file_type
            })
        else:
            return jsonify(result), 404

@agents_bp.route('/<agent_name>/files/<path:file_path>', methods=['PUT'])
def update_file_content(agent_name, file_path):
    """更新文件内容"""
    if not request.is_json:
        return jsonify({"success": False, "message": "Content must be JSON"}), 400
    
    content = request.json.get('content')
    if content is None:
        return jsonify({"success": False, "message": "Content is required"}), 400
    
    mofa_cli = get_mofa_cli()
    result = mofa_cli.write_file(agent_name, file_path, content)
    return jsonify(result)

@agents_bp.route('/<agent_name>/files/<path:file_path>', methods=['DELETE'])
def delete_file_or_folder(agent_name, file_path):
    """删除文件或文件夹"""
    mofa_cli = get_mofa_cli()
    # 可能的base路径
    candidate_dirs = [mofa_cli.agent_hub_dir, mofa_cli.examples_dir]
    full_path = None
    for base in candidate_dirs:
        p = os.path.join(base, agent_name, file_path)
        if os.path.exists(p):
            full_path = p
            break
    if not full_path:
        return jsonify({"success": False, "message": "File or folder not found"}), 404
    try:
        if delete_path(full_path):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Delete failed"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@agents_bp.route('/<agent_name>/dataflow-file', methods=['GET'])
def get_dataflow_file(agent_name):
    """获取 agent 目录中的 dataflow YAML 文件名"""
    mofa_cli = get_mofa_cli()
    
    # 检查示例是否存在
    settings = mofa_cli.settings
    examples_path = settings.get('custom_examples_path') or settings.get('examples_path') or os.path.join(settings.get('mofa_dir', ''), 'python', 'examples')
    agent_path = os.path.join(examples_path, agent_name)
    
    if not os.path.exists(agent_path) or not os.path.isdir(agent_path):
        return jsonify({"success": False, "message": f"Agent {agent_name} not found in examples directory"}), 404
    
    try:
        # 查找 dataflow 配置文件，优先查找 _dataflow.yml，然后查找所有 .yml 文件
        dataflow_files = []
        
        # 首先查找符合命名约定的文件
        for filename in os.listdir(agent_path):
            if filename.endswith('_dataflow.yml'):
                dataflow_files.append(filename)
        
        # 如果没找到，查找所有 .yml 和 .yaml 文件
        if not dataflow_files:
            for filename in os.listdir(agent_path):
                if filename.endswith('.yml') or filename.endswith('.yaml'):
                    dataflow_files.append(filename)
        
        if not dataflow_files:
            return jsonify({
                "success": False,
                "message": f"No dataflow configuration file found in {agent_name}"
            }), 404
        
        # 返回第一个找到的文件（与后端运行逻辑保持一致）
        dataflow_file = dataflow_files[0]
        
        return jsonify({
            "success": True,
            "dataflow_file": dataflow_file,
            "agent_path": agent_path,
            "all_dataflow_files": dataflow_files
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@agents_bp.route('/<agent_name>/files/<path:file_path>/rename', methods=['POST'])
def rename_file_or_folder(agent_name, file_path):
    """重命名文件或文件夹"""
    if not request.is_json:
        return jsonify({"success": False, "message": "Content must be JSON"}), 400
    
    new_name = request.json.get('new_name')
    if not new_name:
        return jsonify({"success": False, "message": "New name is required"}), 400
    
    mofa_cli = get_mofa_cli()
    # 可能的base路径
    candidate_dirs = [mofa_cli.agent_hub_dir, mofa_cli.examples_dir]
    old_full_path = None
    base_dir = None
    
    for base in candidate_dirs:
        p = os.path.join(base, agent_name, file_path)
        if os.path.exists(p):
            old_full_path = p
            base_dir = base
            break
    
    if not old_full_path:
        return jsonify({"success": False, "message": "File or folder not found"}), 404
    
    # 构建新的完整路径
    path_parts = file_path.split('/')
    path_parts[-1] = new_name  # 替换最后一部分（文件名）
    new_file_path = '/'.join(path_parts)
    new_full_path = os.path.join(base_dir, agent_name, new_file_path)
    
    try:
        success, message = rename_path(old_full_path, new_full_path)
        if success:
            return jsonify({
                "success": True, 
                "message": message,
                "new_path": new_file_path
            })
        else:
            return jsonify({"success": False, "message": message}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@agents_bp.route('/generate-dataflow', methods=['POST'])
def generate_dataflow():
    """基于用户选择的nodes和描述，使用Gemini API自动生成dataflow"""
    data = request.json
    selected_nodes = data.get('selected_nodes', [])
    flow_description = data.get('flow_description', '')
    flow_name = data.get('flow_name', '')
    
    if not selected_nodes or not flow_description or not flow_name:
        return jsonify({
            "success": False, 
            "message": "Missing required parameters: selected_nodes, flow_description, flow_name"
        }), 400
    
    mofa_cli = get_mofa_cli()
    result = mofa_cli.generate_dataflow_with_gemini(selected_nodes, flow_description, flow_name)
    return jsonify(result)

@agents_bp.route('/available-nodes', methods=['GET'])
def get_available_nodes():
    """获取所有可用的nodes列表及其描述"""
    mofa_cli = get_mofa_cli()
    result = mofa_cli.get_available_nodes()
    return jsonify(result)
