<script setup>
import { ref, onUnmounted } from 'vue'
import { formatTime } from '../utils/markdown'
import { getTTSPlayer } from '../utils/ttsAudioPlayer'
import { stripMarkdown } from '../utils/npcParser'

const props = defineProps({
  message: {
    type: Object,
    required: true
  },
  autoPlay: {
    type: Boolean,
    default: false
  }
})

// TTS 相关状态
const isLoading = ref(false)
const isPlaying = ref(false)

// TTS播放器实例
const ttsPlayer = getTTSPlayer()

// 格式化时间
const time = props.message.timestamp ? formatTime(props.message.timestamp) : ''

/**
 * 播放NPC语音
 */
async function playVoice() {
  const text = stripMarkdown(props.message.content)
  if (!text) return

  // 显示加载状态
  isLoading.value = true

  try {
    const result = await ttsPlayer.play(text)

    // 如果是从缓存加载，延迟一下再隐藏加载状态
    if (result.cached) {
      await new Promise(resolve => setTimeout(resolve, 200))
    }

    isLoading.value = false
    isPlaying.value = true

    // 播放完成后清除状态
    const onEnded = () => {
      isLoading.value = false
      isPlaying.value = false
      ttsPlayer.audio.removeEventListener('ended', onEnded)
    }
    ttsPlayer.audio.addEventListener('ended', onEnded)

  } catch (error) {
    console.error('NPC语音播放失败:', error)
    isLoading.value = false
    isPlaying.value = false
  }
}

// 仅在收到新消息时自动播放，加载历史消息时不播放
if (props.autoPlay) {
  playVoice().catch(err => {
    // 浏览器自动播放策略阻止时静默处理
    if (err.name === 'NotAllowedError') {
      console.log('自动播放被浏览器阻止，用户点击后可播放')
    }
  })
}

// 组件卸载时清理
onUnmounted(() => {
  // 如果是本组件触发的播放，停止播放
  if (isPlaying.value) {
    ttsPlayer.stop()
  }
})
</script>

<template>
  <div class="npc-voice-message">
    <!-- NPC信息 -->
    <div class="npc-info">
      <span class="npc-icon">📢</span>
      <span class="npc-name">{{ message.npcName }}</span>
    </div>

    <!-- 语音气泡 -->
    <div
      class="voice-bubble"
      :class="{ 'is-loading': isLoading, 'is-playing': isPlaying }"
      @click="playVoice"
    >
      <!-- 播放图标/动画 -->
      <div class="play-icon">
        <span v-if="isLoading" class="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </span>
        <span v-else-if="isPlaying" class="playing-waves">
          <span></span>
          <span></span>
          <span></span>
        </span>
        <span v-else class="play-triangle">▶</span>
      </div>

      <!-- 时长指示（模拟） -->
      <div class="duration">
        {{ isPlaying ? '播放中...' : isLoading ? '加载中...' : '点击播放' }}
      </div>

      <!-- 时间戳 -->
      <span v-if="time" class="timestamp">{{ time }}</span>
    </div>
  </div>
</template>

<style scoped>
.npc-voice-message {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-self: flex-start;
  max-width: 80%;
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

.npc-info {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 4px;
}

.npc-icon {
  font-size: 16px;
}

.npc-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.voice-bubble {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  border-bottom-left-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  user-select: none;
  transition: all var(--transition-fast);
  min-width: 140px;
}

.voice-bubble:hover {
  background: var(--bg-secondary);
}

.voice-bubble:active {
  transform: scale(0.98);
}

.voice-bubble.is-playing {
  background: var(--bg-secondary);
  border-color: var(--accent-color);
}

/* 播放图标 */
.play-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* 播放三角形 */
.play-triangle {
  font-size: 12px;
  color: var(--accent-color);
}

/* 加载点动画 */
.loading-dots {
  display: flex;
  gap: 4px;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-color);
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) { animation-delay: 0s; }
.loading-dots span:nth-child(2) { animation-delay: 0.16s; }
.loading-dots span:nth-child(3) { animation-delay: 0.32s; }

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* 播放波形动画 */
.playing-waves {
  display: flex;
  gap: 3px;
  align-items: center;
  height: 16px;
}

.playing-waves span {
  width: 3px;
  background: var(--accent-color);
  border-radius: 2px;
  animation: wave 0.8s ease-in-out infinite;
}

.playing-waves span:nth-child(1) { animation-delay: 0s; height: 8px; }
.playing-waves span:nth-child(2) { animation-delay: 0.1s; height: 12px; }
.playing-waves span:nth-child(3) { animation-delay: 0.2s; height: 16px; }

@keyframes wave {
  0%, 100% {
    transform: scaleY(0.5);
  }
  50% {
    transform: scaleY(1);
  }
}

/* 时长文字 */
.duration {
  flex: 1;
  font-size: 13px;
  color: var(--text-secondary);
}

.timestamp {
  font-size: 11px;
  color: var(--text-muted);
  padding: 0 4px;
}

@media (max-width: 480px) {
  .npc-voice-message {
    max-width: 90%;
  }

  .voice-bubble {
    min-width: 120px;
    padding: 10px 14px;
  }
}
</style>
