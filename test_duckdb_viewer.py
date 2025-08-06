#!/usr/bin/env python3
"""
DuckDB数据库内容查看器 - 独立测试脚本
"""
from flask import Flask, render_template_string, jsonify
import duckdb
import json
from datetime import datetime

app = Flask(__name__)

# DuckDB文件路径
DB_PATH = "/Users/liyao/Code/mofa/mofa_old/mofa/python/examples/hello_world/logs.duckdb"
TABLE_NAME = "log_table"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>DuckDB数据库查看器</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-number { font-size: 24px; font-weight: bold; color: #409eff; }
        .stat-label { color: #666; margin-top: 5px; }
        .node-card { background: white; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .node-header { background: #409eff; color: white; padding: 15px; border-radius: 8px 8px 0 0; }
        .node-content { padding: 20px; }
        .variable-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 15px; }
        .variable-card { border: 1px solid #eee; border-radius: 6px; padding: 15px; }
        .variable-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .variable-name { font-weight: bold; font-size: 16px; }
        .variable-type { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .type-input { background: #67c23a; color: white; }
        .type-output { background: #e6a23c; color: white; }
        .variable-value { background: #f8f9fa; border-radius: 4px; padding: 10px; font-family: monospace; white-space: pre-wrap; margin-bottom: 10px; }
        .variable-time { color: #666; font-size: 12px; }
        .records-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .records-table th, .records-table td { padding: 8px 12px; border: 1px solid #ddd; text-align: left; }
        .records-table th { background: #f8f9fa; font-weight: bold; }
        .records-table tr:nth-child(even) { background: #f9f9f9; }
        .refresh-btn { background: #409eff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        .refresh-btn:hover { background: #337ecc; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗄️ DuckDB数据库查看器</h1>
            <p>数据库文件: <code>{{ db_path }}</code></p>
            <button class="refresh-btn" onclick="location.reload()">🔄 刷新数据</button>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_records }}</div>
                <div class="stat-label">总记录数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_nodes }}</div>
                <div class="stat-label">节点数量</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.input_vars }}</div>
                <div class="stat-label">输入变量</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.output_vars }}</div>
                <div class="stat-label">输出变量</div>
            </div>
        </div>

        {% for node in nodes %}
        <div class="node-card">
            <div class="node-header">
                <h2>📦 节点: {{ node.name }}</h2>
                <span>{{ node.record_count }} 条记录 | 最后活动: {{ node.last_activity }}</span>
            </div>
            <div class="node-content">
                <h3>🔧 当前变量值</h3>
                <div class="variable-grid">
                    {% for var_name, var_data in node.variables.items() %}
                    <div class="variable-card">
                        <div class="variable-header">
                            <span class="variable-name">{{ var_name }}</span>
                            <span class="variable-type type-{{ var_data.type }}">{{ var_data.type }}</span>
                        </div>
                        <div class="variable-value">{{ var_data.display_value }}</div>
                        <div class="variable-time">⏰ {{ var_data.time }}</div>
                    </div>
                    {% endfor %}
                </div>

                <h3>📋 历史记录</h3>
                <table class="records-table">
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>输入变量</th>
                            <th>输入值</th>
                            <th>输出变量</th>
                            <th>输出值</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for record in node.history %}
                        <tr>
                            <td>{{ record.time }}</td>
                            <td>{{ record.input_name or '-' }}</td>
                            <td>{{ record.input_value or '-' }}</td>
                            <td>{{ record.output_name or '-' }}</td>
                            <td>{{ record.output_value or '-' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

def get_database_data():
    """获取数据库的完整数据"""
    try:
        conn = duckdb.connect(DB_PATH)
        
        # 基础统计
        total_records = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        total_nodes = conn.execute(f"SELECT COUNT(DISTINCT node_name) FROM {TABLE_NAME}").fetchone()[0]
        input_vars = conn.execute(f"SELECT COUNT(DISTINCT input_name) FROM {TABLE_NAME} WHERE input_name IS NOT NULL").fetchone()[0]
        output_vars = conn.execute(f"SELECT COUNT(DISTINCT output_name) FROM {TABLE_NAME} WHERE output_name IS NOT NULL").fetchone()[0]
        
        stats = {
            'total_records': total_records,
            'total_nodes': total_nodes,
            'input_vars': input_vars,
            'output_vars': output_vars
        }
        
        # 获取所有节点
        nodes_query = f"""
            SELECT DISTINCT node_name, 
                   COUNT(*) as record_count,
                   MAX(time) as last_activity
            FROM {TABLE_NAME} 
            GROUP BY node_name 
            ORDER BY last_activity DESC
        """
        node_results = conn.execute(nodes_query).fetchall()
        
        nodes = []
        for node_name, record_count, last_activity in node_results:
            # 获取该节点的当前变量
            variables = get_node_variables(conn, node_name)
            
            # 获取该节点的历史记录
            history_query = f"""
                SELECT time, input_name, input_value, output_name, output_value
                FROM {TABLE_NAME}
                WHERE node_name = ?
                ORDER BY time DESC
                LIMIT 20
            """
            history_results = conn.execute(history_query, [node_name]).fetchall()
            
            history = []
            for time, input_name, input_value, output_name, output_value in history_results:
                history.append({
                    'time': time,
                    'input_name': input_name,
                    'input_value': input_value,
                    'output_name': output_name,
                    'output_value': output_value
                })
            
            nodes.append({
                'name': node_name,
                'record_count': record_count,
                'last_activity': last_activity,
                'variables': variables,
                'history': history
            })
        
        conn.close()
        return stats, nodes
        
    except Exception as e:
        print(f"数据库查询错误: {e}")
        return None, None

def get_node_variables(conn, node_name):
    """获取节点的当前变量值"""
    variables = {}
    
    # 输入变量查询
    input_query = f"""
        SELECT input_name, input_value, time
        FROM {TABLE_NAME} 
        WHERE node_name = ? AND input_name IS NOT NULL AND input_value IS NOT NULL
        AND (node_name, input_name, time) IN (
            SELECT node_name, input_name, MAX(time) 
            FROM {TABLE_NAME} 
            WHERE node_name = ? AND input_name IS NOT NULL 
            GROUP BY node_name, input_name
        )
    """
    
    # 输出变量查询
    output_query = f"""
        SELECT output_name, output_value, time
        FROM {TABLE_NAME} 
        WHERE node_name = ? AND output_name IS NOT NULL AND output_value IS NOT NULL
        AND (node_name, output_name, time) IN (
            SELECT node_name, output_name, MAX(time) 
            FROM {TABLE_NAME} 
            WHERE node_name = ? AND output_name IS NOT NULL 
            GROUP BY node_name, output_name
        )
    """
    
    # 处理输入变量
    input_results = conn.execute(input_query, [node_name, node_name]).fetchall()
    for var_name, var_value, time in input_results:
        try:
            parsed_value = json.loads(var_value)
            display_value = json.dumps(parsed_value, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            parsed_value = var_value
            display_value = str(var_value)
        
        variables[var_name] = {
            'value': parsed_value,
            'display_value': display_value,
            'time': time,
            'type': 'input'
        }
    
    # 处理输出变量
    output_results = conn.execute(output_query, [node_name, node_name]).fetchall()
    for var_name, var_value, time in output_results:
        try:
            parsed_value = json.loads(var_value)
            display_value = json.dumps(parsed_value, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            parsed_value = var_value
            display_value = str(var_value)
        
        # 如果同时有输入和输出，选择时间更新的
        if var_name in variables:
            if time > variables[var_name]["time"]:
                variables[var_name] = {
                    'value': parsed_value,
                    'display_value': display_value,
                    'time': time,
                    'type': 'output'
                }
        else:
            variables[var_name] = {
                'value': parsed_value,
                'display_value': display_value,
                'time': time,
                'type': 'output'
            }
    
    return variables

@app.route('/')
def index():
    """主页面"""
    stats, nodes = get_database_data()
    
    if stats is None:
        return "❌ 数据库连接失败或数据读取错误", 500
    
    return render_template_string(HTML_TEMPLATE, 
                                db_path=DB_PATH,
                                stats=stats, 
                                nodes=nodes)

@app.route('/api/data')
def api_data():
    """API接口返回JSON数据"""
    stats, nodes = get_database_data()
    
    if stats is None:
        return jsonify({"error": "数据库连接失败"}), 500
    
    return jsonify({
        "stats": stats,
        "nodes": nodes
    })

if __name__ == '__main__':
    print(f"🚀 启动DuckDB查看器...")
    print(f"📂 数据库文件: {DB_PATH}")
    print(f"🌐 访问地址: http://localhost:8888")
    
    app.run(host='0.0.0.0', port=8888, debug=True)