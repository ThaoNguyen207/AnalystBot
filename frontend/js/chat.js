/* chat.js — Chat widget logic */

let chatOpen = false;

function toggleChat() {
  chatOpen = !chatOpen;
  document.getElementById('chatPanel').classList.toggle('open', chatOpen);
  document.getElementById('chatFab').textContent = chatOpen ? '✕' : '💬';
  if (chatOpen) document.getElementById('chatInput').focus();
}

function sendQuick(text) {
  document.getElementById('chatInput').value = text;
  sendChat();
}

async function sendChat() {
  const input = document.getElementById('chatInput');
  const text  = input.value.trim();
  if (!text) return;
  input.value = '';

  appendMsg(text, 'user');
  const typing = appendTyping();

  try {
    const res = await apiPost('/api/chat/', {
      message: text,
      session_id: currentSessionId || null,
    });

    typing.remove();
    handleBotResponse(res);
  } catch (e) {
    typing.remove();
    appendMsg('❌ Lỗi kết nối: ' + e.message, 'bot');
  }
}

function handleBotResponse(res) {
  if (!res) return;

  // Show main message
  appendMsg(res.message || '...', 'bot');

  // If action needed, trigger it
  if (res.action === 'crawl' && res.slots?.url) {
    document.getElementById('urlInput').value = res.slots.url;
    setTimeout(() => appendMsg('🕷️ Đang crawl URL này trên Dashboard...', 'bot'), 600);
    setTimeout(() => doCrawl(), 1000);

  } else if (res.action === 'analyze') {
    setTimeout(() => doAnalyze(), 500);

  } else if (res.action === 'show_chart') {
    setTimeout(() => {
      document.getElementById('chartsGrid')?.scrollIntoView({ behavior: 'smooth' });
    }, 300);

  } else if (res.action === 'export') {
    exportCSV();

  } else if (res.action === 'history') {
    loadChatHistory();

  } else if (res.action === 'prompt_crawl') {
    setTimeout(() => {
      if (!chatOpen) toggleChat();
      document.getElementById('urlInput').focus();
    }, 400);
  }

  // Render data if any (top_n list)
  if (res.data && Array.isArray(res.data) && res.data.length) {
    renderTopList(res.data);
  } else if (res.data?.insights) {
    res.data.insights.forEach(i => appendMsg(i, 'bot'));
  }
}

function renderTopList(items) {
  const rows = items.map((p, i) => {
    let stats = '';
    if (p.goals !== undefined) stats += `<span title="Bàn thắng"> ⚽ ${p.goals}</span>`;
    if (p.assists !== undefined) stats += `<span title="Kiến tạo" style="margin-left:8px"> 🎯 ${p.assists}</span>`;
    
    return `<div style="border-bottom:1px solid rgba(255,255,255,0.07);padding:8px 0;font-size:0.85rem;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <b>${i + 1}. ${p.name || '—'}</b>
        <span style="color:#10b981;font-weight:600;">${p.price_raw || fmtPrice(p.price)}</span>
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:4px;">
        <span style="color:#94a3b8;font-size:0.75rem;">${p.team ? '🛡️ ' + p.team : (p.category || '')}</span>
        <div style="font-size:0.8rem;">${stats || (p.rating ? '⭐ ' + p.rating : '')}</div>
      </div>
    </div>`;
  }).join('');

  const el = document.createElement('div');
  el.className = 'msg bot';
  el.innerHTML = `
    <div class="msg-bubble" style="max-width:95%;width:95%;">
      ${rows}
    </div>`;
  document.getElementById('chatMessages').appendChild(el);
  scrollChat();
}

async function loadChatHistory() {
  try {
    const history = await apiGet('/api/chat/history?limit=5');
    if (!history.length) { appendMsg('📜 Chưa có lịch sử phân tích.', 'bot'); return; }
    appendMsg(`📜 **${history.length} câu hỏi gần nhất:**`, 'bot');
    history.slice(0, 5).forEach(h => {
      appendMsg(`❓ ${h.query}\n💬 ${h.insight}`, 'bot');
    });
  } catch (e) {
    appendMsg('❌ Không tải được lịch sử: ' + e.message, 'bot');
  }
}

// ── DOM helpers ───────────────────────────────────────────────────────────

function appendMsg(text, role) {
  const messages = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = `msg ${role}`;

  const now = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  const processed = text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>');

  div.innerHTML = `
    <div class="msg-bubble">${processed}</div>
    <div class="msg-time">${now}</div>`;
  messages.appendChild(div);
  scrollChat();
  return div;
}

function appendTyping() {
  const messages = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = 'msg bot';
  div.innerHTML = `
    <div class="msg-bubble">
      <div class="typing-dots">
        <span></span><span></span><span></span>
      </div>
    </div>`;
  messages.appendChild(div);
  scrollChat();
  return div;
}

function scrollChat() {
  const el = document.getElementById('chatMessages');
  el.scrollTop = el.scrollHeight;
}
