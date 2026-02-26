// 用户兑换页面JavaScript

// HTML转义函数 - 防止XSS攻击
function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) {
        return '';
    }
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// 全局变量
let currentEmail = '';
let currentCode = '';
let selectedRedeemType = 'team'; // 默认 team

// Toast提示函数
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    let icon = 'info';
    if (type === 'success') icon = 'check-circle';
    if (type === 'error') icon = 'alert-circle';

    toast.innerHTML = `<i data-lucide="${icon}"></i><span>${message}</span>`;
    toast.className = `toast ${type} show`;

    if (window.lucide) {
        lucide.createIcons();
    }

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// 切换步骤
function showStep(stepNumber) {
    document.querySelectorAll('.step').forEach(step => {
        step.classList.remove('active');
    });
    document.getElementById(`step${stepNumber}`).classList.add('active');
}

// 返回步骤1
function backToStep1() {
    showStep(1);
}

// 选择兑换类型
function selectType(type) {
    selectedRedeemType = type;
    const teamBtn = document.getElementById('typeTeamBtn');
    const plusBtn = document.getElementById('typePlusBtn');
    const emailHelp = document.getElementById('emailHelp');

    if (type === 'team') {
        teamBtn.classList.add('active');
        plusBtn.classList.remove('active');
        emailHelp.textContent = '请使用您的常用邮箱,邀请将发送到此邮箱';
    } else {
        teamBtn.classList.remove('active');
        plusBtn.classList.add('active');
        emailHelp.textContent = '请输入您的邮箱以关联兑换记录';
    }

    if (window.lucide) lucide.createIcons();
}

// 复制文本到剪贴板
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('已复制到剪贴板', 'success');
    } catch (e) {
        // fallback
        const input = document.createElement('input');
        input.value = text;
        document.body.appendChild(input);
        input.select();
        document.execCommand('copy');
        document.body.removeChild(input);
        showToast('已复制到剪贴板', 'success');
    }
}

// 步骤1: 验证兑换码并直接兑换
document.getElementById('verifyForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = document.getElementById('email').value.trim();
    const code = document.getElementById('code').value.trim();
    const verifyBtn = document.getElementById('verifyBtn');

    // 验证
    if (!email || !code) {
        showToast('请填写完整信息', 'error');
        return;
    }

    // 保存到全局变量
    currentEmail = email;
    currentCode = code;

    // 禁用按钮
    verifyBtn.disabled = true;
    verifyBtn.textContent = '正在兑换...';

    // 调用兑换接口
    await confirmRedeem();

    // 恢复按钮状态
    verifyBtn.disabled = false;
    verifyBtn.innerHTML = '<i data-lucide="shield-check"></i> 立即兑换';
    if (window.lucide) lucide.createIcons();
});

// 确认兑换
async function confirmRedeem() {
    try {
        const response = await fetch('/redeem/confirm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: currentEmail,
                code: currentCode,
                redeem_type: selectedRedeemType,
                team_id: null
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            if (data.redeem_type === 'plus') {
                showPlusResult(data);
            } else {
                showTeamResult(data);
            }
        } else {
            const errorMessage = data.detail || data.error || '兑换失败';
            showErrorResult(errorMessage);
        }
    } catch (error) {
        showErrorResult('网络错误,请稍后重试');
    }
}

// 显示 Team 兑换结果
function showTeamResult(data) {
    const resultContent = document.getElementById('resultContent');
    const teamInfo = data.team_info || {};

    resultContent.innerHTML = `
        <div class="result-success">
            <div class="result-icon"><i data-lucide="check-circle" style="width: 64px; height: 64px; color: var(--success);"></i></div>
            <div class="result-title">兑换成功!</div>
            <div class="result-message">${escapeHtml(data.message) || '您已成功加入 Team'}</div>

            <div class="result-details">
                <div class="result-detail-item">
                    <span class="result-detail-label">Team 名称</span>
                    <span class="result-detail-value">${escapeHtml(teamInfo.team_name) || '-'}</span>
                </div>
                <div class="result-detail-item">
                    <span class="result-detail-label">邮箱地址</span>
                    <span class="result-detail-value">${escapeHtml(currentEmail)}</span>
                </div>
                ${teamInfo.expires_at ? `
                <div class="result-detail-item">
                    <span class="result-detail-label">到期时间</span>
                    <span class="result-detail-value">${formatDate(teamInfo.expires_at)}</span>
                </div>
                ` : ''}
            </div>

            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 2rem; background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px;">
                邀请邮件已发送到您的邮箱，请查收并按照邮件指引接受邀请。
            </p>

            <button onclick="location.reload()" class="btn btn-primary">
                <i data-lucide="refresh-cw"></i> 再次兑换
            </button>
        </div>
    `;
    if (window.lucide) lucide.createIcons();
    showStep(3);
}

// 显示 Plus 兑换结果
function showPlusResult(data) {
    const resultContent = document.getElementById('resultContent');
    const plusInfo = data.plus_info || {};

    resultContent.innerHTML = `
        <div class="result-success">
            <div class="result-icon"><i data-lucide="check-circle" style="width: 64px; height: 64px; color: var(--success);"></i></div>
            <div class="result-title">兑换成功!</div>
            <div class="result-message">您的 Plus 账号信息如下</div>

            <div class="plus-info-card">
                <div class="plus-info-item">
                    <span class="plus-info-label">账号</span>
                    <span class="plus-info-value">
                        ${escapeHtml(plusInfo.email)}
                        <button class="copy-btn" onclick="copyToClipboard('${escapeHtml(plusInfo.email)}')">复制</button>
                    </span>
                </div>
                <div class="plus-info-item">
                    <span class="plus-info-label">密码</span>
                    <span class="plus-info-value">
                        ${escapeHtml(plusInfo.password)}
                        <button class="copy-btn" onclick="copyToClipboard('${escapeHtml(plusInfo.password)}')">复制</button>
                    </span>
                </div>
                ${plusInfo.verify_url ? `
                <div class="plus-info-item">
                    <span class="plus-info-label">接码链接</span>
                    <span class="plus-info-value">
                        <a href="${escapeHtml(plusInfo.verify_url)}" target="_blank">${escapeHtml(plusInfo.verify_url)}</a>
                        <button class="copy-btn" onclick="copyToClipboard('${escapeHtml(plusInfo.verify_url)}')">复制</button>
                    </span>
                </div>
                ` : ''}
            </div>

            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 2rem; background: rgba(255,255,255,0.05); padding: 1rem; border-radius: 8px;">
                ⚠️ 请立即保存以上信息！关闭页面后无法再次查看。
            </p>

            <button onclick="location.reload()" class="btn btn-primary">
                <i data-lucide="refresh-cw"></i> 再次兑换
            </button>
        </div>
    `;
    if (window.lucide) lucide.createIcons();
    showStep(3);
}

// 显示错误结果
function showErrorResult(errorMessage) {
    const resultContent = document.getElementById('resultContent');

    resultContent.innerHTML = `
        <div class="result-error">
            <div class="result-icon"><i data-lucide="x-circle" style="width: 64px; height: 64px; color: var(--danger);"></i></div>
            <div class="result-title">兑换失败</div>
            <div class="result-message">${escapeHtml(errorMessage)}</div>

            <div style="display: flex; gap: 1rem; justify-content: center; margin-top: 2rem;">
                <button onclick="backToStep1()" class="btn btn-secondary">
                    <i data-lucide="arrow-left"></i> 返回重试
                </button>
                <button onclick="location.reload()" class="btn btn-primary">
                    <i data-lucide="rotate-ccw"></i> 重新开始
                </button>
            </div>
        </div>
    `;
    if (window.lucide) lucide.createIcons();

    showStep(3);
}

// 格式化日期
function formatDate(dateString) {
    if (!dateString) return '-';

    try {
        const date = new Date(dateString);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    } catch (e) {
        return dateString;
    }
}
