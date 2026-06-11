// DOM 元素
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const debugModeCheckbox = document.getElementById('debug-mode');
const refreshFilesBtn = document.getElementById('refresh-files');
const clearWorkspaceBtn = document.getElementById('clear-workspace');
const fileListContainer = document.getElementById('file-list');
const quickButtons = document.querySelectorAll('.quick-btn');

// 是否正在处理请求
let isProcessing = false;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadFileList();
    
    // 发送按钮点击事件
    sendBtn.addEventListener('click', sendMessage);
    
    // 回车发送（Shift+Enter换行）
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // 快捷按钮事件
    quickButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const message = btn.getAttribute('data-message');
            userInput.value = message;
            sendMessage();
        });
    });
    
    // 刷新文件列表
    refreshFilesBtn.addEventListener('click', loadFileList);
    
    // 清空工作区
    clearWorkspaceBtn.addEventListener('click', clearWorkspace);
});

// 发送消息
async function sendMessage() {
    const message = userInput.value.trim();
    
    if (!message || isProcessing) {
        return;
    }
    
    // 禁用输入
    setProcessingState(true);
    
    // 添加用户消息到聊天区
    addMessage('user', message);
    
    // 清空输入框
    userInput.value = '';
    
    const debugMode = debugModeCheckbox.checked;
    
    // 如果开启调试模式，使用流式输出
    if (debugMode) {
        await sendStreamMessage(message);
    } else {
        // 非调试模式，使用传统方式
        await sendNormalMessage(message);
    }
    
    setProcessingState(false);
    userInput.focus();
}

// 流式发送消息（实时显示推理过程）
async function sendStreamMessage(message) {
    // 创建一个可折叠的推理过程容器
    const reasoningContainer = createReasoningContainer();
    chatMessages.appendChild(reasoningContainer);
    scrollToBottom();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                debug_mode: true,
                stream: true  // 启用流式输出
            })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResult = '';
        let history = [];
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // 保留未完成的行
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        handleStreamEvent(data, reasoningContainer);
                        
                        // 保存最终结果和历史
                        if (data.type === 'final') {
                            finalResult = data.result;
                            history = data.history;
                        }
                    } catch (e) {
                        console.error('解析SSE数据失败:', e);
                    }
                }
            }
            
            scrollToBottom();
        }
        
        // 添加最终答案
        if (finalResult) {
            addMessage('assistant', finalResult, history, true);
        }
        
    } catch (error) {
        addErrorMessage('网络错误：' + error.message);
    }
}

// 处理流式事件
function handleStreamEvent(data, container) {
    const stepsContainer = container.querySelector('.reasoning-steps');
    
    switch (data.type) {
        case 'start':
            container.querySelector('.reasoning-header span').textContent = '🤔 AI正在思考...';
            break;
            
        case 'thought':
            addReasoningStep(stepsContainer, data.step, 'thought', data.content);
            break;
            
        case 'action':
            addReasoningStep(stepsContainer, data.step, 'action', 
                `调用工具: ${data.tool}`, data.args);
            break;
            
        case 'observation':
            addReasoningStep(stepsContainer, data.step, 'observation', data.content);
            break;
            
        case 'final':
            container.querySelector('.reasoning-header span').textContent = '✅ 推理完成';
            container.classList.add('completed');
            break;
            
        case 'error':
            addErrorMessage(data.message);
            break;
    }
}

// 创建推理过程容器
function createReasoningContainer() {
    const container = document.createElement('div');
    container.className = 'reasoning-container';
    
    const header = document.createElement('div');
    header.className = 'reasoning-header';
    header.innerHTML = `
        <span>🤔 AI正在思考...</span>
        <button class="toggle-btn" onclick="toggleReasoning(this)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
        </button>
    `;
    
    const stepsContainer = document.createElement('div');
    stepsContainer.className = 'reasoning-steps';
    stepsContainer.style.display = 'block'; // 默认展开
    
    container.appendChild(header);
    container.appendChild(stepsContainer);
    
    return container;
}

// 添加推理步骤
function addReasoningStep(container, step, type, content, extraData = null) {
    const stepDiv = document.createElement('div');
    stepDiv.className = `reasoning-step step-${type}`;
    
    let icon, title;
    switch (type) {
        case 'thought':
            icon = '💭';
            title = `思考 #${step}`;
            break;
        case 'action':
            icon = '🔧';
            title = `工具调用 #${step}`;
            break;
        case 'observation':
            icon = '👁️';
            title = `观察结果 #${step}`;
            break;
    }
    
    const header = document.createElement('div');
    header.className = 'step-header';
    header.innerHTML = `<span>${icon} ${title}</span>`;
    stepDiv.appendChild(header);
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'step-content';
    contentDiv.textContent = content;
    stepDiv.appendChild(contentDiv);
    
    // 如果有额外数据（如工具参数），显示为JSON
    if (extraData) {
        const jsonDiv = document.createElement('pre');
        jsonDiv.className = 'step-json';
        jsonDiv.textContent = JSON.stringify(extraData, null, 2);
        stepDiv.appendChild(jsonDiv);
    }
    
    container.appendChild(stepDiv);
    
    // 自动滚动到新步骤
    stepDiv.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

// 切换推理过程展开/折叠
function toggleReasoning(button) {
    const container = button.closest('.reasoning-container');
    const steps = container.querySelector('.reasoning-steps');
    const svg = button.querySelector('svg');
    
    if (steps.style.display === 'none') {
        steps.style.display = 'block';
        svg.style.transform = 'rotate(0deg)';
    } else {
        steps.style.display = 'none';
        svg.style.transform = 'rotate(-90deg)';
    }
}

// 普通方式发送消息（非调试模式）
async function sendNormalMessage(message) {
    showThinkingIndicator();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                debug_mode: false,
                stream: false
            })
        });
        
        const data = await response.json();
        
        removeThinkingIndicator();
        
        if (data.success) {
            addMessage('assistant', data.result, data.history, false);
            loadFileList();
        } else {
            addErrorMessage(data.error || '发生未知错误');
        }
    } catch (error) {
        removeThinkingIndicator();
        addErrorMessage('网络错误：' + error.message);
    }
}

// 添加消息到聊天区
function addMessage(role, content, history = null, debugMode = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // 消息头部
    const headerDiv = document.createElement('div');
    headerDiv.className = 'message-header';
    headerDiv.textContent = role === 'user' ? '👤 你' : '🤖 AI Agent';
    contentDiv.appendChild(headerDiv);
    
    // 消息文本
    const textDiv = document.createElement('div');
    textDiv.className = 'message-text';
    textDiv.textContent = content;
    contentDiv.appendChild(textDiv);
    
    // 如果开启调试模式且有历史记录，显示详细过程
    if (debugMode && history && history.length > 0) {
        const debugDetails = createDebugDetails(history);
        contentDiv.appendChild(debugDetails);
    }
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // 滚动到底部
    scrollToBottom();
}

// 创建调试详情
function createDebugDetails(history) {
    const detailsDiv = document.createElement('details');
    detailsDiv.className = 'debug-info';
    
    const summary = document.createElement('summary');
    summary.textContent = '📊 查看完整推理过程';
    detailsDiv.appendChild(summary);
    
    // 遍历历史记录，提取Thought和Action
    let stepNumber = 1;
    for (let i = 0; i < history.length; i++) {
        const msg = history[i];
        
        if (msg.role === 'assistant') {
            // 提取 Thought
            const thoughtMatch = msg.content.match(/Thought:\s*([\s\S]*?)(?=Action:|Final Answer:|$)/);
            const actionMatch = msg.content.match(/Action:\s*({[\s\S]*?})/);
            const finalAnswerMatch = msg.content.match(/Final Answer:\s*([\s\S]*)/);
            
            if (thoughtMatch || actionMatch || finalAnswerMatch) {
                const stepDiv = document.createElement('div');
                stepDiv.className = 'debug-step';
                
                if (thoughtMatch) {
                    const thoughtP = document.createElement('p');
                    thoughtP.innerHTML = `<strong>💭 思考 ${stepNumber}:</strong><br>${escapeHtml(thoughtMatch[1].trim())}`;
                    stepDiv.appendChild(thoughtP);
                }
                
                if (actionMatch) {
                    try {
                        const actionObj = JSON.parse(actionMatch[1]);
                        const actionP = document.createElement('p');
                        actionP.innerHTML = `<strong>🔧 工具调用:</strong> ${actionObj.tool}<br><code>${JSON.stringify(actionObj.args, null, 2)}</code>`;
                        stepDiv.appendChild(actionP);
                    } catch (e) {
                        console.error('解析Action失败:', e);
                    }
                }
                
                if (finalAnswerMatch) {
                    const finalP = document.createElement('p');
                    finalP.innerHTML = `<strong>✅ 最终答案:</strong><br>${escapeHtml(finalAnswerMatch[1].trim())}`;
                    stepDiv.appendChild(finalP);
                }
                
                detailsDiv.appendChild(stepDiv);
                stepNumber++;
            }
        } else if (msg.role === 'user' && msg.content.startsWith('Observation:')) {
            // 观察结果
            const obsDiv = document.createElement('div');
            obsDiv.className = 'debug-step';
            obsDiv.innerHTML = `<strong>👁️ 观察结果 ${stepNumber - 1}:</strong><br><code>${escapeHtml(msg.content.substring(12))}</code>`;
            detailsDiv.appendChild(obsDiv);
        }
    }
    
    return detailsDiv;
}

// 显示思考指示器
function showThinkingIndicator() {
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'message message-assistant';
    thinkingDiv.id = 'thinking-indicator';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'thinking-indicator';
    contentDiv.innerHTML = `
        <span>AI正在思考</span>
        <div class="thinking-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    
    thinkingDiv.appendChild(contentDiv);
    chatMessages.appendChild(thinkingDiv);
    scrollToBottom();
}

// 移除思考指示器
function removeThinkingIndicator() {
    const indicator = document.getElementById('thinking-indicator');
    if (indicator) {
        indicator.remove();
    }
}

// 添加错误消息
function addErrorMessage(error) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message message-assistant';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.style.background = '#f8d7da';
    contentDiv.style.color = '#721c24';
    
    contentDiv.innerHTML = `
        <div class="message-header">❌ 错误</div>
        <div class="message-text">${escapeHtml(error)}</div>
    `;
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// 加载文件列表
async function loadFileList() {
    try {
        const response = await fetch('/api/list_files');
        const data = await response.json();
        
        if (data.success) {
            renderFileList(data.files);
        }
    } catch (error) {
        console.error('加载文件列表失败:', error);
    }
}

// 渲染文件列表
function renderFileList(files) {
    if (files.length === 0) {
        fileListContainer.innerHTML = '<p class="empty-text">暂无文件</p>';
        return;
    }
    
    fileListContainer.innerHTML = '';
    
    files.forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <span class="file-name">📄 ${escapeHtml(file.name)}</span>
            <span class="file-size">${file.size_human}</span>
        `;
        fileListContainer.appendChild(fileItem);
    });
}

// 清空工作区
async function clearWorkspace() {
    if (!confirm('确定要清空工作区的所有文件吗？此操作不可恢复！')) {
        return;
    }
    
    try {
        const response = await fetch('/api/clear_workspace', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(data.message);
            loadFileList();
        } else {
            alert('清空失败：' + data.error);
        }
    } catch (error) {
        alert('网络错误：' + error.message);
    }
}

// 设置处理状态
function setProcessingState(processing) {
    isProcessing = processing;
    sendBtn.disabled = processing;
    userInput.disabled = processing;
    
    if (processing) {
        sendBtn.innerHTML = '<span class="loading"></span> 处理中...';
    } else {
        sendBtn.innerHTML = `
            <span>发送</span>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
            </svg>
        `;
    }
}

// 滚动到底部
function scrollToBottom() {
    // 使用requestAnimationFrame确保DOM更新后再滚动
    requestAnimationFrame(() => {
        chatMessages.scrollTo({
            top: chatMessages.scrollHeight,
            behavior: 'smooth'
        });
    });
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
