/**
 * NPC语音消息解析器
 * 解析 Agent 回复中的 📢 name: content 模式
 */

/**
 * 解析NPC消息模式
 * 匹配格式: 📢 名字: 内容
 * 支持跨行匹配和同一行多个消息
 *
 * 模式说明:
 * - 📢\s+ - 喇叭emoji + 至少一个空格
 * - ([^:\n]+) - 捕获名字（不含冒号和换行）
 * - :\s* - 冒号 + 可选空格
 * - ([\s\S]+?) - 捕获内容（非贪婪）
 * - (?=\s*📢\s+[^:\n]+:|$) - 前瞻：下一个NPC消息或字符串结尾
 */
const NPC_PATTERN = /📢\s+([^:\n]+):\s*([\s\S]+?)(?=\s*📢\s+[^:\n]+:|$)/g

/**
 * 从文本中解析出所有NPC语音消息
 * @param {string} content - Agent回复的完整内容
 * @returns {Array<{name: string, content: string, raw: string}>} NPC消息列表
 */
export function parseNpcMessages(content) {
  if (!content || !content.includes('📢')) {
    return []
  }

  const messages = []
  let match

  // 重置正则的lastIndex
  NPC_PATTERN.lastIndex = 0

  while ((match = NPC_PATTERN.exec(content)) !== null) {
    const name = match[1].trim()
    const speechContent = match[2].trim()

    if (name && speechContent) {
      messages.push({
        name,
        content: speechContent,
        raw: match[0] // 原始匹配的文本
      })
    }
  }

  return messages
}

/**
 * 检查消息是否包含NPC语音
 * @param {string} content - 消息内容
 * @returns {boolean}
 */
export function hasNpcMessages(content) {
  return content && content.includes('📢')
}

/**
 * 从内容中移除NPC消息部分，返回剩余文本
 * @param {string} content - 原始内容
 * @returns {string} 移除NPC消息后的内容
 */
export function removeNpcMessages(content) {
  if (!content || !content.includes('📢')) {
    return content
  }

  return content.replace(NPC_PATTERN, '').trim()
}

/**
 * 转换消息结构，将包含NPC的消息转换为多条消息
 * @param {Object} message - 原始消息对象
 * @returns {Array} 转换后的消息列表
 */
export function expandNpcMessages(message) {
  if (message.role !== 'assistant' || !hasNpcMessages(message.content)) {
    return [message]
  }

  const npcMessages = parseNpcMessages(message.content)
  const remainingContent = removeNpcMessages(message.content)

  const result = []

  // 添加NPC语音消息
  for (const npc of npcMessages) {
    result.push({
      role: 'npc_voice',
      npcName: npc.name,
      content: npc.content,
      timestamp: message.timestamp,
      // 保存原始消息引用用于状态管理
      _originalMessage: message
    })
  }

  // 如果有剩余内容，添加为普通assistant消息
  if (remainingContent) {
    result.push({
      role: 'assistant',
      content: remainingContent,
      timestamp: message.timestamp
    })
  }

  return result
}
