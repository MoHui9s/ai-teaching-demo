<script setup>
import { computed, ref, watch, onMounted, nextTick } from 'vue'
import MessageBubble from './MessageBubble.vue'
import NpcVoiceMessage from './NpcVoiceMessage.vue'
import WelcomeScreen from './WelcomeScreen.vue'
import { expandNpcMessages } from '../utils/npcParser'

const props = defineProps({
  messages: Array,
  isLoading: Boolean,
  streamingContent: String
})

const isEmpty = computed(() => props.messages.length === 0)
const showStreaming = computed(() => props.isLoading || props.streamingContent)

// Use a fixed timestamp for streaming message to prevent re-renders
const streamingTimestamp = ref('')
const streamingKey = ref('')

// NPC语音自动播放控制
const autoPlayNpcIndex = ref(-1)
const lastNpcCount = ref(0)
const isInitialized = ref(false)

// 计算当前消息中NPC消息的索引
const getNpcIndex = (msg) => {
  let npcIndex = 0
  for (const m of displayMessages.value) {
    if (m === msg) return npcIndex
    if (m.role === 'npc_voice') npcIndex++
  }
  return -1
}

// 展开所有NPC消息为独立条目
const displayMessages = computed(() => {
  const result = []

  for (const msg of props.messages) {
    // 如果是assistant消息，检查是否包含NPC语音
    if (msg.role === 'assistant') {
      const expanded = expandNpcMessages(msg)
      result.push(...expanded)
    } else {
      result.push(msg)
    }
  }

  // 添加streaming消息（如果有）
  if (showStreaming.value && props.streamingContent) {
    if (!streamingTimestamp.value) {
      streamingTimestamp.value = new Date().toISOString()
      streamingKey.value = `streaming-${Date.now()}`
    }
    result.push({
      role: 'assistant',
      content: props.streamingContent,
      timestamp: streamingTimestamp.value,
      streaming: true
    })
  } else {
    // Reset when not streaming
    streamingTimestamp.value = ''
    streamingKey.value = ''
  }

  return result
})

// 获取NPC语音消息列表（用于自动播放）
const npcVoiceMessages = computed(() => {
  return displayMessages.value.filter(msg => msg.role === 'npc_voice')
})

// 监听NPC消息变化，触发自动播放
watch(npcVoiceMessages, (newNpcMessages, oldNpcMessages) => {
  const newCount = newNpcMessages.length
  // 如果是初始化阶段（autoPlayNpcIndex为-1且lastNpcCount为0），跳过
  if (autoPlayNpcIndex.value === -1 && lastNpcCount.value === 0) {
    console.log('[NPC AutoPlay] Initialization phase, skipping')
    // 更新lastNpcCount
    lastNpcCount.value = newCount
    return
  }
  // 只在初始化完成后才处理自动播放
  if (!isInitialized.value) return

  console.log('[NPC AutoPlay] npcVoiceMessages changed:', {
    newCount,
    lastCount: lastNpcCount.value,
    shouldPlay: newCount > lastNpcCount.value
  })
  if (newCount > lastNpcCount.value) {
    // 有新的NPC语音消息，开始自动播放第一个新消息
    // 从上次的数量开始播放
    autoPlayNpcIndex.value = lastNpcCount.value
    console.log('[NPC AutoPlay] Setting autoPlayNpcIndex to:', autoPlayNpcIndex.value)
    lastNpcCount.value = newCount
  }
}, { deep: true })

// 组件挂载时初始化
onMounted(async () => {
  const npcCount = npcVoiceMessages.value.length
  if (npcCount > 0) {
    lastNpcCount.value = npcCount
  }
  // 延迟标记初始化完成，确保watch不会在初始化时触发
  setTimeout(() => {
    isInitialized.value = true
  }, 100)
})
</script>

<template>
  <div class="message-list">
    <!-- Welcome Screen -->
    <WelcomeScreen v-if="isEmpty" />

    <!-- Messages -->
    <template v-else>
      <template v-for="(msg, index) in displayMessages" :key="msg.streaming ? streamingKey : `${msg.role}-${index}`">
        <!-- NPC语音消息 -->
        <NpcVoiceMessage
          v-if="msg.role === 'npc_voice'"
          :npc-name="msg.npcName"
          :content="msg.content"
          :timestamp="msg.timestamp"
          :auto-play="autoPlayNpcIndex === getNpcIndex(msg)"
          @play-end="() => { autoPlayNpcIndex = getNpcIndex(msg) + 1 }"
        />
        <!-- 普通消息 -->
        <MessageBubble
          v-else
          :message="msg"
          :is-streaming="msg.streaming"
        />
      </template>

      <!-- Loading indicator -->
      <div v-if="isLoading && !streamingContent" class="typing-indicator">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.message-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  padding-bottom: var(--spacing-sm);
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--spacing-sm) var(--spacing-md);
  width: fit-content;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.16s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.32s; }

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
</style>
