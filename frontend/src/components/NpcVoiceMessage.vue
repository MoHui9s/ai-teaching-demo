<script setup>
import { ref, computed, onUnmounted, watch } from 'vue'
import { getTTSPlayer } from '../utils/ttsAudioPlayer'

const props = defineProps({
  npcName: {
    type: String,
    required: true
  },
  content: {
    type: String,
    required: true
  },
  timestamp: String,
  autoPlay: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['play-start', 'play-end', 'play-next'])

// 播放状态
const isPlaying = ref(false)
const isLoading = ref(false)
const isPlayed = ref(false) // 是否已播放过

// 文本展开状态
const isExpanded = ref(false)

// TTS播放器
const ttsPlayer = getTTSPlayer()

// 计算第一行文本
const firstLine = computed(() => {
  const lines = props.content.split('\n')
  return lines[0]
})

// 是否有多行
const hasMoreLines = computed(() => {
  return props.content.includes('\n')
})

// 是否显示展开按钮
const showExpandButton = computed(() => {
  return hasMoreLines.value && !isExpanded.value
})

// 播放语音
async function playVoice() {
  if (isLoading.value) return

  // 如果正在播放，停止播放
  if (isPlaying.value) {
    stopVoice()
    return
  }

  isLoading.value = true

  try {
    emit('play-start')
    await ttsPlayer.play(props.content, 'en-US-AriaNeural')
    isLoading.value = false
    isPlaying.value = true
    isPlayed.value = true

    // 播放结束后清理
    const onEnded = () => {
      isPlaying.value = false
      isLoading.value = false
      emit('play-end')
      ttsPlayer.audio.removeEventListener('ended', onEnded)
    }
    ttsPlayer.audio.addEventListener('ended', onEnded)

  } catch (error) {
    console.error('NPC语音播放失败:', error)
    isLoading.value = false
    emit('play-end')
  }
}

// 停止播放
function stopVoice() {
  if (isPlaying.value) {
    ttsPlayer.stop()
    isPlaying.value = false
  }
}

// 切换文本展开
function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

// 监听自动播放
watch(() => props.autoPlay, (shouldPlay) => {
  if (shouldPlay && !isPlayed.value && !isLoading.value && !isPlaying.value) {
    // 延迟一点播放，让动画效果更好
    setTimeout(() => {
      playVoice()
    }, 100)
  }
}, { immediate: true })

// 组件卸载时清理
onUnmounted(() => {
  if (isPlaying.value) {
    stopVoice()
  }
})
</script>

<template>
  <div class="npc-voice-message">
    <!-- 语音控件行 -->
    <div
      class="voice-control"
      :class="{ playing: isPlaying, loading: isLoading, played: isPlayed }"
      @click="playVoice"
    >
      <div class="voice-icon">
        📢
      </div>
      <div class="npc-name">{{ npcName }}</div>

      <!-- 播放动画 - 类似微信声波 -->
      <div v-if="isPlaying" class="voice-wave">
        <span class="wave-bar"></span>
        <span class="wave-bar"></span>
        <span class="wave-bar"></span>
        <span class="wave-bar"></span>
        <span class="wave-bar"></span>
      </div>

      <!-- 加载中指示 -->
      <div v-else-if="isLoading" class="loading-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>

      <!-- 播放完成指示 -->
      <div v-else-if="isPlayed" class="play-indicator">
        ▶
      </div>

      <!-- 未播放指示 -->
      <div v-else class="play-indicator">
        ▶
      </div>
    </div>

    <!-- 文本内容 -->
    <div class="voice-content">
      <div class="content-text" :class="{ expanded: isExpanded }">
        {{ isExpanded ? content : firstLine }}
      </div>
      <button
        v-if="showExpandButton"
        class="expand-btn"
        @click="toggleExpand"
      >
        {{ isExpanded ? '收起' : '展开更多' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.npc-voice-message {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 85%;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 语音控件行 */
.voice-control {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: linear-gradient(135deg, #f8fafc, #e2e8f0);
  border: 1px solid #cbd5e1;
  border-radius: 20px 20px 20px 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.voice-control:hover {
  background: linear-gradient(135deg, #f1f5f9, #dbeafe);
  border-color: #94a3b8;
}

.voice-control:active {
  transform: scale(0.98);
}

.voice-control.playing {
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  border-color: #60a5fa;
  box-shadow: 0 0 12px rgba(96, 165, 250, 0.4);
}

.voice-control.loading {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  border-color: #fbbf24;
}

.voice-icon {
  font-size: 18px;
  line-height: 1;
}

.npc-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 14px;
}

/* 播放动画 - 声波效果 */
.voice-wave {
  display: flex;
  align-items: center;
  gap: 3px;
  margin-left: auto;
}

.voice-wave .wave-bar {
  width: 3px;
  height: 12px;
  background: #3b82f6;
  border-radius: 2px;
  animation: wave 1s ease-in-out infinite;
}

.voice-wave .wave-bar:nth-child(1) { animation-delay: 0s; }
.voice-wave .wave-bar:nth-child(2) { animation-delay: 0.1s; }
.voice-wave .wave-bar:nth-child(3) { animation-delay: 0.2s; }
.voice-wave .wave-bar:nth-child(4) { animation-delay: 0.3s; }
.voice-wave .wave-bar:nth-child(5) { animation-delay: 0.4s; }

@keyframes wave {
  0%, 100% {
    height: 4px;
  }
  50% {
    height: 16px;
  }
}

/* 加载动画 */
.loading-dots {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #f59e0b;
  animation: bounce 1.4s infinite ease-in-out;
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

/* 播放指示 */
.play-indicator {
  margin-left: auto;
  font-size: 12px;
  color: #64748b;
}

.voice-control.playing .play-indicator,
.voice-control.loading .play-indicator {
  display: none;
}

/* 文本内容 */
.voice-content {
  padding-left: 12px;
}

.content-text {
  color: #475569;
  font-size: 14px;
  line-height: 1.6;
  word-wrap: break-word;
  overflow-wrap: break-word;

  /* 默认折叠：只显示一行 */
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.content-text.expanded {
  display: block;
  -webkit-line-clamp: unset;
}

.expand-btn {
  margin-top: 4px;
  padding: 4px 8px;
  font-size: 12px;
  color: #3b82f6;
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.2s;
}

.expand-btn:hover {
  color: #2563eb;
}

/* 移动端适配 */
@media (max-width: 480px) {
  .npc-voice-message {
    max-width: 90%;
  }

  .voice-control {
    padding: 6px 10px;
  }

  .npc-name {
    font-size: 13px;
  }
}
</style>
