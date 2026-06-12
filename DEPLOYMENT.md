# 公网部署指南

## 推荐平台：Railway（免费且简单）

### 前置准备

1. **注册 Railway 账号**
   - 访问 https://railway.com
   - 使用 GitHub 账号登录

2. **准备 API Key**
   - 确保你有阿里云 DashScope API Key
   - 如果没有，访问 https://dashscope.console.aliyun.com/ 申请

---

## 部署步骤

### 方法一：通过 GitHub 自动部署（推荐）

#### 1. 将代码推送到 GitHub

```bash
# 初始化 Git（如果还没有）
git init
git add .
git commit -m "Initial commit for deployment"

# 创建 GitHub 仓库并推送
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

#### 2. 在 Railway 上部署

1. 登录 Railway 控制台
2. 点击 **"New Project"**
3. 选择 **"Deploy from GitHub repo"**
4. 选择你的仓库
5. Railway 会自动检测 Python 项目并开始构建

#### 3. 配置环境变量

在 Railway 项目页面：
1. 点击 **"Variables"** 标签
2. 添加以下环境变量：
   ```
   DASHSCOPE_API_KEY=sk-你的API密钥
   DEBUG_MODE=false
   PORT=5000
   ```

#### 4. 获取公网地址

部署成功后，Railway 会提供一个公网 URL，格式类似：
```
https://your-project-name.railway.app
```

---

### 方法二：通过 Railway CLI 部署

#### 1. 安装 Railway CLI

```bash
npm install -g @railway/cli
```

#### 2. 登录 Railway

```bash
railway login
```

#### 3. 初始化项目

```bash
railway init
```

#### 4. 设置环境变量

```bash
railway variables set DASHSCOPE_API_KEY="sk-你的API密钥"
railway variables set DEBUG_MODE="false"
```

#### 5. 部署

```bash
railway up
```

---

## 其他部署平台选项

### 选项 2：Render（免费套餐）

1. 访问 https://render.com
2. 创建 Web Service
3. 连接 GitHub 仓库
4. 配置：
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
5. 添加环境变量 `DASHSCOPE_API_KEY`

### 选项 3：Fly.io（有免费额度）

1. 安装 Fly CLI: `brew install flyctl` 或从官网下载
2. 登录: `fly auth login`
3. 初始化: `fly launch`
4. 设置密钥: `fly secrets set DASHSCOPE_API_KEY=sk-xxx`
5. 部署: `fly deploy`

### 选项 4：Vercel（需要适配）

注意：Vercel 更适合 Serverless 函数，Flask 应用需要使用 `vercel.json` 配置。

---

## 安全注意事项

⚠️ **重要：**

1. **永远不要将 API Key 提交到 Git**
   - 已配置 `.gitignore` 忽略 `.env` 文件
   - 使用平台的环境变量功能存储密钥

2. **生产环境禁用 Debug 模式**
   - 设置 `DEBUG_MODE=false`
   - 避免泄露敏感信息

3. **监控使用情况**
   - 定期检查 API 调用量
   - 设置预算告警

---

## 常见问题

### Q: 部署后无法访问？
A: 检查：
- 环境变量是否正确配置
- 应用是否成功启动（查看日志）
- 防火墙/安全组设置

### Q: 如何查看日志？
A: 
- Railway: 在项目页面的 "Logs" 标签
- Render: 在 Dashboard 中点击 "Logs"
- Fly.io: `fly logs`

### Q: 免费套餐有限制吗？
A: 
- Railway: 每月 $5 免费额度
- Render: 免费但会在闲置时休眠
- Fly.io: 有免费额度限制

### Q: 如何自定义域名？
A: 各平台都支持自定义域名，在设置中添加即可。

---

## 测试部署

部署完成后，访问你的公网 URL：
```
https://your-domain.com
```

应该能看到 ReAct Agent 的 Web 界面，可以正常进行对话和工具调用。

---

## 后续优化建议

1. **添加 HTTPS**（大多数平台自动提供）
2. **配置 CORS**（如果需要跨域访问）
3. **添加速率限制**（防止滥用）
4. **设置监控和告警**
5. **配置数据库**（如果需要持久化）
