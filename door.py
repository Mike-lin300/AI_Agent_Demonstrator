import json, re
from openai import OpenAI
import os
import math
from datetime import datetime
import random
import requests

# ================= 配置区域 =================
# 如果你本地开了梯子，请设置为 True，并确认下面的代理地址是否正确
USE_PROXY = False  
PROXY_URL = "http://127.0.0.1:7890"  # 常见的梯子端口：7890, 10809, 7897

# 调试模式：可以通过环境变量 DEBUG_MODE 控制（true/false），默认为 true
DEBUG_MODE = os.environ.get('DEBUG_MODE', 'true').lower() == 'true'

# 如果开启了代理但连接阿里云报错，可以尝试取消下面这行的注释来绕过代理
# os.environ['NO_PROXY'] = 'dashscope.aliyuncs.com'
# ===========================================

def get_proxies():
    """获取代理配置"""
    if USE_PROXY:
        return {"http": PROXY_URL, "https": PROXY_URL}
    return None

# 创建一个安全的沙箱目录
WORKSPACE = "./agent_workspace"
os.makedirs(WORKSPACE, exist_ok=True)


class SimpleAgent:
    def __init__(self, api_key, base_url=None, model="deepseek-chat"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.messages = []                  # 对话历史记录
        self.tools = {}                     # 可用的工具列表
        self.register_builtin_tools()       # 注册内置工具

    def register_tool(self, name, func, description):
        self.tools[name] = {"func": func, "desc": description}

    def register_builtin_tools(self):
        # 计算器
        def calculator(expr: str):
            """计算数学表达式，支持单个表达式或多个表达式（用分号分隔）"""
            try:
                safe_dict = {
                    # 数学常量
                    'pi': math.pi,
                    'e': math.e,
                    'tau': math.tau,
                    
                    # 基本数学函数
                    'sqrt': math.sqrt,
                    'cbrt': lambda x: math.pow(x, 1/3),
                    
                    # 三角函数
                    'sin': math.sin,
                    'cos': math.cos,
                    'tan': math.tan,
                    'asin': math.asin,
                    'acos': math.acos,
                    'atan': math.atan,
                    'atan2': math.atan2,
                    
                    # 双曲函数
                    'sinh': math.sinh,
                    'cosh': math.cosh,
                    'tanh': math.tanh,
                    
                    # 指数和对数
                    'exp': math.exp,
                    'log': math.log,
                    'log10': math.log10,
                    'log2': math.log2,
                    'ln': math.log,
                    
                    # 幂函数
                    'pow': math.pow,
                    
                    # 取整函数
                    'ceil': math.ceil,
                    'floor': math.floor,
                    'fabs': math.fabs,
                    'trunc': math.trunc,
                    
                    # 其他实用函数
                    'factorial': math.factorial,
                    'gcd': math.gcd,
                    'lcm': lambda a, b: abs(a * b) // math.gcd(a, b),
                    
                    # 角度转换
                    'degrees': math.degrees,
                    'radians': math.radians,
                    
                    # 最大值最小值
                    'max': max,
                    'min': min,
                    'abs': abs,
                    'round': round,
                    'sum': sum,
                    'len': len,
                }
                
                # 检查是否包含多个表达式（用分号分隔）
                if ';' in expr:
                    expressions = [e.strip() for e in expr.split(';') if e.strip()]
                    results = []
                    for i, single_expr in enumerate(expressions):
                        result = eval(single_expr, {"__builtins__": {}}, safe_dict)
                        results.append(f"表达式{i+1}: {single_expr} = {result}")
                    return "\n".join(results)
                else:
                    return eval(expr, {"__builtins__": {}}, safe_dict)
            except Exception as e:
                return f"计算错误: {str(e)}"
        self.register_tool("calculator", calculator, "计算数学表达式，支持单个表达式或多个表达式（用分号分隔）。示例：'(85+90)/2; (78+82)/2; (92+88)/2' 或 'sum([85,78,92,80,87])/5'")

        def read_file(path: str) -> str:
            """读取沙箱内的文件"""
            safe_path = os.path.join(WORKSPACE, os.path.basename(path))
            try:
                with open(safe_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except FileNotFoundError:
                return f"文件 {safe_path} 不存在"
            except Exception as e:
                return f"读取错误：{e}"
        self.register_tool("read_file", read_file, "读取文件，参数path为文件名")

        def write_file(path: str, content: str) -> str:
            """写入沙箱内的文件"""
            safe_path = os.path.join(WORKSPACE, os.path.basename(path))
            try:
                with open(safe_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"成功写入 {safe_path}"
            except Exception as e:
                return f"写入错误：{e}"
        self.register_tool("write_file", write_file, "写入文件（覆盖模式），参数path和content。如果文件已存在，会完全覆盖原有内容")

        def append_file(path: str, content: str) -> str:
            """追加内容到文件末尾"""
            safe_path = os.path.join(WORKSPACE, os.path.basename(path))
            try:
                with open(safe_path, 'a', encoding='utf-8') as f:  # 'a' 表示追加模式
                    f.write(content)
                return f"成功追加内容到 {safe_path}"
            except Exception as e:
                return f"追加错误：{e}"
        self.register_tool("append_file", append_file, "追加内容到文件末尾（不覆盖），参数path和content。如果文件不存在则创建新文件")

        def get_current_time(format_type: str = "datetime") -> str:
            """获取当前系统时间或日期"""
            now = datetime.now()
            try:
                if format_type == "date":
                    return now.strftime("%Y年%m月%d日")
                elif format_type == "time":
                    return now.strftime("%H:%M:%S")
                elif format_type == "datetime":
                    return now.strftime("%Y年%m月%d日 %H:%M:%S")
                elif format_type == "timestamp":
                    return str(int(now.timestamp()))
                else:
                    return now.strftime("%Y年%m月%d日 %H:%M:%S")
            except Exception as e:
                return f"获取时间错误: {str(e)}"
        self.register_tool("get_current_time", get_current_time, "获取当前时间/日期，参数format_type可选值：'date'(仅日期), 'time'(仅时间), 'datetime'(完整日期时间), 'timestamp'(时间戳)，默认为'datetime'")

        def get_weather(city: str = "杭州") -> str:
            """查询实时天气信息（使用 wttr.in API）"""
            try:
                # wttr.in API - 免费、无需密钥、支持中文
                url = f"https://wttr.in/{city}?format=%C+%t+%w+%h&lang=zh"
                headers = {"User-Agent": "curl/7.68.0"}  # wttr.in 建议的 User-Agent
                
                resp = requests.get(url, headers=headers, proxies=get_proxies(), timeout=10)
                
                if resp.status_code == 200:
                    text = resp.text.strip()
                    
                    # 【调试】打印原始API返回数据
                    import os
                    if os.environ.get('DEBUG_MODE', 'true').lower() == 'true':
                        print(f"[天气API原始返回]: '{text}'")
                        print(f"[天气API分割结果]: {text.split()}")
                    
                    # 解析返回内容：格式为 "天气状况 温度 风力 湿度"
                    # 例如："晴 +25°C 北风2级 45%" 或 "Light rain +20°C SW 15 km/h 60%"
                    # 或者："Smoky haze +30C 12km/h" (无湿度)
                    parts = text.split()
                    
                    if len(parts) >= 3:
                        # 智能解析：从后往前识别各个字段
                        humidity = "未知"
                        wind = "未知"
                        temperature = "未知"
                        condition_parts = []
                        
                        # 策略1：查找湿度（包含%符号）
                        humidity_idx = -1
                        for i in range(len(parts) - 1, -1, -1):
                            if '%' in parts[i]:
                                humidity = parts[i]
                                humidity_idx = i
                                break
                        
                        # 策略2：查找温度（包含°C、°F或单独C/F）
                        temp_idx = -1
                        for i in range(len(parts) - 1, -1, -1):
                            if '°' in parts[i] or (parts[i].endswith('C') and len(parts[i]) > 1) or parts[i].endswith('F'):
                                # 确保不是风力描述（如"SW"、"NE"等）
                                if not parts[i].isalpha() or len(parts[i]) > 2:
                                    temperature = parts[i]
                                    temp_idx = i
                                    break
                        
                        # 策略3：根据位置推断
                        if temp_idx > 0:
                            # 温度后面的部分是风力和湿度
                            remaining = parts[temp_idx + 1:]
                            if humidity_idx > temp_idx:
                                # 湿度在温度后面
                                wind_parts = parts[temp_idx + 1:humidity_idx]
                                wind = ' '.join(wind_parts) if wind_parts else "未知"
                            else:
                                # 没有明确湿度，剩余的都是风力
                                wind = ' '.join(remaining) if remaining else "未知"
                            
                            # 温度前面的是天气描述
                            condition_parts = parts[:temp_idx]
                        else:
                            # 没找到温度，使用简单策略：最后3个是温度、风力、湿度
                            if len(parts) >= 3:
                                temperature = parts[-3]
                                wind = parts[-2]
                                humidity = parts[-1] if '%' in parts[-1] else "未知"
                                condition_parts = parts[:-3]
                            else:
                                condition_parts = parts
                        
                        condition = ' '.join(condition_parts) if condition_parts else "未知"
                        
                        return f"{city}实时天气：{condition}，气温：{temperature}，风力：{wind}，湿度：{humidity}"
                    else:
                        # 数据不完整，直接返回原始文本
                        return f"{city}天气：{text}"
                else:
                    return f"查询失败，HTTP状态码：{resp.status_code}"
            
            except requests.exceptions.Timeout:
                return f"查询超时，请检查网络连接"
            except requests.exceptions.ConnectionError:
                return f"连接失败，请检查网络或代理设置"
            except Exception as e:
                return f"查询错误: {str(e)}"
        self.register_tool("get_weather", get_weather, "查询实时天气，参数city为城市名称（支持中文）。使用 wttr.in API，返回天气状况、温度、风力和湿度。示例：'北京'、'上海'、'Hangzhou'")

        def generate_random_number(min_val: float = 0, max_val: float = 1, is_integer: bool = False, count: int = 1) -> str:
            """生成一个或多个随机数"""
            try:
                # 限制最大生成数量，防止滥用
                if count > 100:
                    return f"错误：一次最多生成100个随机数，当前请求：{count}个"
                
                if count <= 0:
                    return f"错误：生成数量必须大于0，当前值：{count}"
                
                results = []
                
                if is_integer:
                    # 生成整数
                    for i in range(count):
                        result = random.randint(int(min_val), int(max_val))
                        results.append(result)
                    
                    if count == 1:
                        return f"生成的随机整数：{results[0]} (范围：{int(min_val)}-{int(max_val)})"
                    else:
                        # 多个结果时，提供统计信息
                        avg = sum(results) / len(results)
                        return f"生成的 {count} 个随机整数：\n" + \
                               f"  结果列表：{results}\n" + \
                               f"  范围：{int(min_val)}-{int(max_val)}\n" + \
                               f"  平均值：{avg:.2f}\n" + \
                               f"  最小值：{min(results)}\n" + \
                               f"  最大值：{max(results)}"
                else:
                    # 生成浮点数
                    for i in range(count):
                        result = random.uniform(min_val, max_val)
                        results.append(round(result, 4))
                    
                    if count == 1:
                        return f"生成的随机数：{results[0]:.4f} (范围：{min_val}-{max_val})"
                    else:
                        # 多个结果时，提供统计信息
                        avg = sum(results) / len(results)
                        return f"生成的 {count} 个随机数：\n" + \
                               f"  结果列表：{results}\n" + \
                               f"  范围：{min_val}-{max_val}\n" + \
                               f"  平均值：{avg:.4f}\n" + \
                               f"  最小值：{min(results):.4f}\n" + \
                               f"  最大值：{max(results):.4f}"
            except Exception as e:
                return f"生成随机数错误: {str(e)}"
        self.register_tool("generate_random_number", generate_random_number, "生成随机数，参数min_val(最小值，默认0), max_val(最大值，默认1), is_integer(是否整数，默认False), count(生成数量，默认1，最多100)。示例：{'min_val': 1, 'max_val': 100, 'is_integer': true, 'count': 5}")

        def list_files() -> str:
            """列出沙箱目录中的所有文件"""
            try:
                files = os.listdir(WORKSPACE)
                if not files:
                    return "目录为空，没有文件"
                file_list = []
                for f in sorted(files):
                    file_path = os.path.join(WORKSPACE, f)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        file_list.append(f"{f} ({size} bytes)")
                return "文件列表：\n" + "\n".join(file_list)
            except Exception as e:
                return f"列出文件错误: {str(e)}"
        self.register_tool("list_files", list_files, "列出agent_workspace目录中的所有文件及其大小，无需参数")

        def read_json(path: str) -> str:
            """读取JSON文件并返回格式化内容"""
            safe_path = os.path.join(WORKSPACE, os.path.basename(path))
            try:
                with open(safe_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 返回格式化的JSON字符串，便于AI阅读
                return json.dumps(data, ensure_ascii=False, indent=2)
            except FileNotFoundError:
                return f"文件 {safe_path} 不存在"
            except json.JSONDecodeError as e:
                return f"JSON格式错误: {str(e)}"
            except Exception as e:
                return f"读取错误：{e}"
        self.register_tool("read_json", read_json, "读取JSON文件并返回格式化内容，参数path为文件名（.json后缀可选）")

        def write_json(path: str, data) -> str:
            """写入JSON文件（接受Python对象，自动序列化）"""
            safe_path = os.path.join(WORKSPACE, os.path.basename(path))
            try:
                # 直接接受Python对象（dict/list），自动序列化为JSON
                with open(safe_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return f"成功写入JSON文件 {safe_path}"
            except TypeError as e:
                return f"数据类型错误，请提供有效的Python对象(dict或list): {str(e)}"
            except Exception as e:
                return f"写入错误：{e}"
        self.register_tool("write_json", write_json, "写入JSON文件，参数path为文件名，data为Python对象（字典或列表，会自动序列化为JSON并格式化）")

        def analyze_json_data(path: str, operations: str) -> str:
            """对JSON数据进行批量分析计算"""
            safe_path = os.path.join(WORKSPACE, os.path.basename(path))
            try:
                # 读取JSON文件
                with open(safe_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                results = []
                
                # 解析操作指令（支持多种操作，用分号分隔）
                ops = [op.strip() for op in operations.split(';') if op.strip()]
                
                for op in ops:
                    if op.startswith('avg:'):
                        # 计算平均值，如 avg:students.math
                        field_path = op[4:].strip()
                        values = extract_values(data, field_path)
                        if values:
                            avg_val = sum(values) / len(values)
                            results.append(f"{field_path}的平均值: {avg_val:.2f}")
                        else:
                            results.append(f"未找到字段: {field_path}")
                    
                    elif op.startswith('sum:'):
                        # 计算总和
                        field_path = op[4:].strip()
                        values = extract_values(data, field_path)
                        if values:
                            total = sum(values)
                            results.append(f"{field_path}的总和: {total}")
                        else:
                            results.append(f"未找到字段: {field_path}")
                    
                    elif op.startswith('max:'):
                        # 最大值
                        field_path = op[4:].strip()
                        values = extract_values(data, field_path)
                        if values:
                            max_val = max(values)
                            results.append(f"{field_path}的最大值: {max_val}")
                        else:
                            results.append(f"未找到字段: {field_path}")
                    
                    elif op.startswith('min:'):
                        # 最小值
                        field_path = op[4:].strip()
                        values = extract_values(data, field_path)
                        if values:
                            min_val = min(values)
                            results.append(f"{field_path}的最小值: {min_val}")
                        else:
                            results.append(f"未找到字段: {field_path}")
                    
                    elif op.startswith('count:'):
                        # 计数
                        field_path = op[6:].strip()
                        values = extract_values(data, field_path)
                        results.append(f"{field_path}的数量: {len(values)}")
                    
                    else:
                        results.append(f"未知操作: {op}")
                
                return "\n".join(results)
            
            except FileNotFoundError:
                return f"文件 {safe_path} 不存在"
            except Exception as e:
                return f"分析错误: {str(e)}"
        
        def extract_values(data, field_path):
            """从JSON数据中提取指定字段的值"""
            # 简单实现：支持 students.math 或 sales.amount 格式
            parts = field_path.split('.')
            values = []
            
            if len(parts) == 2:
                array_name, field_name = parts
                if isinstance(data, dict) and array_name in data:
                    items = data[array_name]
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and field_name in item:
                                val = item[field_name]
                                if isinstance(val, (int, float)):
                                    values.append(val)
            
            return values
        
        self.register_tool("analyze_json_data", analyze_json_data, "对JSON数据进行批量统计分析，参数path为文件名，operations为操作指令（用分号分隔）。支持的操作：avg:字段(平均值), sum:字段(总和), max:字段(最大值), min:字段(最小值), count:字段(计数)。示例：'avg:students.math; avg:students.english; sum:students.math'")

    def system_prompt(self):
        # ReAct 风格输出格式约束
        return """你是一个能调用工具的AI助手。当你需要执行动作时，必须严格输出如下格式：

Thought: 你的思考过程
Action: {"tool": "工具名", "args": {"参数名": "参数值"}}

如果任务已经完成，请输出：
Thought: 任务完成
Final Answer: 给用户的最终回复

可用的工具：
- calculator: 计算数学表达式，args中的"expr"为表达式字符串
  支持的函数：sqrt, sin, cos, tan, asin, acos, atan, log, log10, log2, exp, pow, factorial, ceil, floor, abs, max, min, round等
  支持的常量：pi (π), e (自然常数)
  示例：'sin(pi/2)', 'sqrt(16) + 5', 'log(100, 10)', 'factorial(5)', '2**3 + sqrt(9)'
  注意：使用Python语法，不要使用数学符号（如用'*'表示乘法，用'**'表示幂）
  重要：所有数学计算都必须使用calculator工具，不要手动计算！
  技巧：可以使用分号分隔多个表达式一次性计算，如'(85+90)/2; (78+82)/2; (92+88)/2'
- read_file: 读取文本文件，args中的"path"为文件路径（仅限文件名，不能带目录）
- write_file: 写入文本文件（覆盖模式），args中的"path"为文件名，"content"为要写入的文本
- append_file: 追加内容到文件末尾（不覆盖），args中的"path"为文件名，"content"为要追加的文本
- read_json: 读取JSON文件并返回格式化内容，args中的"path"为文件名
- write_json: 写入JSON文件，args中的"path"为文件名，"data"为Python对象（字典或列表，无需手动转义）
- analyze_json_data: 批量分析JSON数据，args中的"path"为文件名，"operations"为操作指令（avg/sum/max/min/count）
- list_files: 列出目录中的所有文件，无需参数
- get_current_time: 获取当前时间/日期，args中的"format_type"可选：'date'(日期), 'time'(时间), 'datetime'(完整), 'timestamp'(时间戳)，默认'datetime'
- get_weather: 查询实时天气，args中的"city"为城市名称（支持中文），如"北京"、"上海"、"Hangzhou"
- generate_random_number: 生成随机数，args中的"min_val"(最小值), "max_val"(最大值), "is_integer"(是否整数), "count"(生成数量，默认1)

注意：write_file 和 read_file 只能操作 agent_workspace 目录下的文件。

重要原则：
1. 与实时时间验证相关的任务，必须使用get_current_time查看用户现在的事实时间
2. 所有数学计算（包括加减乘除、平均值、总和等）必须使用calculator工具
3. 创建JSON文件时，write_json的data参数直接传Python对象（字典或列表），不需要转义
4. 每次只输出一个Action，收到观察结果后继续思考
5. 复杂任务要分解为多个步骤，逐步执行
"""

    def run(self, user_input, debug_mode=None):
        """
        运行 AI Agent
        :param user_input: 用户输入
        :param debug_mode: 是否开启实时调试模式（None则使用全局配置）
        """
        # 如果未指定，使用全局配置
        if debug_mode is None:
            debug_mode = DEBUG_MODE
        
        self.messages.append({"role": "user", "content": user_input})
        max_steps = 10
        
        if debug_mode:
            print("\n" + "="*60)
            print("🚀 开始执行任务")
            print("="*60)
            print(f"\n用户指令: {user_input}\n")
        
        for step in range(1, max_steps + 1):
            if debug_mode:
                print(f"\n{'─'*60}")
                print(f"📍 第 {step}/{max_steps} 步 - 调用大模型...")
                print(f"{'─'*60}")
            
            # 调用大模型（开启阿里云原生联网搜索）
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": self.system_prompt()}] + self.messages,
                    temperature=0,
                    extra_body={
                        "enable_search": False  # 【关键】通过 extra_body 开启阿里云百炼 Web Search
                    }
                )
            except Exception as e:
                error_msg = f"API调用失败: {str(e)}"
                if debug_mode:
                    print(f"❌ {error_msg}")
                return error_msg
            
            output = resp.choices[0].message.content
            self.messages.append({"role": "assistant", "content": output})
            
            if debug_mode:
                print(f"\n💭 AI思考过程:")
                # 提取 Thought 部分
                thought_match = re.search(r'Thought:\s*(.*?)(?=Action:|Final Answer:|$)', output, re.DOTALL)
                if thought_match:
                    print(f"   {thought_match.group(1).strip()}")
            
            # 解析是否有 Action
            action_match = re.search(r'Action:\s*({.*})', output, re.DOTALL)
            if not action_match:
                # 没有 Action，说明是最终回复
                if debug_mode:
                    print(f"\n✅ 任务完成！")
                final_match = re.search(r'Final Answer:\s*(.*)', output, re.DOTALL)
                result = final_match.group(1) if final_match else output
                
                if debug_mode:
                    print(f"\n📝 最终结果:")
                    print(f"   {result[:200]}{'...' if len(result) > 200 else ''}")
                
                return result
            
            # 执行工具
            try:
                action_json = json.loads(action_match.group(1))
                tool_name = action_json["tool"]
                args = action_json.get("args", {})
                
                if debug_mode:
                    print(f"\n🔧 执行工具: {tool_name}")
                    # 只显示关键参数
                    args_preview = json.dumps(args, ensure_ascii=False)[:100]
                    print(f"   参数: {args_preview}")
                
                if tool_name not in self.tools:
                    observation = f"错误：未知工具 {tool_name}"
                    if debug_mode:
                        print(f"   ❌ {observation}")
                else:
                    observation = str(self.tools[tool_name]["func"](**args))
                    if debug_mode:
                        # 截断过长的输出
                        obs_preview = observation[:300] + ('...' if len(observation) > 300 else '')
                        print(f"   ✅ 观察结果: {obs_preview}")
                        
            except Exception as e:
                observation = f"解析或执行错误: {e}"
                if debug_mode:
                    print(f"   ❌ {observation}")

            # 将观察结果喂回给模型
            self.messages.append({"role": "user", "content": f"Observation: {observation}"})
        
        if debug_mode:
            print(f"\n{'='*60}")
            print(f"⚠️ 达到最大步骤限制 ({max_steps}步)，任务未完成")
            print(f"{'='*60}")
        
        return "达到最大步骤限制，任务未完成。"


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='AI Agent Demo - 支持实时调试',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python door.py                          # 使用默认配置（开启调试）
  python door.py --debug                  # 强制开启调试
  python door.py --no-debug               # 关闭调试
  python door.py --message "查询天气"      # 直接传入消息
  DEBUG_MODE=false python door.py         # 通过环境变量关闭调试
        """
    )
    parser.add_argument('--debug', action='store_true', 
                       help='强制开启实时调试模式')
    parser.add_argument('--no-debug', action='store_true', 
                       help='关闭实时调试模式')
    parser.add_argument('--message', type=str, 
                       help='直接传入消息（跳过交互式输入）')
    
    args = parser.parse_args()
    
    # 确定调试模式优先级：命令行参数 > 环境变量 > 默认值
    if args.no_debug:
        debug_mode = False
    elif args.debug:
        debug_mode = True
    else:
        debug_mode = DEBUG_MODE  # 使用环境变量或默认值
    
    # 从环境变量获取API密钥
    api_key = os.environ.get('DASHSCOPE_API_KEY')
    if not api_key:
        raise EnvironmentError("请设置环境变量 DASHSCOPE_API_KEY")
    
    agent = SimpleAgent(api_key=api_key,
                        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                        model="qwen3.5-plus")
    
    # 获取用户输入
    if args.message:
        user_message = args.message
        if not debug_mode:
            print(f"\n📝 收到指令: {user_message}\n")
    else:
        user_message = input("用户原始指令：")

    result = agent.run(user_message, debug_mode=debug_mode)

    # 如果关闭了调试模式，显示简洁的最终结果
    if not debug_mode:
        print("\n" + "=" * 50)
        print("✅ 最终结果:", result)
        print("=" * 50)
    else:
        # 调试模式下，显示完整对话历史
        print("\n" + "=" * 60)
        print("📊 完整对话历史")
        print("=" * 60)
        for i, msg in enumerate(agent.messages):
            print(f"\n--- 第 {i + 1} 条消息 ---")
            print(f"角色: {msg['role']}")
            print(f"内容: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}")

