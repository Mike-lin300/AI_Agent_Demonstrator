# AI Agent 调试模式使用说明

## 📋 功能概述

当前 AI Agent 支持灵活的调试模式控制，可以通过以下三种方式开关实时调试信息：

1. **环境变量** - 适合长期配置
2. **命令行参数** - 适合临时切换
3. **代码参数** - 适合编程调用

---

## 🎯 使用方法

### 方法1：环境变量（推荐用于开发/生产环境切换）

#### Windows PowerShell
```powershell
# 开启调试（默认）
$env:DEBUG_MODE="true"
python door.py

# 关闭调试
$env:DEBUG_MODE="false"
python door.py
```

#### Windows CMD
```cmd
# 开启调试
set DEBUG_MODE=true
python door.py

# 关闭调试
set DEBUG_MODE=false
python door.py
```

#### 永久设置（系统环境变量）
1. 右键"此电脑" → 属性 → 高级系统设置
2. 点击"环境变量"
3. 在"用户变量"或"系统变量"中新建：
   - 变量名：`DEBUG_MODE`
   - 变量值：`true` 或 `false`
4. 重启终端生效

---

### 方法2：命令行参数（推荐用于快速测试）

```bash
# 使用默认配置（根据环境变量或默认值）
python door.py

# 强制开启调试
python door.py --debug

# 强制关闭调试
python door.py --no-debug

# 直接传入消息（跳过交互式输入）
python door.py --message "查询北京天气"

# 组合使用
python door.py --message "计算1+1" --no-debug
```

#### 查看帮助
```bash
python door.py --help
```

---

### 方法3：代码中控制（推荐用于集成到其他项目）

```python
from door import SimpleAgent

agent = SimpleAgent(
    api_key="your-api-key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    model="qwen3.5-plus"
)

# 开启调试
result = agent.run("查询天气", debug_mode=True)

# 关闭调试
result = agent.run("查询天气", debug_mode=False)

# 使用全局配置
result = agent.run("查询天气")  # 自动使用 DEBUG_MODE 环境变量
```

---

## 📊 输出对比

### 开启调试模式（debug_mode=True）

```
============================================================
🚀 开始执行任务
============================================================

用户指令: 查询北京天气

────────────────────────────────────────────────────────────
📍 第 1/10 步 - 调用大模型...
────────────────────────────────────────────────────────────

💭 AI思考过程:
   我需要查询北京的天气，应该使用get_weather工具

🔧 执行工具: get_weather
   参数: {"city": "北京"}
   ✅ 观察结果: 北京实时天气：晴，气温：+25°C...

────────────────────────────────────────────────────────────
📍 第 2/10 步 - 调用大模型...
────────────────────────────────────────────────────────────

💭 AI思考过程:
   已经获取到天气信息，任务完成

✅ 任务完成！

📝 最终结果:
   北京当前天气晴朗，气温25°C...

============================================================
📊 完整对话历史
============================================================
--- 第 1 条消息 ---
角色: user
内容: 查询北京天气
...
```

### 关闭调试模式（debug_mode=False）

```
📝 收到指令: 查询北京天气

==================================================
✅ 最终结果: 北京当前天气晴朗，气温25°C，北风2级
==================================================
```

---

## 🔧 优先级说明

调试模式的确定遵循以下优先级（从高到低）：

1. **命令行参数** `--debug` / `--no-debug`
2. **环境变量** `DEBUG_MODE`
3. **代码参数** `debug_mode=True/False`
4. **默认值** `true`（开启调试）

### 示例

```bash
# 即使环境变量设置为 false，--debug 也会强制开启
DEBUG_MODE=false python door.py --debug

# 环境变量生效
DEBUG_MODE=false python door.py

# 代码中的参数会覆盖环境变量
# 在 Python 脚本中
import os
os.environ['DEBUG_MODE'] = 'false'
agent.run("test", debug_mode=True)  # 仍然开启调试
```

---

## 💡 最佳实践

### 开发阶段
```bash
# 保持调试开启，便于排查问题
python door.py
```

### 测试阶段
```bash
# 快速测试多个场景
python door.py --message "查询天气" --no-debug
python door.py --message "计算1+1" --no-debug
```

### 生产环境
```bash
# 设置环境变量，关闭调试
# Windows: setx DEBUG_MODE false
# Linux/Mac: export DEBUG_MODE=false
python door.py
```

### 集成到其他项目
```python
# 库文件中
from door import SimpleAgent, DEBUG_MODE

class MyApplication:
    def __init__(self):
        self.agent = SimpleAgent(...)
    
    def process(self, query):
        # 根据应用配置决定是否调试
        return self.agent.run(query, debug_mode=self.config.debug)
```

---

## ⚠️ 注意事项

1. **性能影响**：调试模式会增加少量 I/O 开销，但对 API 调用时间无影响
2. **日志长度**：调试模式下，过长的输出会被截断显示（前200-300字符）
3. **环境变量持久化**：使用 `set` 或 `$env:` 设置的变量仅在当前终端会话有效
4. **默认行为**：未指定任何参数时，默认开启调试模式

---

## 🎨 自定义输出

如果想修改调试输出的格式，可以编辑 `door.py` 中的 `run` 方法：

```python
# 修改这些部分来自定义输出
if debug_mode:
    print(f"\n{'─'*60}")  # 分隔线样式
    print(f"📍 第 {step}/{max_steps} 步")  # 步骤显示
    print(f"💭 AI思考过程:")  # 标题文本
```

---

## 📞 问题排查

### Q: 设置了环境变量但不生效？
A: 检查是否在当前终端会话中设置，或者是否拼写正确（区分大小写）

### Q: 如何临时关闭某次运行的调试？
A: 使用 `python door.py --no-debug`

### Q: 想在代码中动态切换？
A: 使用 `agent.run(query, debug_mode=False)`

---

**最后更新**: 2026-06-11
