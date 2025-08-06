"""
DuckDB查询相关的 API 路由
与现有的Agent日志数据库集成，支持变量监控
"""
from flask import Blueprint, request, jsonify
import os
import duckdb
import json
from pathlib import Path

duckdb_bp = Blueprint('duckdb', __name__, url_prefix='/api/agents/duckdb')

def get_duckdb_connection(db_file_path=None):
    """获取DuckDB连接，支持指定具体的数据库文件路径"""
    if db_file_path:
        # 如果指定了具体的数据库文件路径，直接使用
        if not os.path.isabs(db_file_path):
            # 如果是相对路径，基于当前工作目录
            db_file_path = os.path.abspath(db_file_path)
        
        if not os.path.exists(db_file_path):
            return None
            
        try:
            return duckdb.connect(db_file_path)
        except Exception as e:
            print(f"Failed to connect to DuckDB at {db_file_path}: {e}")
            return None
    else:
        # 向后兼容：使用环境变量或默认路径
        db_path = os.getenv('LOG_DB_PATH', 'logs.duckdb')
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
        
        try:
            return duckdb.connect(db_path)
        except Exception as e:
            print(f"Failed to connect to DuckDB at {db_path}: {e}")
            return None

def get_table_name():
    """获取日志表名，使用与Agent相同的配置"""
    return os.getenv('LOG_DB_TABLE_NAME', 'log_table')

@duckdb_bp.route('/latest/<node_id>/<variable_name>', methods=['GET'])
def get_latest_variable_value(node_id, variable_name):
    """获取指定节点的变量最新值"""
    try:
        conn = get_duckdb_connection()
        if conn is None:
            return jsonify({
                "success": False,
                "message": "DuckDB database not found or not accessible"
            }), 404
        
        table_name = get_table_name()
        
        # 查询最新的输入值
        input_query = f"""
            SELECT input_value, time 
            FROM {table_name} 
            WHERE node_name = ? AND input_name = ? AND input_value IS NOT NULL
            ORDER BY time DESC 
            LIMIT 1
        """
        
        # 查询最新的输出值
        output_query = f"""
            SELECT output_value, time 
            FROM {table_name} 
            WHERE node_name = ? AND output_name = ? AND output_value IS NOT NULL
            ORDER BY time DESC 
            LIMIT 1
        """
        
        input_result = conn.execute(input_query, [node_id, variable_name]).fetchone()
        output_result = conn.execute(output_query, [node_id, variable_name]).fetchone()
        
        conn.close()
        
        # 选择最新的值（输入或输出中时间最新的）
        latest_value = None
        latest_time = None
        value_type = None
        
        if input_result and output_result:
            input_time = input_result[1]
            output_time = output_result[1]
            if input_time >= output_time:
                latest_value = input_result[0]
                latest_time = input_time
                value_type = 'input'
            else:
                latest_value = output_result[0]
                latest_time = output_time
                value_type = 'output'
        elif input_result:
            latest_value = input_result[0]
            latest_time = input_result[1]
            value_type = 'input'
        elif output_result:
            latest_value = output_result[0]
            latest_time = output_result[1]
            value_type = 'output'
        
        if latest_value is not None:
            # 尝试解析JSON值
            try:
                parsed_value = json.loads(latest_value)
            except (json.JSONDecodeError, TypeError):
                parsed_value = latest_value
            
            return jsonify({
                "success": True,
                "value": parsed_value,
                "time": latest_time,
                "type": value_type,
                "node_id": node_id,
                "variable_name": variable_name
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Variable {variable_name} not found for node {node_id}"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Database error: {str(e)}"
        }), 500

@duckdb_bp.route('/history/<node_id>/<variable_name>', methods=['GET'])
def get_variable_history(node_id, variable_name):
    """获取变量的历史记录"""
    try:
        # 获取查询参数
        limit = request.args.get('limit', 50, type=int)
        value_type = request.args.get('type', 'both')  # 'input', 'output', 'both'
        
        conn = get_duckdb_connection()
        if conn is None:
            return jsonify({
                "success": False,
                "message": "DuckDB database not found"
            }), 404
        
        table_name = get_table_name()
        history = []
        
        # 根据类型查询不同的数据
        if value_type in ['input', 'both']:
            input_query = f"""
                SELECT input_value as value, time, 'input' as type 
                FROM {table_name} 
                WHERE node_name = ? AND input_name = ? AND input_value IS NOT NULL
                ORDER BY time DESC 
                LIMIT ?
            """
            input_results = conn.execute(input_query, [node_id, variable_name, limit]).fetchall()
            
            for value, time, val_type in input_results:
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed_value = value
                
                history.append({
                    "value": parsed_value,
                    "time": time,
                    "type": val_type
                })
        
        if value_type in ['output', 'both']:
            output_query = f"""
                SELECT output_value as value, time, 'output' as type 
                FROM {table_name} 
                WHERE node_name = ? AND output_name = ? AND output_value IS NOT NULL
                ORDER BY time DESC 
                LIMIT ?
            """
            output_results = conn.execute(output_query, [node_id, variable_name, limit]).fetchall()
            
            for value, time, val_type in output_results:
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed_value = value
                
                history.append({
                    "value": parsed_value,
                    "time": time,
                    "type": val_type
                })
        
        conn.close()
        
        # 按时间排序
        history.sort(key=lambda x: x['time'], reverse=True)
        history = history[:limit]  # 应用限制
        
        return jsonify({
            "success": True,
            "history": history,
            "count": len(history),
            "node_id": node_id,
            "variable_name": variable_name
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to get variable history: {str(e)}"
        }), 500

@duckdb_bp.route('/node/<node_id>/variables', methods=['GET'])
def get_node_all_variables(node_id):
    """获取指定节点的所有当前变量"""
    try:
        conn = get_duckdb_connection()
        if conn is None:
            return jsonify({
                "success": False,
                "message": "DuckDB database not found"
            }), 404
        
        table_name = get_table_name()
        
        # 获取所有输入变量的最新值
        input_query = f"""
            SELECT input_name, input_value, time
            FROM {table_name} 
            WHERE node_name = ? AND input_name IS NOT NULL AND input_value IS NOT NULL
            AND (node_name, input_name, time) IN (
                SELECT node_name, input_name, MAX(time) 
                FROM {table_name} 
                WHERE node_name = ? AND input_name IS NOT NULL 
                GROUP BY node_name, input_name
            )
        """
        
        # 获取所有输出变量的最新值
        output_query = f"""
            SELECT output_name, output_value, time
            FROM {table_name} 
            WHERE node_name = ? AND output_name IS NOT NULL AND output_value IS NOT NULL
            AND (node_name, output_name, time) IN (
                SELECT node_name, output_name, MAX(time) 
                FROM {table_name} 
                WHERE node_name = ? AND output_name IS NOT NULL 
                GROUP BY node_name, output_name
            )
        """
        
        input_results = conn.execute(input_query, [node_id, node_id]).fetchall()
        output_results = conn.execute(output_query, [node_id, node_id]).fetchall()
        
        conn.close()
        
        variables = {}
        
        # 处理输入变量
        for var_name, var_value, time in input_results:
            try:
                parsed_value = json.loads(var_value)
            except (json.JSONDecodeError, TypeError):
                parsed_value = var_value
            
            variables[var_name] = {
                "value": parsed_value,
                "time": time,
                "type": "input"
            }
        
        # 处理输出变量
        for var_name, var_value, time in output_results:
            try:
                parsed_value = json.loads(var_value)
            except (json.JSONDecodeError, TypeError):
                parsed_value = var_value
            
            # 如果同时有输入和输出，选择时间更新的
            if var_name in variables:
                if time > variables[var_name]["time"]:
                    variables[var_name] = {
                        "value": parsed_value,
                        "time": time,
                        "type": "output"
                    }
            else:
                variables[var_name] = {
                    "value": parsed_value,
                    "time": time,
                    "type": "output"
                }
        
        return jsonify({
            "success": True,
            "node_id": node_id,
            "variables": variables,
            "count": len(variables)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to get node variables: {str(e)}"
        }), 500

@duckdb_bp.route('/nodes', methods=['GET'])
def get_all_nodes():
    """获取数据库中所有的节点列表"""
    try:
        conn = get_duckdb_connection()
        if conn is None:
            return jsonify({
                "success": False,
                "message": "DuckDB database not found"
            }), 404
        
        table_name = get_table_name()
        
        query = f"""
            SELECT DISTINCT node_name, 
                   COUNT(*) as record_count,
                   MAX(time) as last_activity
            FROM {table_name} 
            GROUP BY node_name 
            ORDER BY last_activity DESC
        """
        
        results = conn.execute(query).fetchall()
        conn.close()
        
        nodes = []
        for node_name, record_count, last_activity in results:
            nodes.append({
                "node_name": node_name,
                "record_count": record_count,
                "last_activity": last_activity
            })
        
        return jsonify({
            "success": True,
            "nodes": nodes,
            "count": len(nodes)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to get nodes: {str(e)}"
        }), 500

@duckdb_bp.route('/file/stats', methods=['GET']) 
def get_file_database_stats():
    """获取指定文件的数据库统计信息"""
    try:
        db_file_path = request.args.get('path')
        if not db_file_path:
            return jsonify({
                "success": False,
                "message": "Missing 'path' parameter"
            }), 400
            
        conn = get_duckdb_connection(db_file_path)
        if conn is None:
            return jsonify({
                "success": False,
                "message": f"DuckDB database not found at {db_file_path}"
            }), 404
        
        table_name = get_table_name()
        
        try:
            # 获取总记录数
            total_query = f"SELECT COUNT(*) FROM {table_name}"
            total_records = conn.execute(total_query).fetchone()[0]
            
            # 获取节点数量
            nodes_query = f"SELECT COUNT(DISTINCT node_name) FROM {table_name}"
            total_nodes = conn.execute(nodes_query).fetchone()[0]
            
            # 获取时间范围
            time_range_query = f"SELECT MIN(time), MAX(time) FROM {table_name}"
            time_range = conn.execute(time_range_query).fetchone()
            
            conn.close()
            
            return jsonify({
                "success": True,
                "stats": {
                    "total_records": total_records,
                    "total_nodes": total_nodes,
                    "earliest_record": time_range[0],
                    "latest_record": time_range[1],
                    "database_path": db_file_path,
                    "table_name": table_name
                }
            })
        except Exception as e:
            conn.close()
            return jsonify({
                "success": False,
                "message": f"Database query error: {str(e)}"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to get database stats: {str(e)}"
        }), 500

@duckdb_bp.route('/file/nodes', methods=['GET'])
def get_file_all_nodes():
    """获取指定文件数据库中所有的节点列表"""
    try:
        db_file_path = request.args.get('path')
        if not db_file_path:
            return jsonify({
                "success": False,
                "message": "Missing 'path' parameter"
            }), 400
            
        conn = get_duckdb_connection(db_file_path)
        if conn is None:
            return jsonify({
                "success": False,
                "message": f"DuckDB database not found at {db_file_path}"
            }), 404
        
        table_name = get_table_name()
        
        query = f"""
            SELECT DISTINCT node_name, 
                   COUNT(*) as record_count,
                   MAX(time) as last_activity
            FROM {table_name} 
            GROUP BY node_name 
            ORDER BY last_activity DESC
        """
        
        results = conn.execute(query).fetchall()
        conn.close()
        
        nodes = []
        for node_name, record_count, last_activity in results:
            nodes.append({
                "node_name": node_name,
                "record_count": record_count,
                "last_activity": last_activity
            })
        
        return jsonify({
            "success": True,
            "nodes": nodes,
            "count": len(nodes)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to get nodes: {str(e)}"
        }), 500

@duckdb_bp.route('/file/node/<node_id>/variables', methods=['GET'])
def get_file_node_all_variables(node_id):
    """获取指定文件数据库中指定节点的所有当前变量"""
    try:
        db_file_path = request.args.get('path')
        if not db_file_path:
            return jsonify({
                "success": False,
                "message": "Missing 'path' parameter"
            }), 400
            
        conn = get_duckdb_connection(db_file_path)
        if conn is None:
            return jsonify({
                "success": False,
                "message": f"DuckDB database not found at {db_file_path}"
            }), 404
        
        table_name = get_table_name()
        
        # 获取所有输入变量的最新值
        input_query = f"""
            SELECT input_name, input_value, time
            FROM {table_name} 
            WHERE node_name = ? AND input_name IS NOT NULL AND input_value IS NOT NULL
            AND (node_name, input_name, time) IN (
                SELECT node_name, input_name, MAX(time) 
                FROM {table_name} 
                WHERE node_name = ? AND input_name IS NOT NULL 
                GROUP BY node_name, input_name
            )
        """
        
        # 获取所有输出变量的最新值
        output_query = f"""
            SELECT output_name, output_value, time
            FROM {table_name} 
            WHERE node_name = ? AND output_name IS NOT NULL AND output_value IS NOT NULL
            AND (node_name, output_name, time) IN (
                SELECT node_name, output_name, MAX(time) 
                FROM {table_name} 
                WHERE node_name = ? AND output_name IS NOT NULL 
                GROUP BY node_name, output_name
            )
        """
        
        input_results = conn.execute(input_query, [node_id, node_id]).fetchall()
        output_results = conn.execute(output_query, [node_id, node_id]).fetchall()
        
        variables = {}
        
        # 处理输入变量
        for var_name, var_value, time in input_results:
            try:
                parsed_value = json.loads(var_value)
                display_value = json.dumps(parsed_value, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                parsed_value = var_value
                display_value = str(var_value)
            
            variables[var_name] = {
                "value": parsed_value,
                "display_value": display_value,
                "time": time,
                "type": "input"
            }
        
        # 处理输出变量
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
                        "value": parsed_value,
                        "display_value": display_value,
                        "time": time,
                        "type": "output"
                    }
            else:
                variables[var_name] = {
                    "value": parsed_value,
                    "display_value": display_value,
                    "time": time,
                    "type": "output"
                }
        
        conn.close()
        
        return jsonify({
            "success": True,
            "node_id": node_id,
            "variables": variables,
            "count": len(variables)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to get node variables: {str(e)}"
        }), 500

@duckdb_bp.route('/file/node/<node_id>/history', methods=['GET'])
def get_file_node_history(node_id):
    """获取指定文件数据库中指定节点的历史记录"""
    try:
        db_file_path = request.args.get('path')
        if not db_file_path:
            return jsonify({
                "success": False,
                "message": "Missing 'path' parameter"
            }), 400
            
        limit = request.args.get('limit', 20, type=int)
            
        conn = get_duckdb_connection(db_file_path)
        if conn is None:
            return jsonify({
                "success": False,
                "message": f"DuckDB database not found at {db_file_path}"
            }), 404
        
        table_name = get_table_name()
        
        # 获取该节点的历史记录
        history_query = f"""
            SELECT time, input_name, input_value, output_name, output_value
            FROM {table_name}
            WHERE node_name = ?
            ORDER BY time DESC
            LIMIT ?
        """
        history_results = conn.execute(history_query, [node_id, limit]).fetchall()
        
        history = []
        for time, input_name, input_value, output_name, output_value in history_results:
            # 解析JSON值
            def parse_json_value(value):
                if value is None or value == 'None':
                    return None
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            
            history.append({
                'time': time,
                'input_name': input_name,
                'input_value': parse_json_value(input_value),
                'output_name': output_name,
                'output_value': parse_json_value(output_value)
            })
        
        conn.close()
        
        return jsonify({
            "success": True,
            "node_id": node_id,
            "history": history,
            "count": len(history)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to get node history: {str(e)}"
        }), 500

@duckdb_bp.route('/stats', methods=['GET'])
def get_database_stats():
    """获取数据库统计信息"""
    try:
        conn = get_duckdb_connection()
        if conn is None:
            return jsonify({
                "success": False,
                "message": "DuckDB database not found"
            }), 404
        
        table_name = get_table_name()
        
        # 获取总记录数
        total_query = f"SELECT COUNT(*) FROM {table_name}"
        total_records = conn.execute(total_query).fetchone()[0]
        
        # 获取节点数量
        nodes_query = f"SELECT COUNT(DISTINCT node_name) FROM {table_name}"
        total_nodes = conn.execute(nodes_query).fetchone()[0]
        
        # 获取时间范围
        time_range_query = f"SELECT MIN(time), MAX(time) FROM {table_name}"
        time_range = conn.execute(time_range_query).fetchone()
        
        conn.close()
        
        return jsonify({
            "success": True,
            "stats": {
                "total_records": total_records,
                "total_nodes": total_nodes,
                "earliest_record": time_range[0],
                "latest_record": time_range[1],
                "database_path": os.getenv('LOG_DB_PATH', 'logs.duckdb'),
                "table_name": table_name
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to get database stats: {str(e)}"
        }), 500