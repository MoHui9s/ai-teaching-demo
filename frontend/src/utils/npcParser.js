/**
 * NPC发言解析工具
 * 解析Agent回复中的NPC发言格式: 📢 人名: 内容
 */

/**
 * NPC发言正则模式
 * 匹配格式: 📢 后跟可选空格，然后是人名，然后是英文冒号，然后是发言内容
 *
 * 限制匹配范围：
 * - 不跨 markdown 水平线（---）匹配
 * - 不跨代码块匹配
 * - 单个 NPC 消息内容不会太长（最多1000字符）
 */
const NPC_PATTERN = /📢\s*([^:\n：]+)[:：]\s*([^\-\n][\s\S]{0,1000}?)(?=\s*(?:---|\n\n\n|📢|$))/g

/**
 * 解析Agent回复，提取NPC发言和剩余文本
 *
 * @param {string} content - Agent回复内容
 * @returns {Object} { npcMessages: Array<{name, content}>, remainingText: string }
 *
 * @example
 * const result = parseNpcContent("普通文本 📢 Tom: Hello! 📢 Ben: Hi!")
 * // 结果:
 * // {
 * //   npcMessages: [
 * //     { name: 'Tom', content: 'Hello!' },
 * //     { name: 'Ben', content: 'Hi!' }
 * //   ],
 * //   remainingText: '普通文本 '
 * // }
 */
export function parseNpcContent(content) {
  if (!content || typeof content !== 'string') {
    return { npcMessages: [], remainingText: content || '' }
  }

  const npcMessages = []
  let remainingText = content
  let match

  // 重置正则索引
  NPC_PATTERN.lastIndex = 0

  // 查找所有NPC发言
  while ((match = NPC_PATTERN.exec(content)) !== null) {
    const [fullMatch, name, npcContent] = match

    // 清理人名（去除首尾空格和 markdown 标记）
    const cleanName = name.trim().replace(/[*_~`]/g, '')
    // 清理内容（去除首尾空格和换行）
    const cleanContent = npcContent.trim()

    if (cleanName && cleanContent) {
      npcMessages.push({
        name: cleanName,
        content: cleanContent
      })
    }

    // 从剩余文本中移除已匹配的部分
    remainingText = remainingText.replace(fullMatch, '').trim()
  }

  return {
    npcMessages,
    remainingText
  }
}

/**
 * 检查内容是否包含NPC发言
 *
 * @param {string} content - 要检查的内容
 * @returns {boolean} 是否包含NPC发言
 */
export function hasNpcContent(content) {
  if (!content || typeof content !== 'string') {
    return false
  }
  NPC_PATTERN.lastIndex = 0
  return NPC_PATTERN.test(content)
}

/**
 * 为NPC发言创建语音消息对象
 *
 * @param {Object} npc - { name, content }
 * @param {string} timestamp - ISO时间戳
 * @returns {Object} 语音消息对象
 */
/**
 * 清洗 Markdown 格式标记，返回纯文本用于 TTS
 * 移除：*, _, #, `, ~, [, ], (, ), >, | 等格式标记
 */
export function stripMarkdown(text) {
  if (!text || typeof text !== 'string') return text

  return text
    // 移除水平线
    .replace(/^[-*_]{3,}\s*$/gm, '')
    // 移除标题标记
    .replace(/^#{1,6}\s+/gm, '')
    // 移除粗体/斜体标记（保留内部文本）
    .replace(/\*\*\*(.+?)\*\*\*/g, '$1')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/___(.+?)___/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/_(.+?)_/g, '$1')
    // 移除删除线
    .replace(/~~(.+?)~~/g, '$1')
    // 移除行内代码
    .replace(/`(.+?)`/g, '$1')
    // 移除链接 [text](url)
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1')
    // 移除图片 ![alt](url)
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1')
    // 移除引用标记
    .replace(/^>\s+/gm, '')
    // 移除列表标记
    .replace(/^[\s]*[-*+]\s+/gm, '')
    .replace(/^\d+\.\s+/gm, '')
    // 移除表格管道符
    .replace(/\|/g, ' ')
    // 移除残留的星号和下划线
    .replace(/[*_~`]/g, '')
    // 合并多余空白
    .replace(/\s+/g, ' ')
    .trim()
}

export function createVoiceMessage(npc, timestamp = new Date().toISOString()) {
  return {
    role: 'npc-voice',
    npcName: npc.name,
    content: npc.content,
    timestamp
  }
}
