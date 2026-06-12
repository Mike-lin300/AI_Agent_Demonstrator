from flask import Flask, render_template, request, jsonify, Response
import json
import re
import os
from door import SimpleAgent
import time

app = Flask(__name__)

# 创建全局Agent实例（避免重复初始化）
agent = None

def get_agent():
    """获取或创建Agent实例"""
    global agent
    if agent is None:
        api_key = os.environ.get('DASHSCOPE_API_KEY')
        agent = SimpleAgent(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen3.5-plus"
        )
    return agent


@app.route('/')
def index():
    """主页 - 渲染Web界面"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """处理聊天请求（支持流式输出）"""
    try:
        data = request.json
        user_message = data.get('message', '')
        debug_mode = data.get('debug_mode', True)
        stream = data.get('stream', False)  # 是否启用流式输出
        
        if not user_message:
            return jsonify({'error': '消息不能为空'}), 400
        
        # 创建新的Agent实例（每个请求独立，避免状态污染）
        api_key = os.environ.get('DASHSCOPE_API_KEY', 'sk-3c3fbeb1b58e4bf7b0ed56c430ef5e5d')
        current_agent = SimpleAgent(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen3.5-plus"
        )
        
        # 如果启用流式输出
        if stream and debug_mode:
            def generate():
                """生成器函数，逐步返回推理过程"""
                max_steps = 10
                step_count = 0
                
                # 发送初始消息
                yield f"data: {json.dumps({'type': 'start', 'message': '开始执行任务...'}, ensure_ascii=False)}\n\n"
                
                current_agent.messages.append({"role": "user", "content": user_message})
                
                for step in range(1, max_steps + 1):
                    step_count = step
                    
                    # 调用大模型
                    try:
                        resp = current_agent.client.chat.completions.create(
                            model=current_agent.model,
                            messages=[{"role": "system", "content": current_agent.system_prompt()}] + current_agent.messages,
                            temperature=0,
                            extra_body={
                                "enable_search": False
                            }
                        )
                    except Exception as e:
                        error_msg = f"API调用失败: {str(e)}"
                        yield f"data: {json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)}\n\n"
                        break
                    
                    output = resp.choices[0].message.content
                    current_agent.messages.append({"role": "assistant", "content": output})
                    
                    # 解析 Thought
                    thought_match = re.search(r'Thought:\s*(.*?)(?=Action:|Final Answer:|$)', output, re.DOTALL)
                    if thought_match:
                        thought = thought_match.group(1).strip()
                        yield f"data: {json.dumps({'type': 'thought', 'step': step, 'content': thought}, ensure_ascii=False)}\n\n"
                        time.sleep(0.3)  # 模拟思考延迟，让用户看清
                    
                    # 解析 Action
                    action_match = re.search(r'Action:\s*({.*})', output, re.DOTALL)
                    if not action_match:
                        # 没有 Action，说明是最终回复
                        final_match = re.search(r'Final Answer:\s*(.*)', output, re.DOTALL)
                        result = final_match.group(1) if final_match else output
                        
                        yield f"data: {json.dumps({'type': 'final', 'result': result, 'history': current_agent.messages}, ensure_ascii=False)}\n\n"
                        break
                    
                    # 执行工具
                    try:
                        action_json = json.loads(action_match.group(1))
                        tool_name = action_json["tool"]
                        args = action_json.get("args", {})
                        
                        # 发送工具调用信息
                        yield f"data: {json.dumps({'type': 'action', 'step': step, 'tool': tool_name, 'args': args}, ensure_ascii=False)}\n\n"
                        time.sleep(0.2)
                        
                        if tool_name not in current_agent.tools:
                            observation = f"错误：未知工具 {tool_name}"
                        else:
                            observation = str(current_agent.tools[tool_name]["func"](**args))
                        
                        # 发送观察结果
                        yield f"data: {json.dumps({'type': 'observation', 'step': step, 'content': observation[:500]}, ensure_ascii=False)}\n\n"
                        time.sleep(0.3)
                        
                    except Exception as e:
                        observation = f"解析或执行错误: {e}"
                        yield f"data: {json.dumps({'type': 'observation', 'step': step, 'content': observation}, ensure_ascii=False)}\n\n"

                    # 将观察结果喂回给模型
                    current_agent.messages.append({"role": "user", "content": f"Observation: {observation}"})
                
                else:
                    # 达到最大步骤限制
                    yield f"data: {json.dumps({'type': 'final', 'result': '达到最大步骤限制，任务未完成。', 'history': current_agent.messages}, ensure_ascii=False)}\n\n"
            
            return Response(generate(), mimetype='text/event-stream')
        
        else:
            # 非流式模式（原有逻辑）
            result = current_agent.run(user_message, debug_mode=debug_mode)
            
            return jsonify({
                'success': True,
                'result': result,
                'history': current_agent.messages
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/clear_workspace', methods=['POST'])
def clear_workspace():
    """清空工作区文件"""
    try:
        import os
        from door import WORKSPACE
        
        files = os.listdir(WORKSPACE)
        deleted_count = 0
        
        for f in files:
            file_path = os.path.join(WORKSPACE, f)
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted_count += 1
        
        return jsonify({
            'success': True,
            'message': f'已删除 {deleted_count} 个文件'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/list_files', methods=['GET'])
def list_workspace_files():
    """列出工作区文件"""
    try:
        import os
        from door import WORKSPACE
        
        files = []
        if os.path.exists(WORKSPACE):
            for f in sorted(os.listdir(WORKSPACE)):
                file_path = os.path.join(WORKSPACE, f)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    files.append({
                        'name': f,
                        'size': size,
                        'size_human': format_file_size(size)
                    })
        
        return jsonify({
            'success': True,
            'files': files
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
