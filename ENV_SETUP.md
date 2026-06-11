# 环境变量配置说明

## API密钥配置

本项目使用阿里云通义千问（DashScope）API，需要配置以下环境变量：

### DASHSCOPE_API_KEY
你的阿里云DashScope API密钥。

#### Windows PowerShell 设置方法：
```powershell
$env:DASHSCOPE_API_KEY="sk-your-api-key-here"
```

#### Windows CMD 设置方法：
```cmd
set DASHSCOPE_API_KEY=sk-your-api-key-here
```

#### 永久设置（推荐）：
1. 右键"此电脑" → "属性" → "高级系统设置"
2. 点击"环境变量"
3. 在"用户变量"或"系统变量"中新建：
   - 变量名：`DASHSCOPE_API_KEY`
   - 变量值：你的API密钥
4. 重启终端或IDE

---

## 其他环境变量

### DEBUG_MODE
控制调试模式（可选，默认为 `true`）

```powershell
$env:DEBUG_MODE="false"  # 关闭调试模式
$env:DEBUG_MODE="true"   # 开启调试模式（默认）
```

---

## 快速启动示例

### PowerShell：
```powershell
$env:DASHSCOPE_API_KEY="sk-your-api-key-here"
python app.py
```

### 创建 .env 文件（如果使用 python-dotenv）：
```
DASHSCOPE_API_KEY=sk-your-api-key-here
DEBUG_MODE=true
```

---

## 安全提示

⚠️ **重要**：
- 不要将API密钥硬编码在代码中
- 不要将包含密钥的文件提交到Git
- 建议使用环境变量或 `.env` 文件管理密钥
- 在 `.gitignore` 中添加 `.env` 文件
