<script setup>
import { computed, ref } from 'vue'
import { renderMarkdown, formatTime } from '../utils/markdown'
import { extractEnglishPhrase, isEnglishText } from '../utils/phraseExtractor'
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

// Render markdown content
const renderedContent = computed(() => {
  if (isError.value) return props.message.content
  return renderMarkdown(props.message.content || '')
})

// TTS 相关状态
const isPlaying = ref(false)
const highlightedText = ref('')

// TTS播放器实例
const ttsPlayer = getTTSPlayer()

/**
 * 处理文本点击事件
 */
async function handleTextClick(event) {
  // 只处理assistant消息的点击
  if (!isAssistant.value) return

  // 如果正在播放，停止播放
  if (isPlaying.value) {
    ttsPlayer.stop()
    isPlaying.value = false
    highlightedText.value = ''
    return
  }

  // 获取点击的文本节点
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return

  const range = selection.getRangeAt(0)
  const clickNode = range.startContainer
  const clickOffset = range.startOffset

  // 获取容器元素
  const container = event.currentTarget
  if (!container) return

  // 提取英语短语
  const phrase = extractEnglishPhrase(container, clickNode, clickOffset)

  // 验证是否为英语文本
  if (!phrase || !isEnglishText(phrase)) {
    return
  }

  // 播放语音
  try {
    isPlaying.value = true
    highlightedText.value = phrase

    await ttsPlayer.play(phrase)

    // 播放完成后清除高亮
    ttsPlayer.audio.addEventListener('ended', () => {
      isPlaying.value = false
      highlightedText.value = ''
    }, { once: true })
  } catch (error) {
    console.error('TTS播放失败:', error)
    isPlaying.value = false
    highlightedText.value = ''
  }

  // 清除选择
  selection.removeAllRanges()
}

/**
 * 处理触摸事件（移动端）
 */
function handleTouchEnd(event) {
  handleTextClick(event)
}
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
        :class="{ 'is-playing': isPlaying }"
        v-html="renderedContent"
        @click="handleTextClick"
        @touchend="handleTouchEnd"
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
  transition: background-color var(--transition-fast);
}

.message-bubble.assistant .content-text.tts-content:active {
  background-color: var(--bg-secondary);
}

.message-bubble.assistant .content-text.tts-content.is-playing {
  background-color: var(--bg-secondary);
  border-color: var(--accent-color);
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
