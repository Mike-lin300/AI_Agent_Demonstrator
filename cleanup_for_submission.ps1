# 清理不必要文件，准备提交作业
Write-Host "开始清理项目..." -ForegroundColor Green

# 删除虚拟环境
if (Test-Path "venv") {
    Write-Host "删除虚拟环境 venv/ ..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "venv"
}

# 删除缓存
if (Test-Path "__pycache__") {
    Write-Host "删除缓存 __pycache__/ ..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "__pycache__"
}

# 删除IDE配置
if (Test-Path ".idea") {
    Write-Host "删除IDE配置 .idea/ ..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".idea"
}

# 保留 agent_workspace 演示文件（不做任何操作）

Write-Host "清理完成！" -ForegroundColor Green
Write-Host ""
Write-Host "建议提交的文件：" -ForegroundColor Cyan
Write-Host "  ✓ app.py (Flask主程序)" -ForegroundColor White
Write-Host "  ✓ door.py (Agent核心逻辑)" -ForegroundColor White
Write-Host "  ✓ templates/index.html (前端页面)" -ForegroundColor White
Write-Host "  ✓ static/script.js (前端脚本)" -ForegroundColor White
Write-Host "  ✓ static/style.css (样式文件)" -ForegroundColor White
Write-Host "  ✓ requirements.txt (依赖列表)" -ForegroundColor White
Write-Host "  ✓ README.md (项目说明文档)" -ForegroundColor White
Write-Host "  ✓ ENV_SETUP.md (环境变量配置)" -ForegroundColor White
Write-Host "  ✓ agent_workspace/ (演示测试文件)" -ForegroundColor White
Write-Host ""
Write-Host "安装依赖命令：" -ForegroundColor Cyan
Write-Host "  pip install -r requirements.txt" -ForegroundColor White
Write-Host ""
Write-Host "设置API密钥（PowerShell）：" -ForegroundColor Cyan
Write-Host '  $env:DASHSCOPE_API_KEY="sk-your-api-key-here"' -ForegroundColor White
