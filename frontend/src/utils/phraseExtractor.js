/**
 * 英语短语提取工具
 * 从点击位置提取完整的英语短语或句子
 */

/**
 * 英语字符正则：匹配 [a-zA-Z0-9\s.,!?;:'"()-]
 */
const ENGLISH_CHARS = /[a-zA-Z0-9\s.,!?;:'"()-]/

/**
 * 单词边界字符（用于判断单词边界）
 */
const WORD_BOUNDARIES = /[^a-zA-Z0-9]/

/**
 * 获取所有 hr 元素在文本流中的位置
 * 通过遍历文本节点来计算 hr 之前有多少个字符
 */
function getHrBoundaries(element) {
  const boundaries = []
  let textPosition = 0

  // 遍历所有子节点
  const walker = document.createTreeWalker(
    element,
    NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
    null,
    false
  )

  let currentNode
  while ((currentNode = walker.nextNode())) {
    if (currentNode.nodeType === Node.TEXT_NODE) {
      // 文本节点：累加长度
      textPosition += currentNode.textContent.length
    } else if (currentNode.nodeName === 'HR') {
      // hr 元素：记录边界位置
      boundaries.push(textPosition)
    }
  }

  return boundaries
}

/**
 * 检查指定位置是否跨越了 hr 边界
 */
function crossesHrBoundary(position, hrBoundaries) {
  return hrBoundaries.includes(position)
}

/**
 * 从点击位置提取完整英语短语/句子
 *
 * @param {HTMLElement} element - 被点击的容器元素
 * @param {Node} clickNode - 点击的具体节点
 * @param {number} offset - 点击位置偏移
 * @returns {string} 提取的英语短语
 */
export function extractEnglishPhrase(element, clickNode, offset) {
  if (!clickNode) {
    return ''
  }

  // 获取 hr 边界位置
  const hrBoundaries = getHrBoundaries(element)

  // 获取纯文本内容
  const fullText = element.textContent

  if (!fullText) {
    return ''
  }

  // 计算点击位置在全文中的绝对位置
  const clickPosition = getAbsolutePosition(element, clickNode, offset)

  // 向前扫描：从点击位置向前查找，直到遇到非英语字符或开头
  let start = clickPosition
  while (start > 0) {
    // 检查是否遇到 hr 边界
    if (crossesHrBoundary(start, hrBoundaries)) {
      break
    }
    // 检查是否是英语字符
    if (!ENGLISH_CHARS.test(fullText[start - 1])) {
      break
    }
    start--
  }

  // 向后扫描：从点击位置向后查找，直到遇到非英语字符或结尾
  let end = clickPosition
  while (end < fullText.length) {
    // 检查是否遇到 hr 边界
    if (crossesHrBoundary(end, hrBoundaries)) {
      break
    }
    // 检查是否是英语字符
    if (!ENGLISH_CHARS.test(fullText[end])) {
      break
    }
    end++
  }

  // 提取短语并清理
  let phrase = fullText.slice(start, end).trim()

  // 移除开头和结尾的标点符号
  phrase = phrase.replace(/^[.,!?;:'"\(\)\[\]\{\}]+/, '')
  phrase = phrase.replace(/[.,!?;:'"\(\)\[\]\{\}]+$/, '')

  return phrase
}

/**
 * 获取节点在容器中的绝对位置
 */
function getAbsolutePosition(container, node, offset) {
  let position = 0

  // 遍历所有子节点
  const walker = document.createTreeWalker(
    container,
    NodeFilter.SHOW_TEXT,
    null,
    false
  )

  let currentNode
  while ((currentNode = walker.nextNode())) {
    if (currentNode === node) {
      return position + offset
    }
    position += currentNode.textContent.length
  }

  // 如果没找到精确节点，尝试使用选择器API
  try {
    const selection = window.getSelection()
    if (selection.rangeCount > 0) {
      const range = selection.getRangeAt(0)
      const preCaretRange = range.cloneRange()
      preCaretRange.selectNodeContents(container)
      preCaretRange.setEnd(range.startContainer, range.startOffset)
      return preCaretRange.toString().length
    }
  } catch (e) {
    // 忽略错误
  }

  return 0
}

/**
 * 检查文本是否主要为英语
 *
 * @param {string} text - 要检查的文本
 * @returns {boolean} 是否主要为英语
 */
export function isEnglishText(text) {
  if (!text || text.length === 0) {
    return false
  }

  // 统计英语字母数量（只计算字母，忽略标点）
  const englishChars = (text.match(/[a-zA-Z]/g) || []).length
  const totalNonSpaceChars = text.replace(/\s/g, '').length

  if (totalNonSpaceChars === 0) {
    return false
  }

  // 至少有30%的字符是英语字母，或者有2个以上英语字母
  const ratio = englishChars / totalNonSpaceChars
  const hasEnoughEnglish = englishChars >= 2

  return ratio > 0.3 || hasEnoughEnglish
}

/**
 * 提取点击位置的单词
 *
 * @param {HTMLElement} element - 容器元素
 * @param {number} x - 点击X坐标
 * @param {number} y - 点击Y坐标
 * @returns {string|null} 点击的单词
 */
export function extractWordAtPosition(element, x, y) {
  // 使用 caretRangeFromPoint 获取点击位置
  const range = document.caretRangeFromPoint(x, y)
  if (!range) {
    return null
  }

  const startNode = range.startContainer
  const startOffset = range.startOffset

  // 提取完整短语
  const phrase = extractEnglishPhrase(element, startNode, startOffset)

  // 如果提取到短语，返回其中的第一个单词
  if (phrase) {
    const words = phrase.split(/\s+/)
    return words[0] || null
  }

  return null
}

/**
 * 从文本中提取完整的句子
 * 句子以 . ! ? 或结尾
 *
 * @param {string} text - 完整文本
 * @param {number} position - 点击位置
 * @returns {string} 完整句子
 */
export function extractSentence(text, position) {
  // 句子结束标记
  const sentenceEnders = /[.!?]+/

  // 找到句子开始位置
  let start = position
  while (start > 0) {
    const char = text[start - 1]
    if (sentenceEnders.test(char)) {
      break
    }
    start--
  }

  // 找到句子结束位置
  let end = position
  while (end < text.length) {
    const char = text[end]
    if (sentenceEnders.test(char)) {
      end++
      break
    }
    end++
  }

  return text.slice(start, end).trim()
}
