const API = '/api/v1';

let state = {
  agents: [],
  currentAgentId: null,
  sessions: [],
  currentSessionId: null,
  messages: [],
  isGenerating: false
};

let generatingIndicatorEl = null;

function setGenerating(value) {
  state.isGenerating = value;
  const input = document.getElementById('message-input');
  const sendBtn = document.getElementById('send-btn');
  const recordBtn = document.getElementById('record-btn');
  input.disabled = value;
  sendBtn.disabled = value;
  recordBtn.disabled = value;
}

function showGeneratingIndicator() {
  if (generatingIndicatorEl) return;
  const el = messagesEl();
  const div = document.createElement('div');
  div.className = 'message assistant generating';
  div.id = 'generating-indicator';
  div.innerHTML = '<span class="generating-dots"><i></i><i></i><i></i></span><span class="generating-text">Generating...</span><div class="time"></div>';
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
  generatingIndicatorEl = div;
}

function removeGeneratingIndicator() {
  if (generatingIndicatorEl) {
    generatingIndicatorEl.remove();
    generatingIndicatorEl = null;
  }
}

async function request(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') return null;
  const contentType = res.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) return res.json();
  return res;
}

function agentListEl() { return document.getElementById('agents-list'); }
function chatSessionSelect() { return document.getElementById('chat-session-select'); }
function messagesEl() { return document.getElementById('messages'); }
function currentAgentNameEl() { return document.getElementById('current-agent-name'); }
function selectedSessionInfoEl() { return document.getElementById('selected-session-info'); }

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

async function loadAgents() {
  state.agents = await request('/agents');
  renderAgents();
  if (state.agents.length && !state.currentAgentId) {
    state.currentAgentId = state.agents[0].agent_id;
    currentAgentNameEl().textContent = state.agents[0].name;
    await loadSessions();
  }
}

function renderAgents() {
  const ul = agentListEl();
  ul.innerHTML = state.agents.map(a => `
    <li data-agent-id="${a.agent_id}">
      <span class="agent-label">${escapeHtml(a.name)}</span>
      <button type="button" class="btn btn-ghost" data-edit-agent>Edit</button>
    </li>
  `).join('');
}

function escapeHtml(s) {
  if (s == null || s === '') return '';
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

/** Render markdown to safe HTML for assistant messages. */
function renderMarkdown(text) {
  if (text == null || text === '') return '';
  try {
    if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
      const raw = typeof marked.parse === 'function' ? marked.parse(text) : String(text);
      const html = typeof raw === 'string' ? raw : escapeHtml(text);
      return DOMPurify.sanitize(html, { ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'blockquote', 'a', 'hr'], ALLOWED_ATTR: ['href', 'target'] });
    }
  } catch (_) {}
  return escapeHtml(text);
}

async function loadSessions() {
  if (!state.currentAgentId) return;
  state.sessions = await request(`/agents/${state.currentAgentId}/sessions`);
  const sel = chatSessionSelect();
  const prev = state.currentSessionId;
  sel.innerHTML = '<option value="">— Select chat —</option>' + state.sessions.map(s => {
    const time = formatTime(s.created_at);
    return `<option value="${s.session_id}">Chat ${s.session_id} (${time})</option>`;
  }).join('');
  if (prev && state.sessions.some(s => s.session_id === prev)) {
    sel.value = prev;
    state.currentSessionId = prev;
    await loadMessages();
  } else if (state.sessions.length) {
    sel.value = state.sessions[0].session_id;
    state.currentSessionId = state.sessions[0].session_id;
    selectedSessionInfoEl().textContent = `Selected session: session_${state.currentSessionId}`;
    await loadMessages();
  } else {
    state.currentSessionId = null;
    state.messages = [];
    selectedSessionInfoEl().textContent = 'Selected session: —';
    renderMessages();
  }
}

async function loadMessages() {
  if (!state.currentSessionId) return;
  state.messages = await request(`/sessions/messages?session_id=${state.currentSessionId}`);
  selectedSessionInfoEl().textContent = `Selected session: session_${state.currentSessionId}`;
  renderMessages();
}

function renderMessages() {
  generatingIndicatorEl = null;
  const el = messagesEl();
  el.innerHTML = state.messages.map(m => {
    const isAssistant = m.role === 'assistant';
    const body = isAssistant ? renderMarkdown(m.content) : escapeHtml(m.content);
    return `<div class="message ${m.role}">
      <div class="content ${isAssistant ? 'markdown' : ''}">${body}</div>
      <div class="time">${formatTime(m.created_at)}</div>
    </div>`;
  }).join('');
  el.scrollTop = el.scrollHeight;
}

function appendStreamingMessage(content, time) {
  const el = messagesEl();
  const div = document.createElement('div');
  div.className = 'message assistant';
  div.innerHTML = `<div class="content markdown">${renderMarkdown(content)}</div><div class="time">${time || formatTime(new Date().toISOString())}</div>`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
  return div.querySelector('.content');
}

async function createAgent() {
  const name = document.getElementById('new-agent-name').value.trim();
  const prompt = document.getElementById('new-agent-prompt').value.trim();
  if (!name || !prompt) return alert('Name and prompt required');
  await request('/agents', { method: 'POST', body: JSON.stringify({ name, prompt }) });
  document.getElementById('new-agent-name').value = '';
  document.getElementById('new-agent-prompt').value = '';
  await loadAgents();
}

function openEditAgent(agent) {
  document.getElementById('edit-agent-section').classList.remove('hidden');
  document.getElementById('edit-agent-id').value = agent.agent_id;
  document.getElementById('edit-agent-name').value = agent.name;
  document.getElementById('edit-agent-prompt').value = agent.prompt;
}

async function saveAgent() {
  const id = document.getElementById('edit-agent-id').value;
  const name = document.getElementById('edit-agent-name').value.trim();
  const prompt = document.getElementById('edit-agent-prompt').value.trim();
  if (!name || !prompt) return alert('Name and prompt required');
  await request(`/agents/${id}`, { method: 'PUT', body: JSON.stringify({ name, prompt }) });
  document.getElementById('edit-agent-section').classList.add('hidden');
  await loadAgents();
  if (state.currentAgentId === parseInt(id, 10)) currentAgentNameEl().textContent = name;
}

async function newChat() {
  if (!state.currentAgentId) return alert('Select an agent first');
  const session = await request(`/agents/${state.currentAgentId}/sessions`, { method: 'POST' });
  state.sessions.unshift(session);
  state.currentSessionId = session.session_id;
  state.messages = [];
  const sel = chatSessionSelect();
  const time = formatTime(session.created_at);
  sel.innerHTML = '<option value="">— Select chat —</option>' + state.sessions.map(s => {
    const t = formatTime(s.created_at);
    return `<option value="${s.session_id}">Chat ${s.session_id} (${t})</option>`;
  }).join('');
  sel.value = session.session_id;
  selectedSessionInfoEl().textContent = `Selected session: session_${session.session_id}`;
  renderMessages();
}

async function sendMessage(useStream = true) {
  if (state.isGenerating) return;
  const input = document.getElementById('message-input');
  const content = input.value.trim();
  if (!content || !state.currentSessionId) return;
  input.value = '';

  setGenerating(true);
  removeGeneratingIndicator();

  const userMsg = { role: 'user', content, created_at: new Date().toISOString() };
  state.messages.push(userMsg);
  renderMessages();

  showGeneratingIndicator();

  try {
    if (useStream) {
      let full = '';
      let contentEl = null;
      const res = await fetch(API + '/sessions/messages/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: state.currentSessionId, content })
      });
      if (!res.ok) {
        removeGeneratingIndicator();
        const errMsg = 'Error: ' + (await res.text());
        appendStreamingMessage(errMsg, '');
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
                if (data.content) {
                full += data.content;
                if (!contentEl) {
                  removeGeneratingIndicator();
                  contentEl = appendStreamingMessage(full, '');
                } else {
                  contentEl.innerHTML = renderMarkdown(full);
                }
                messagesEl().scrollTop = messagesEl().scrollHeight;
              }
            } catch (_) {}
          }
        }
      }
      if (!contentEl) {
        removeGeneratingIndicator();
        contentEl = appendStreamingMessage(full || '(No response)', '');
      }
      state.messages.push({ role: 'assistant', content: full, created_at: new Date().toISOString() });
    } else {
      const reply = await request('/sessions/messages', {
        method: 'POST',
        body: JSON.stringify({ session_id: state.currentSessionId, content })
      });
      removeGeneratingIndicator();
      state.messages.push(reply);
      renderMessages();
    }
  } finally {
    setGenerating(false);
    removeGeneratingIndicator();
  }
}

let mediaRecorder = null;
let recordingChunks = [];
let recordingStartTime = 0;
let recordingStream = null;
let recordingMimeType = 'audio/webm';  // capture so onstop can use it after mediaRecorder is cleared
const MIN_RECORDING_MS = 800;  // minimum so STT gets enough audio

async function startRecording() {
  if (state.isGenerating) return;
  if (!state.currentSessionId) {
    setVoiceStatus('Select a chat first (or create a new chat).', true);
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recordingStream = stream;
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';
    mediaRecorder = new MediaRecorder(stream, { mimeType });
    recordingMimeType = mediaRecorder.mimeType || mimeType;
    recordingChunks = [];
    recordingStartTime = Date.now();
    mediaRecorder.ondataavailable = e => { if (e.data.size) recordingChunks.push(e.data); };
    mediaRecorder.onstop = async () => {
      if (recordingStream) {
        recordingStream.getTracks().forEach(t => t.stop());
        recordingStream = null;
      }
      const duration = Date.now() - recordingStartTime;
      if (duration < MIN_RECORDING_MS) {
        setVoiceStatus('Record at least ~1 second. Click mic, speak, then click again to send.', true);
        setTimeout(() => setVoiceStatus('Click mic to start recording, click again to send.'), 4000);
        return;
      }
      if (recordingChunks.length === 0) {
        setVoiceStatus('No audio captured. Try again and allow microphone when prompted.', true);
        setTimeout(() => setVoiceStatus('Click mic to start recording, click again to send.'), 4000);
        return;
      }
      const blob = new Blob(recordingChunks, { type: recordingMimeType });
      await sendVoice(blob);
    };
    mediaRecorder.start(250);
    document.getElementById('record-btn').classList.add('recording');
    document.getElementById('record-btn').querySelector('.mic-icon').textContent = '⏹';
    setVoiceStatus('Recording... Speak now. Click the mic again to send.');
  } catch (err) {
    console.error('Microphone error:', err);
    setVoiceStatus('Microphone access denied or unavailable. Check browser permissions.', true);
  }
}

function setVoiceStatus(text, isError = false) {
  const el = document.getElementById('voice-status');
  if (!el) return;
  el.textContent = text;
  el.style.color = isError ? '#b91c1c' : '#059669';
}

function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state !== 'recording') return;
  mediaRecorder.stop();
  mediaRecorder = null;
  const btn = document.getElementById('record-btn');
  btn.classList.remove('recording');
  const icon = btn.querySelector('.mic-icon');
  if (icon) icon.textContent = '🎤';
  setVoiceStatus('Sending...');
}

async function sendVoice(blob) {
  if (!state.currentSessionId) {
    setVoiceStatus('Select a chat first (or create a new chat).', true);
    return;
  }
  if (state.isGenerating) return;
  setGenerating(true);
  showGeneratingIndicator();
  setVoiceStatus('Processing voice...');
  try {
    const fd = new FormData();
    fd.append('session_id', state.currentSessionId);
    fd.append('audio', blob, 'audio.webm');
    const res = await fetch(API + '/sessions/voice', {
      method: 'POST',
      body: fd
    });
    if (!res.ok) {
      const errText = await res.text();
      const msg = errText.includes('no text') || errText.includes('Speech') || errText.includes('transcri')
        ? 'Could not transcribe audio. Speak clearly and record at least 1 second.'
        : (errText || res.statusText);
      setVoiceStatus(msg, true);
      setTimeout(() => setVoiceStatus('Click mic to start recording, click again to send.'), 5000);
      return;
    }
    const audioBlob = await res.blob();
    const url = URL.createObjectURL(audioBlob);
    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    audio.play();
    await loadMessages();
    setVoiceStatus('Click mic to start recording, click again to send.');
  } catch (err) {
    console.error('Voice send error:', err);
    setVoiceStatus('Failed to send voice. Check connection and try again.', true);
    setTimeout(() => setVoiceStatus('Click mic to start recording, click again to send.'), 5000);
  } finally {
    removeGeneratingIndicator();
    setGenerating(false);
  }
}

document.getElementById('create-agent-btn').addEventListener('click', createAgent);

document.getElementById('agents-list').addEventListener('click', e => {
  const btn = e.target.closest('[data-edit-agent]');
  if (btn) {
    const li = btn.closest('li');
    const id = li ? parseInt(li.dataset.agentId, 10) : 0;
    const agent = state.agents.find(a => a.agent_id === id);
    if (agent) openEditAgent(agent);
    e.stopPropagation();
    return;
  }
  const li = e.target.closest('li[data-agent-id]');
  if (!li) return;
  const id = parseInt(li.dataset.agentId, 10);
  state.currentAgentId = id;
  const agent = state.agents.find(a => a.agent_id === id);
  currentAgentNameEl().textContent = agent ? agent.name : '—';
  loadSessions();
});

document.getElementById('save-agent-btn').addEventListener('click', saveAgent);
document.getElementById('cancel-edit-btn').addEventListener('click', () => {
  document.getElementById('edit-agent-section').classList.add('hidden');
});

chatSessionSelect().addEventListener('change', async () => {
  const v = chatSessionSelect().value;
  state.currentSessionId = v ? parseInt(v, 10) : null;
  removeGeneratingIndicator();
  setGenerating(false);
  if (state.currentSessionId) await loadMessages();
  else {
    state.messages = [];
    selectedSessionInfoEl().textContent = 'Selected session: —';
    renderMessages();
  }
});

document.getElementById('new-chat-btn').addEventListener('click', newChat);

document.getElementById('send-btn').addEventListener('click', () => sendMessage(true));

document.getElementById('message-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(true);
  }
});

// Record button: click to start, click again to stop and send (toggle mode)
const recordBtn = document.getElementById('record-btn');
function onRecordClick(e) {
  e.preventDefault();
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    stopRecording();
  } else {
    startRecording();
  }
}
recordBtn.addEventListener('click', onRecordClick);
recordBtn.addEventListener('touchstart', e => { e.preventDefault(); onRecordClick(e); }, { passive: false });

loadAgents();
