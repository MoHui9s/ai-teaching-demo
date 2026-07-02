<script setup>
import { computed, ref, onUnmounted } from 'vue'
import { renderMarkdown, formatTime } from '../utils/markdown'
import { wrapEnglishPhrases, isEnglishText } from '../utils/phraseExtractor'
import { getTTSPlayer } from '../utils/ttsAudioPlayer'

const props = defineProps({
  message: {
    type: Object,
    required: true
  },
  isStreaming: Boolean
})

const isError = computed(() => props.message.role === 'error')
const isUser = computed(() => props.message.role === 'user')
const isAssistant = computed(() => props.message.role === 'assistant')

const avatar = computed(() => {
  if (isError.value) return '⚠️'
  if (isUser.value) return '👤'
  return '🤖'
})

const time = computed(() => {
  return props.message.timestamp ? formatTime(props.message.timestamp) : ''
})

// Render markdown content with span-wrapping for TTS
const renderedContent = computed(() => {
  if (isError.value) return props.message.content
  const html = renderMarkdown(props.message.content || '')
  return wrapEnglishPhrases(html)
})

// TTS 相关状态
const activePhraseEl = ref(null)

// TTS播放器实例
const ttsPlayer = getTTSPlayer()

/**
 * 清除当前激活短语的高亮
 */
function clearActiveHighlight() {
  if (activePhraseEl.value) {
    activePhraseEl.value.classList.remove('tts-loading', 'tts-playing')
    activePhraseEl.value = null
  }
}

/**
 * 处理文本点击事件 —— 事件委托在 .tts-phrase span 上
 */
async function handleTextClick(event) {
  if (!isAssistant.value) return

  if (ttsPlayer.isBusy) return

  // 通过 closest 定位目标短语 span（零坐标依赖）
  const phraseEl = event.target.closest('.tts-phrase')
  if (!phraseEl) return

  const phrase = phraseEl.dataset?.phrase
  if (!phrase || !isEnglishText(phrase)) return

  // 清除上一个高亮
  clearActiveHighlight()

  // 短语级加载动画
  phraseEl.classList.add('tts-loading')
  activePhraseEl.value = phraseEl

  try {
    const result = await ttsPlayer.play(phrase)

    if (result.cached) {
      await new Promise(resolve => setTimeout(resolve, 200))
    }

    phraseEl.classList.remove('tts-loading')
    phraseEl.classList.add('tts-playing')

    const onEnded = () => {
      clearActiveHighlight()
      ttsPlayer.audio.removeEventListener('ended', onEnded)
    }
    ttsPlayer.audio.addEventListener('ended', onEnded)

  } catch (error) {
    console.error('TTS播放失败:', error)
    clearActiveHighlight()
  }
}

// 组件卸载时清理
onUnmounted(() => {
  clearActiveHighlight()
  if (ttsPlayer.isPlaying && activePhraseEl.value) {
    ttsPlayer.stop()
  }
})
</script>

<template>
  <div :class="['message-bubble', message.role, { streaming: isStreaming, error: isError, 'tts-enabled': isAssistant }]">
    <!-- Avatar -->
    <div class="avatar">
      {{ avatar }}
    </div>

    <!-- Content -->
    <div class="bubble-content">
      <!-- Streaming: plain text for faster updates -->
      <div
        v-if="isStreaming"
        class="content-text streaming-content"
      >{{ message.content }}</div>
      <!-- Completed: rendered markdown with TTS click support -->
      <div
        v-else
        class="content-text tts-content"
        v-html="renderedContent"
        @click="handleTextClick"
      ></div>

      <!-- Timestamp -->
      <span v-if="time" class="timestamp">{{ time }}</span>
    </div>
  </div>
</template>

<style scoped>
.message-bubble {
  display: flex;
  gap: var(--spacing-xs);
  max-width: 90%;
  animation: messageIn 0.3s ease-out;
}

@keyframes messageIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-bubble.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-bubble.assistant {
  align-self: flex-start;
}

.message-bubble.error {
  align-self: center;
  max-width: 95%;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  margin-top: 4px;
}

.message-bubble.user .avatar {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  box-shadow: var(--shadow-sm);
}

.message-bubble.assistant .avatar {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
}

.message-bubble.error .avatar {
  background: var(--error-light);
  border: 1px solid var(--error-color);
}

.bubble-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.message-bubble.user .bubble-content {
  align-items: flex-end;
}

.message-bubble.assistant .bubble-content,
.message-bubble.error .bubble-content {
  align-items: flex-start;
}

.content-text {
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  word-wrap: break-word;
  overflow-wrap: break-word;
  line-height: 1.6;
  font-size: var(--font-size-base);
  max-width: 100%;
}

.message-bubble.user .content-text {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border-bottom-right-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
}

.message-bubble.assistant .content-text {
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-bottom-left-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
}

.message-bubble.error .content-text {
  background: var(--error-light);
  border: 1px solid var(--error-color);
  color: var(--error-color);
}

.message-bubble.streaming .content-text {
  position: relative;
}

.message-bubble.streaming .content-text::after {
  content: '';
  position: absolute;
  right: 12px;
  bottom: 8px;
  width: 8px;
  height: 8px;
  background: var(--accent-color);
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

/* Streaming content - preserve whitespace and format */
.message-bubble.streaming .streaming-content {
  white-space: pre-wrap;
  word-wrap: break-word;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

.timestamp {
  font-size: 11px;
  color: var(--text-muted);
  padding: 0 4px;
}

/* Markdown styles within content-text */
.content-text :deep(h1),
.content-text :deep(h2),
.content-text :deep(h3),
.content-text :deep(h4) {
  margin: 12px 0 8px;
  font-weight: 600;
  line-height: 1.3;
}

.content-text :deep(h1) { font-size: 1.4em; }
.content-text :deep(h2) { font-size: 1.25em; }
.content-text :deep(h3) { font-size: 1.1em; }

.content-text :deep(p) {
  margin: 6px 0;
}

.content-text :deep(p:first-child) {
  margin-top: 0;
}

.content-text :deep(p:last-child) {
  margin-bottom: 0;
}

/* TTS 点击交互样式 */
.message-bubble.assistant .content-text.tts-content {
  cursor: pointer;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

/* 短语级 span 样式 */
.content-text :deep(.tts-phrase) {
  border-radius: 3px;
  padding: 1px 0;
  transition: background-color 0.2s, box-shadow 0.2s;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

/* 加载中——脉冲动画 */
.content-text :deep(.tts-phrase.tts-loading) {
  animation: phrase-pulse 0.6s ease-in-out infinite;
}

@keyframes phrase-pulse {
  0%, 100% { background-color: rgba(99, 102, 241, 0.08); }
  50% { background-color: rgba(99, 102, 241, 0.22); }
}

/* 播放中——实色高亮 + box-shadow */
.content-text :deep(.tts-phrase.tts-playing) {
  background-color: rgba(99, 102, 241, 0.15);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.18);
}

.content-text :deep(ul),
.content-text :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.content-text :deep(li) {
  margin: 3px 0;
}

.content-text :deep(a) {
  color: var(--accent-color);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color var(--transition-fast);
}

.content-text :deep(a:hover) {
  border-bottom-color: var(--accent-color);
}

.message-bubble.user .content-text :deep(a) {
  color: white;
  border-bottom-color: rgba(255, 255, 255, 0.4);
}

.message-bubble.user .content-text :deep(a:hover) {
  border-bottom-color: white;
}

.content-text :deep(blockquote) {
  border-left: 3px solid var(--accent-color);
  padding-left: 14px;
  margin: 10px 0;
  color: var(--text-secondary);
  font-style: italic;
}

.content-text :deep(code) {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.9em;
}

.content-text :deep(:not(pre) > code) {
  background: var(--bg-secondary);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.message-bubble.user .content-text :deep(:not(pre) > code) {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.2);
}

.content-text :deep(pre) {
  margin: 10px 0;
  padding: 0;
  background: #1e293b;
  border-radius: var(--radius-md);
  overflow-x: auto;
}

@media (max-width: 480px) {
  .message-bubble {
    max-width: 95%;
  }

  .avatar {
    width: 28px;
    height: 28px;
    font-size: 14px;
  }

  .content-text {
    padding: 10px 14px;
    font-size: var(--font-size-sm);
  }
}
</style>
