/**
 * Badminton Match Score Tracker
 * 羽毛球比赛记分系统 - 前端逻辑
 */

// ==================== 数据结构 ====================

/**
 * 比赛数据结构
 * {
 *   id: string,          // 唯一标识
 *   round: number,       // 轮次
 *   court: number,       // 场地号
 *   type: string,        // 类型：混双/男双/女双
 *   teamA: string[],     // 队伍 A 球员名单
 *   teamB: string[],     // 队伍 B 球员名单
 *   scoreA: [number, number], // 队伍 A 比分 [局 1, 局 2]
 *   scoreB: [number, number], // 队伍 B 比分 [局 1, 局 2]
 *   status: string       // pending/in-progress/finished
 * }
 */

// ==================== 全局状态 ====================

let appData = {
    eventName: '2026 马年首秀战',
    courtCount: 3,
    matches: [],
    playerStats: {} // { playerName: { total: 0, 男双：0, 女双：0, 混双：0 } }
};

let currentCourt = 1;
let currentMatchId = null;

// ==================== 默认对阵数据（示例） ====================

const DEFAULT_MATCHES = [
    // 1 号场地
    { id: 'm1', round: 1, court: 1, type: '混双', teamA: ['林锋', '李祺祺'], teamB: ['王小波', '谢卓珊'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm2', round: 1, court: 1, type: '男双', teamA: ['罗蒙', '陈顺星'], teamB: ['陈小洪', '卢志辉'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm3', round: 2, court: 1, type: '女双', teamA: ['唐英武', '高洁'], teamB: ['崔倩男', '林小连'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm4', round: 3, court: 1, type: '混双', teamA: ['林锋', '谢卓珊'], teamB: ['王小波', '李祺祺'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm5', round: 4, court: 1, type: '男双', teamA: ['严勇文', '罗蒙'], teamB: ['陈顺星', '陈小洪'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm6', round: 5, court: 1, type: '混双', teamA: ['林锋', '唐英武'], teamB: ['王小波', '高洁'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    
    // 2 号场地
    { id: 'm7', round: 1, court: 2, type: '男双', teamA: ['严勇文', '江锐'], teamB: ['罗琴荩', '卢志辉'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm8', round: 1, court: 2, type: '混双', teamA: ['陈顺星', '崔倩男'], teamB: ['罗琴荩', '唐英武'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm9', round: 2, court: 2, type: '男双', teamA: ['林锋', '王小波'], teamB: ['罗蒙', '江锐'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm10', round: 3, court: 2, type: '女双', teamA: ['李祺祺', '谢卓珊'], teamB: ['高洁', '林小连'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm11', round: 4, court: 2, type: '混双', teamA: ['陈顺星', '林小连'], teamB: ['罗琴荩', '崔倩男'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm12', round: 5, court: 2, type: '男双', teamA: ['严勇文', '陈小洪'], teamB: ['江锐', '卢志辉'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    
    // 3 号场地
    { id: 'm13', round: 1, court: 3, type: '女双', teamA: ['李祺祺', '唐英武'], teamB: ['谢卓珊', '高洁'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm14', round: 2, court: 3, type: '混双', teamA: ['林锋', '崔倩男'], teamB: ['陈顺星', '李祺祺'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm15', round: 3, court: 3, type: '男双', teamA: ['王小波', '罗蒙'], teamB: ['严勇文', '江锐'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm16', round: 4, court: 3, type: '女双', teamA: ['唐英武', '林小连'], teamB: ['崔倩男', '谢卓珊'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
    { id: 'm17', round: 5, court: 3, type: '混双', teamA: ['王小波', '林小连'], teamB: ['罗琴荩', '唐英武'], scoreA: [0, 0], scoreB: [0, 0], status: 'pending' },
];

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', function() {
    loadData();
    // renderMatches() 和 updateEventName() 在 loadData 的异步回调中调用
    switchCourt(1);  // 初始化时切换到 1 号场地，确保 tab 样式正确
});

// ==================== 数据持久化 ====================

function loadData() {
    const saved = localStorage.getItem('badminton_match_data');
    if (saved) {
        try {
            appData = JSON.parse(saved);
        } catch (e) {
            console.error('加载数据失败:', e);
            appData.matches = [...DEFAULT_MATCHES];
        }
    } else {
        // 首次访问时，尝试从 data.json 加载
        fetch('data.json')
            .then(res => res.json())
            .then(data => {
                if (data.eventName) {
                    appData.eventName = data.eventName;
                }
                if (data.matches && data.matches.length > 0) {
                    appData.matches = data.matches;
                } else {
                    appData.matches = [...DEFAULT_MATCHES];
                }
                if (data.courtCount) {
                    appData.courtCount = data.courtCount;
                }
                calculatePlayerStats();
                renderMatches();
                updateEventName();
                saveData();
            })
            .catch(err => {
                console.error('加载 data.json 失败:', err);
                appData.matches = [...DEFAULT_MATCHES];
                calculatePlayerStats();
            });
        return;  // 异步加载，直接返回
    }

    // 计算球员统计
    calculatePlayerStats();
}

function saveData() {
    localStorage.setItem('badminton_match_data', JSON.stringify(appData));
}

function resetData() {
    if (confirm('确定要重置所有比分数据吗？此操作不可恢复。')) {
        appData.matches = appData.matches.map(m => ({
            ...m,
            scoreA: [0, 0],
            scoreB: [0, 0],
            status: 'pending'
        }));
        appData.playerStats = {};
        saveData();
        renderMatches();
        alert('✅ 数据已重置');
    }
}

// ==================== 模拟比赛 ====================

function simulateAllMatches() {
    if (!confirm('🎲 模拟所有未完成的比赛？\n\n系统将为所有未开始的比赛随机生成比分。\n\n确定继续吗？')) {
        return;
    }
    
    let simulatedCount = 0;
    
    appData.matches.forEach(match => {
        if (match.status === 'pending') {
            // 生成随机比分（15 分制，有竞争性）
            const baseScore = 11;
            const variance = 4;
            
            const a1 = baseScore + Math.floor(Math.random() * variance) - Math.floor(variance / 2);
            const b1 = baseScore + Math.floor(Math.random() * variance) - Math.floor(variance / 2);
            
            // 确保第一局有胜负
            if (a1 === b1) {
                match.scoreA[0] = a1 + 1;
                match.scoreB[0] = b1;
            } else {
                match.scoreA[0] = Math.max(0, a1);
                match.scoreB[0] = Math.max(0, b1);
            }
            
            // 第二局
            const a2 = baseScore + Math.floor(Math.random() * variance) - Math.floor(variance / 2);
            const b2 = baseScore + Math.floor(Math.random() * variance) - Math.floor(variance / 2);
            
            if (a2 === b2) {
                match.scoreA[1] = a2 + 1;
                match.scoreB[1] = b2;
            } else {
                match.scoreA[1] = Math.max(0, a2);
                match.scoreB[1] = Math.max(0, b2);
            }
            
            match.status = 'finished';
            simulatedCount++;
        }
    });
    
    saveData();
    renderMatches();
    calculatePlayerStats();
    
    alert(`✅ 已模拟 ${simulatedCount} 场比赛！\n\n可以在统计中查看球员数据，或生成海报分享。`);
}

// ==================== 渲染比赛列表 ====================

function renderMatches() {
    for (let court = 1; court <= appData.courtCount; court++) {
        const container = document.getElementById(`matches-${court}`);
        if (!container) continue;
        
        const courtMatches = appData.matches.filter(m => m.court === court);
        container.innerHTML = courtMatches.map(match => renderMatchCard(match)).join('');
    }
}

function renderMatchCard(match) {
    const statusClass = match.status;
    const statusText = {
        'pending': '未开始',
        'in-progress': '进行中',
        'finished': '已结束'
    }[match.status];
    
    const scoreA1 = match.scoreA[0] || 0;
    const scoreA2 = match.scoreA[1] || 0;
    const scoreB1 = match.scoreB[0] || 0;
    const scoreB2 = match.scoreB[1] || 0;
    
    const totalA = scoreA1 + scoreA2;
    const totalB = scoreB1 + scoreB2;
    
    const winnerA = match.status === 'finished' && totalA > totalB;
    const winnerB = match.status === 'finished' && totalB > totalA;
    
    return `
        <div class="match-card ${statusClass}" onclick="openScoreModal('${match.id}')">
            <div class="match-header">
                <span class="match-round">第${match.round}轮</span>
                <span class="match-type ${match.type}">${match.type}</span>
            </div>
            <div class="match-teams">
                <div class="team ${winnerA ? 'winner' : ''}">
                    <span class="team-name">${match.teamA.join('/')}</span>
                    <span class="team-score-display">${match.status !== 'pending' ? scoreA1 : '-'}</span>
                </div>
                <div class="vs-divider">第 1 局</div>
                <div class="team ${winnerB ? 'winner' : ''}">
                    <span class="team-name">${match.teamB.join('/')}</span>
                    <span class="team-score-display">${match.status !== 'pending' ? scoreB1 : '-'}</span>
                </div>
            </div>
            ${match.status !== 'pending' ? `
                <div class="match-teams" style="margin-top: 8px;">
                    <div class="team ${winnerA ? 'winner' : ''}">
                        <span class="team-name"></span>
                        <span class="team-score-display">${scoreA2}</span>
                    </div>
                    <div class="vs-divider">第 2 局</div>
                    <div class="team ${winnerB ? 'winner' : ''}">
                        <span class="team-name"></span>
                        <span class="team-score-display">${scoreB2}</span>
                    </div>
                </div>
            ` : ''}
            <div class="match-status ${statusClass}">${statusText}${match.status === 'finished' ? ` (${scoreA1}:${scoreB1}, ${scoreA2}:${scoreB2})` : ''}</div>
        </div>
    `;
}

// ==================== 场地切换 ====================

function switchCourt(court) {
    currentCourt = court;
    
    // 更新 Tab 样式
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', parseInt(tab.dataset.court) === court);
    });
    
    // 更新场地显示
    document.querySelectorAll('.court-section').forEach(section => {
        section.style.display = 'none';
    });
    document.getElementById(`court-${court}`).style.display = 'block';
}

// ==================== 比分录入弹窗 ====================

function openScoreModal(matchId) {
    currentMatchId = matchId;
    const match = appData.matches.find(m => m.id === matchId);
    if (!match) return;
    
    // 填充弹窗信息
    document.getElementById('modal-match-info').innerHTML = `
        <div class="teams">${match.teamA.join('/')} VS ${match.teamB.join('/')}</div>
        <div class="type">${match.type} | 第${match.round}轮 | ${match.court}号场地</div>
    `;
    
    // 填充当前比分
    document.getElementById('score-a1').value = match.scoreA[0] || '';
    document.getElementById('score-a2').value = match.scoreA[1] || '';
    document.getElementById('score-b1').value = match.scoreB[0] || '';
    document.getElementById('score-b2').value = match.scoreB[1] || '';
    
    // 显示弹窗
    document.getElementById('score-modal').classList.add('show');
}

function closeModal() {
    document.getElementById('score-modal').classList.remove('show');
    currentMatchId = null;
}

function saveScore() {
    const match = appData.matches.find(m => m.id === currentMatchId);
    if (!match) return;
    
    const a1 = parseInt(document.getElementById('score-a1').value) || 0;
    const a2 = parseInt(document.getElementById('score-a2').value) || 0;
    const b1 = parseInt(document.getElementById('score-b1').value) || 0;
    const b2 = parseInt(document.getElementById('score-b2').value) || 0;
    
    match.scoreA = [a1, a2];
    match.scoreB = [b1, b2];
    
    // 判断比赛状态
    if (a1 === 0 && a2 === 0 && b1 === 0 && b2 === 0) {
        match.status = 'pending';
    } else if (a2 === 0 && b2 === 0) {
        match.status = 'in-progress';
    } else {
        match.status = 'finished';
    }
    
    saveData();
    renderMatches();
    calculatePlayerStats();
    closeModal();
}

function clearScore() {
    const match = appData.matches.find(m => m.id === currentMatchId);
    if (!match) return;
    
    match.scoreA = [0, 0];
    match.scoreB = [0, 0];
    match.status = 'pending';
    
    document.getElementById('score-a1').value = '';
    document.getElementById('score-a2').value = '';
    document.getElementById('score-b1').value = '';
    document.getElementById('score-b2').value = '';
    
    saveData();
    renderMatches();
    calculatePlayerStats();
}

// ==================== 球员统计 ====================

function calculatePlayerStats() {
    appData.playerStats = {};
    
    appData.matches.forEach(match => {
        if (match.status === 'finished') {
            [...match.teamA, ...match.teamB].forEach(player => {
                if (!appData.playerStats[player]) {
                    appData.playerStats[player] = { total: 0, '男双': 0, '女双': 0, '混双': 0 };
                }
                appData.playerStats[player].total++;
                appData.playerStats[player][match.type]++;
            });
        }
    });
}

function showStats() {
    renderStats('all');
    document.getElementById('stats-modal').classList.add('show');
}

function closeStatsModal() {
    document.getElementById('stats-modal').classList.remove('show');
}

// ==================== 战绩分析 ====================

function showAnalysis() {
    // 填充球员选择下拉框
    const select = document.getElementById('analysis-player-select');
    const players = Object.keys(appData.playerStats).sort();
    
    select.innerHTML = '<option value="">-- 全部球员 --</option>' + 
        players.map(p => `<option value="${p}">${p}</option>`).join('');
    
    document.getElementById('analysis-modal').classList.add('show');
    renderAnalysis();
}

function closeAnalysisModal() {
    document.getElementById('analysis-modal').classList.remove('show');
}

function renderAnalysis() {
    const selectedPlayer = document.getElementById('analysis-player-select').value;
    const finishedMatches = appData.matches.filter(m => m.status === 'finished');
    
    // 筛选比赛
    let playerMatches = [];
    if (selectedPlayer) {
        playerMatches = finishedMatches.filter(m => 
            m.teamA.includes(selectedPlayer) || m.teamB.includes(selectedPlayer)
        );
    } else {
        playerMatches = finishedMatches;
    }
    
    // 计算统计
    let wins = 0, losses = 0, totalGames = 0;
    let setsWon = 0, setsLost = 0;
    
    playerMatches.forEach(match => {
        const scoreA1 = match.scoreA[0] || 0;
        const scoreA2 = match.scoreA[1] || 0;
        const scoreB1 = match.scoreB[0] || 0;
        const scoreB2 = match.scoreB[1] || 0;
        
        // 计算局分
        if (scoreA1 > scoreB1) setsWon++; else setsLost++;
        if (scoreA2 > scoreB2) setsWon++; else setsLost++;
        
        // 计算胜负
        const totalA = scoreA1 + scoreA2;
        const totalB = scoreB1 + scoreB2;
        
        if (selectedPlayer) {
            const isTeamA = match.teamA.includes(selectedPlayer);
            const playerWon = (isTeamA && totalA > totalB) || (!isTeamA && totalB > totalA);
            if (playerWon) wins++; else losses++;
        }
        
        totalGames++;
    });
    
    // 显示汇总
    const winRate = totalGames > 0 ? Math.round(wins / totalGames * 100) : 0;
    const summaryHtml = `
        <div class="analysis-card">
            <div class="value">${wins}-${losses}</div>
            <div class="label">胜负</div>
        </div>
        <div class="analysis-card win">
            <div class="value">${winRate}%</div>
            <div class="label">胜率</div>
        </div>
        <div class="analysis-card">
            <div class="value">${setsWon}-${setsLost}</div>
            <div class="label">局分</div>
        </div>
    `;
    document.getElementById('analysis-summary').innerHTML = summaryHtml;
    
    // 显示比赛列表
    const listHtml = playerMatches.length === 0 ? 
        '<div style="text-align:center;color:#999;padding:20px;">暂无比赛数据</div>' :
        playerMatches
            .sort((a, b) => b.round - a.round)
            .map(match => {
                const scoreA1 = match.scoreA[0] || 0;
                const scoreA2 = match.scoreA[1] || 0;
                const scoreB1 = match.scoreB[0] || 0;
                const scoreB2 = match.scoreB[1] || 0;
                const totalA = scoreA1 + scoreA2;
                const totalB = scoreB1 + scoreB2;
                
                let isWin = false;
                let playerTeam = '';
                if (selectedPlayer) {
                    if (match.teamA.includes(selectedPlayer)) {
                        isWin = totalA > totalB;
                        playerTeam = match.teamA.join('/');
                    } else {
                        isWin = totalB > totalA;
                        playerTeam = match.teamB.join('/');
                    }
                }
                
                return `
                    <div class="analysis-item">
                        <div class="analysis-match-info">
                            <span class="analysis-match-type">${match.type}</span>
                            <span class="analysis-match-result ${selectedPlayer ? (isWin ? 'win' : 'loss') : ''}">
                                ${selectedPlayer ? (isWin ? '🏆 胜' : '❌ 负') : ''}
                            </span>
                        </div>
                        <div class="analysis-teams">
                            ${match.teamA.join('/')} 
                            <span style="color:#999;margin:0 8px;">VS</span> 
                            ${match.teamB.join('/')}
                        </div>
                        <div class="analysis-score">
                            比分：${scoreA1}:${scoreB1}  ${scoreA2}:${scoreB2}
                            ${selectedPlayer && isWin ? ' <span style="color:#11998e;font-weight:600;">(胜)</span>' : ''}
                            ${selectedPlayer && !isWin ? ' <span style="color:#f5a623;font-weight:600;">(负)</span>' : ''}
                        </div>
                    </div>
                `;
            })
            .join('');
    
    document.getElementById('analysis-list').innerHTML = listHtml;
}

function switchStatsTab(filter) {
    document.querySelectorAll('.stats-tab').forEach(tab => {
        tab.classList.toggle('active', tab.textContent === {
            'all': '全部',
            'male': '男球员',
            'female': '女球员'
        }[filter]);
    });
    renderStats(filter);
}

function renderStats(filter) {
    const MALE_PLAYERS = [
        "苏大哲", "罗蒙", "江锐", "严勇文", "陈顺星", "陈小洪",
        "卢志辉", "林锋", "王小波", "刘继宇", "董广博", "林琪琛", "罗琴荩"
    ];
    
    const FEMALE_PLAYERS = [
        "田茜", "唐英武", "李祺祺", "高洁", "滕菲", "谢卓珊", "崔倩男", "林小连"
    ];
    
    let players = Object.keys(appData.playerStats);
    
    if (filter === 'male') {
        players = players.filter(p => MALE_PLAYERS.includes(p));
    } else if (filter === 'female') {
        players = players.filter(p => FEMALE_PLAYERS.includes(p));
    }
    
    // 按总场次排序
    players.sort((a, b) => appData.playerStats[b].total - appData.playerStats[a].total);
    
    const container = document.getElementById('stats-list');
    if (players.length === 0) {
        container.innerHTML = '<div style="text-align:center;color:#999;padding:20px;">暂无比赛数据</div>';
        return;
    }
    
    container.innerHTML = players.map(player => {
        const stats = appData.playerStats[player];
        return `
            <div class="stat-item">
                <span class="stat-player">${player}</span>
                <div class="stat-games">
                    <span class="total">总${stats.total}场</span>
                    <span>男${stats.男双}</span>
                    <span>女${stats.女双}</span>
                    <span>混${stats.混双}</span>
                </div>
            </div>
        `;
    }).join('');
}

// ==================== 数据导出/导入 ====================

function exportData() {
    const dataStr = JSON.stringify(appData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    // 文件名：活动名称_比分数据.json
    a.download = `${appData.eventName.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '_')}_比分数据.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function importData() {
    document.getElementById('import-file').click();
}

function handleFileImport(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const imported = JSON.parse(e.target.result);
            if (imported.matches && Array.isArray(imported.matches)) {
                if (confirm('导入将覆盖当前数据，确定继续吗？')) {
                    appData = imported;
                    saveData();
                    renderMatches();
                    calculatePlayerStats();
                    if (imported.eventName) {
                        updateEventName();
                    }
                    alert('导入成功！');
                }
            } else {
                alert('文件格式不正确');
            }
        } catch (err) {
            alert('文件解析失败：' + err.message);
        }
    };
    reader.readAsText(file);
    event.target.value = ''; // 重置 input
}

// ==================== 海报生成 ====================

function generatePoster() {
    // 更新海报内容
    document.getElementById('poster-event-name').textContent = appData.eventName;
    document.getElementById('poster-date').textContent = new Date().toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        weekday: 'long'
    });
    
    // 计算汇总
    const finishedMatches = appData.matches.filter(m => m.status === 'finished');
    const summary = `
        <div class="poster-summary">
            <div class="summary-item">
                <div class="summary-value">${appData.matches.length}</div>
                <div class="summary-label">总场次</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">${finishedMatches.length}</div>
                <div class="summary-label">已完成</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">${appData.courtCount}</div>
                <div class="summary-label">场地数</div>
            </div>
        </div>
    `;
    document.getElementById('poster-summary').innerHTML = summary;
    
    // 生成比赛列表
    const matchesHtml = appData.matches
        .sort((a, b) => a.court - b.court || a.round - b.round)
        .map(match => {
            const scoreA1 = match.scoreA[0] || 0;
            const scoreA2 = match.scoreA[1] || 0;
            const scoreB1 = match.scoreB[0] || 0;
            const scoreB2 = match.scoreB[1] || 0;
            const totalA = scoreA1 + scoreA2;
            const totalB = scoreB1 + scoreB2;
            
            return `
                <div class="poster-match">
                    <span class="poster-match-type">${match.type}</span>
                    <div class="poster-match-teams">
                        <span class="poster-team" style="${match.status === 'finished' && totalA > totalB ? 'font-weight:600;color:#11998e' : ''}">
                            ${match.teamA.join('/')}
                        </span>
                        <span class="poster-score">
                            ${match.status !== 'pending' ? `${scoreA1}:${scoreB1}  ${scoreA2}:${scoreB2}` : 'VS'}
                        </span>
                        <span class="poster-team" style="${match.status === 'finished' && totalB > totalA ? 'font-weight:600;color:#11998e' : ''}">
                            ${match.teamB.join('/')}
                        </span>
                    </div>
                </div>
            `;
        })
        .join('');
    
    document.getElementById('poster-matches').innerHTML = matchesHtml;
    
    // 显示海报容器
    const posterContainer = document.getElementById('poster-container');
    posterContainer.style.display = 'block';
    const poster = document.getElementById('poster');
    
    // 使用 html2canvas 生成图片
    html2canvas(poster, {
        scale: 2,
        backgroundColor: '#ffffff',
        logging: false,
        useCORS: true
    }).then(canvas => {
        // 转换为图片并下载
        canvas.toBlob(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${appData.eventName.replace(/[^a-zA-Z0-9]/g, '_')}_比分海报.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            // 隐藏海报容器
            posterContainer.style.display = 'none';
            
            // 提示用户
            alert('✅ 海报已生成并下载！\n\n图片已保存到你的下载文件夹，可以直接分享到微信群。');
        }, 'image/png');
    }).catch(err => {
        console.error('海报生成失败:', err);
        alert('海报生成失败，请截图保存。\n\n（提示：滚动到页面底部可以看到海报）');
    });
}

// ==================== 活动名称编辑 ====================

function editEventName() {
    const newName = prompt('请输入活动名称：', appData.eventName);
    if (newName && newName.trim()) {
        appData.eventName = newName.trim();
        saveData();
        updateEventName();
    }
}

function updateEventName() {
    document.getElementById('event-name').textContent = appData.eventName;
    document.getElementById('poster-event-name').textContent = appData.eventName;
}

// ==================== 工具函数 ====================

// 关闭弹窗（点击背景）
document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', function(e) {
        if (e.target === this) {
            this.classList.remove('show');
        }
    });
});

// 阻止弹窗内容点击关闭
document.querySelectorAll('.modal-content').forEach(content => {
    content.addEventListener('click', function(e) {
        e.stopPropagation();
    });
});
