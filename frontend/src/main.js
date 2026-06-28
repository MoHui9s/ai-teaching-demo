import { renderMarkdown, renderCodeBlock } from './ui.js';
import { SSEClient } from './sse.js';

const API_BASE = '';
const MAX_MESSAGE_LENGTH = 8000;

let currentUserId = localStorage.getItem('currentUserId') || 'default';
let messageHistory = [];
let isDarkMode = localStorage.getItem('darkMode') === 'true';
let userMessageCounts = {};

const sseClient = new SSEClient();

function init() {
  applyTheme();
  document.getElementById('user-id').value = currentUserId;
  setupEventListeners();
  setupScrollToBottom();
  setupAutoResize();
  setupCharCount();
  loadUserList();
  loadHistory();
}

function setupEventListeners() {
  document.getElementById('switch-user').addEventListener('click', handleSwitchUser);
  document.getElementById('new-user').addEventListener('click', handleNewUser);
  document.getElementById('load-history').addEventListener('click', loadHistory);
  document.getElementById('clear-history').addEventListener('click', handleClearHistory);
  document.getElementById('dark-mode').addEventListener('click', toggleDarkMode);
  document.getElementById('send-message').addEventListener('click', handleSendMessage);
  document.getElementById('stop-generation').addEventListener('click', () => {
    sseClient.stop();
    updateUIState(false);
    finishStreamingMessage(sseClient.accumulatedText);
  });

  document.getElementById('user-id').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleSwitchUser();
  });

  const messageInput = document.getElementById('message-input');
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });
}

function setupScrollToBottom() {
  const messagesContainer = document.getElementById('messages');
  const scrollButton = createScrollButton();

  messagesContainer.addEventListener('scroll', () => {
    const { scrollTop, scrollHeight, clientHeight } = messagesContainer;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    if (distanceFromBottom > 120) {
      scrollButton.style.display = 'flex';
    } else {
      scrollButton.style.display = 'none';
    }
  });
}

function createScrollButton() {
  const btn = document.createElement('button');
  btn.className = 'scroll-button';
  btn.textContent = '\u2193';
  btn.title = 'Scroll to bottom';
  btn.style.display = 'none';
  btn.addEventListener('click', () => {
    const messagesContainer = document.getElementById('messages');
    messagesContainer.scrollTo({ top: messagesContainer.scrollHeight, behavior: 'smooth' });
  });
  document.body.appendChild(btn);
  return btn;
}

function setupAutoResize() {
  const textarea = document.getElementById('message-input');
  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
  });
}

function setupCharCount() {
  const textarea = document.getElementById('message-input');
  const charCount = document.getElementById('char-count');
  textarea.addEventListener('input', () => {
    const len = textarea.value.length;
    if (len > 0) {
      charCount.textContent = `${len} / ${MAX_MESSAGE_LENGTH}`;
      if (len > MAX_MESSAGE_LENGTH * 0.9) {
        charCount.style.color = 'var(--warning-color)';
      } else {
        charCount.style.color = '';
      }
    } else {
      charCount.textContent = '';
    }
  });
}

function applyTheme() {
  const darkBtn = document.getElementById('dark-mode');
  if (isDarkMode) {
    document.documentElement.setAttribute('data-theme', 'dark');
    darkBtn.innerHTML = '<span class="btn-icon">&#9728;</span> Light Mode';
  } else {
    document.documentElement.removeAttribute('data-theme');
    darkBtn.innerHTML = '<span class="btn-icon">&#127769;</span> Dark Mode';
  }
}

function toggleDarkMode() {
  isDarkMode = !isDarkMode;
  localStorage.setItem('darkMode', isDarkMode);
  applyTheme();
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease-in';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

async function loadUserList() {
  try {
    const response = await fetch(`${API_BASE}/v1/users`);
    if (!response.ok) throw new Error('Failed to fetch users');
    const data = await response.json();

    const userListEl = document.getElementById('user-list');
    userListEl.innerHTML = '';

    if (!data.users || data.users.length === 0) {
      const emptyEl = document.createElement('div');
      emptyEl.style.cssText = 'padding: 20px; text-align: center; color: var(--text-muted); font-size: 13px;';
      emptyEl.textContent = 'No users yet. Create one above.';
      userListEl.appendChild(emptyEl);
      return;
    }

    data.users.forEach((user) => {
      const userItem = document.createElement('div');
      userItem.className = `user-item ${user.user_id === currentUserId ? 'active' : ''}`;

      const initial = user.user_id.charAt(0).toUpperCase();
      const count = user.message_count || userMessageCounts[user.user_id] || 0;
      userMessageCounts[user.user_id] = count;
      const countLabel = count === 1 ? '1 message' : `${count} messages`;

      userItem.innerHTML = `
        <div class="user-avatar">${initial}</div>
        <div class="user-info">
          <span class="user-id">${user.user_id}</span>
          <span class="user-count">${countLabel}</span>
        </div>
      `;

      userItem.addEventListener('click', () => {
        switchToUser(user.user_id);
      });

      userListEl.appendChild(userItem);
    });
  } catch (error) {
    console.error('Failed to load user list:', error);
  }
}

async function switchToUser(userId) {
  if (userId === currentUserId) return;

  currentUserId = userId;
  localStorage.setItem('currentUserId', userId);
  document.getElementById('user-id').value = userId;

  await loadHistory();
  loadUserList();
}

async function handleSwitchUser() {
  const newUserId = document.getElementById('user-id').value.trim();
  if (!newUserId) {
    showToast('Please enter a user ID', 'error');
    return;
  }
  await switchToUser(newUserId);
}

async function handleNewUser() {
  const newUserId = prompt('Enter new user ID:');
  if (!newUserId || !newUserId.trim()) return;

  const userId = newUserId.trim();
  await switchToUser(userId);
  loadUserList();
}

async function loadHistory() {
  try {
    const response = await fetch(`${API_BASE}/v1/users/${currentUserId}/history`);
    if (!response.ok) throw new Error(`Failed to load history (${response.status})`);
    const data = await response.json();

    messageHistory = data.messages || [];
    const count = data.count || messageHistory.length;
    userMessageCounts[currentUserId] = count;

    renderMessages();
    loadUserList();

    const messagesContainer = document.getElementById('messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  } catch (error) {
    console.error('Failed to load history:', error);
    showError('Failed to load history: ' + error.message);
  }
}

async function handleClearHistory() {
  if (!confirm('Are you sure you want to clear all conversation history for this user?')) return;

  try {
    const response = await fetch(`${API_BASE}/v1/users/${currentUserId}/history`, {
      method: 'DELETE',
    });

    if (!response.ok) throw new Error(`Failed to clear history (${response.status})`);

    messageHistory = [];
    userMessageCounts[currentUserId] = 0;
    renderMessages();
    loadUserList();
    showToast('History cleared', 'success');
  } catch (error) {
    console.error('Failed to clear history:', error);
    showError('Failed to clear history: ' + error.message);
  }
}

function renderMessages() {
  const messagesContainer = document.getElementById('messages');
  messagesContainer.innerHTML = '';

  const welcomeScreen = document.getElementById('welcome-screen');
  if (messageHistory.length === 0) {
    if (welcomeScreen) return;
    const welcome = createWelcomeScreen();
    messagesContainer.appendChild(welcome);
    return;
  }

  if (welcomeScreen) {
    welcomeScreen.remove();
    messagesContainer.innerHTML = '';
  }

  messageHistory.forEach((msg) => {
    if (msg.role === 'user' || msg.role === 'assistant') {
      appendMessageToUI(msg.role, msg.content, msg.timestamp);
    }
  });
}

function createWelcomeScreen() {
  const welcome = document.createElement('div');
  welcome.className = 'welcome-screen';
  welcome.id = 'welcome-screen';
  welcome.innerHTML = `
    <div class="welcome-icon">&#9889;</div>
    <h1>Welcome to Hermes</h1>
    <h2>Your Personal AI Assistant</h2>
    <p>Start a conversation below. Hermes remembers your context and can perform complex tasks with persistent memory.</p>
    <div class="welcome-features">
      <span class="welcome-feature">Persistent Memory</span>
      <span class="welcome-feature">Multi-User</span>
      <span class="welcome-feature">Markdown</span>
      <span class="welcome-feature">Code Highlighting</span>
    </div>
  `;
  return welcome;
}

function formatTime(isoString) {
  try {
    return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function appendMessageToUI(role, content, timestamp) {
  const messagesContainer = document.getElementById('messages');

  const welcomeScreen = document.getElementById('welcome-screen');
  if (welcomeScreen) welcomeScreen.remove();

  const messageEl = document.createElement('div');
  messageEl.className = `message ${role}`;

  const avatarEmoji = role === 'user' ? '\u{1F464}' : '\u{1F916}';
  const timeStr = timestamp ? formatTime(timestamp) : '';

  messageEl.innerHTML = `
    <div class="message-avatar">${avatarEmoji}</div>
    <div class="message-body">
      <div class="message-content">${renderCodeBlock(content || '')}</div>
      ${timeStr ? `<span class="message-time">${timeStr}</span>` : ''}
    </div>
  `;

  messagesContainer.appendChild(messageEl);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;

  return messageEl.querySelector('.message-content');
}

function updateStreamingMessage(content) {
  const streamingMessage = document.getElementById('streaming-message');
  if (!streamingMessage) return;

  const contentEl = streamingMessage.querySelector('.message-content');
  contentEl.innerHTML = renderCodeBlock(content);

  const messagesContainer = document.getElementById('messages');
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function finishStreamingMessage(content) {
  const streamingMessage = document.getElementById('streaming-message');
  if (streamingMessage) {
    streamingMessage.removeAttribute('id');
    const timeEl = streamingMessage.querySelector('.message-time');
    if (timeEl) {
      timeEl.textContent = formatTime(new Date().toISOString());
    } else {
      const timeSpan = document.createElement('span');
      timeSpan.className = 'message-time';
      timeSpan.textContent = formatTime(new Date().toISOString());
      streamingMessage.querySelector('.message-body').appendChild(timeSpan);
    }
  }
}

function showError(errorText) {
  const messagesContainer = document.getElementById('messages');
  const welcomeScreen = document.getElementById('welcome-screen');
  if (welcomeScreen) welcomeScreen.remove();

  const messageEl = document.createElement('div');
  messageEl.className = 'message error';

  messageEl.innerHTML = `
    <div class="message-avatar">&#9888;</div>
    <div class="message-body">
      <div class="message-content">${errorText}</div>
    </div>
  `;

  messagesContainer.appendChild(messageEl);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function updateUIState(isStreaming) {
  const sendButton = document.getElementById('send-message');
  const stopButton = document.getElementById('stop-generation');
  const messageInput = document.getElementById('message-input');

  sendButton.disabled = isStreaming;
  stopButton.style.display = isStreaming ? 'block' : 'none';
  messageInput.disabled = isStreaming;

  if (isStreaming) {
    sendButton.textContent = 'Thinking...';
  } else {
    sendButton.textContent = 'Send';
    messageInput.focus();
  }
}

async function handleSendMessage() {
  const messageInput = document.getElementById('message-input');
  const content = messageInput.value.trim();

  if (!content || sseClient.isStreaming()) {
    if (!content) messageInput.focus();
    return;
  }

  if (content.length > MAX_MESSAGE_LENGTH) {
    showToast(`Message too long (${content.length}/${MAX_MESSAGE_LENGTH})`, 'error');
    return;
  }

  messageInput.value = '';
  messageInput.style.height = 'auto';
  document.getElementById('char-count').textContent = '';

  appendMessageToUI('user', content, new Date().toISOString());
  messageHistory.push({ role: 'user', content });

  updateUIState(true);

  sseClient.onChunk = (accumulatedText) => {
    updateStreamingMessage(accumulatedText);
  };

  sseClient.onStatus = (status) => {
    const streamingMessage = document.getElementById('streaming-message');
    if (streamingMessage) {
      let statusEl = streamingMessage.querySelector('.message-status');
      if (!statusEl) {
        statusEl = document.createElement('div');
        statusEl.className = 'message-status';
        streamingMessage.querySelector('.message-body').appendChild(statusEl);
      }
      statusEl.textContent = status;
    }
  };

  sseClient.onDone = (finalText) => {
    finishStreamingMessage(finalText);
    messageHistory.push({ role: 'assistant', content: finalText });

    const streamingMessage = document.getElementById('streaming-message');
    if (streamingMessage) {
      const statusEl = streamingMessage.querySelector('.message-status');
      if (statusEl) statusEl.remove();
    }

    updateUIState(false);
  };

  sseClient.onError = (errorMessage) => {
    showError(errorMessage);
    updateUIState(false);
  };

  await sseClient.streamChat(messageHistory, currentUserId);
}

init();
