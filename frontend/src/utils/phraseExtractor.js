/**
 * 英语短语提取工具
 * 从点击位置提取完整的英语短语或句子
 * 以及将渲染后的 HTML 中的英语句子包裹为可点击的 span
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

  return ratio >= 0.3 && hasEnoughEnglish
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

// ──────────────────────────────────────
//  span-wrapping: 将 HTML 中的英语句子包裹为可点击 span
// ──────────────────────────────────────

/**
 * 跳过内容——这些元素内的文本不做包裹
 */
const SKIP_TAGS = new Set(['PRE', 'CODE', 'SCRIPT', 'STYLE', 'AUDIO', 'VIDEO'])

/**
 * 块级元素——以块为单位做短语识别（跨行内标记如 <strong> <em>）
 */
const BLOCK_TAGS = new Set(['P', 'LI', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
  'TD', 'TH', 'BLOCKQUOTE', 'DIV', 'SECTION', 'ARTICLE'])

/**
 * 句子结束判定：`. ` `! ` `? ` 后跟空格+大写、或结尾、或非英语字符
 * 但排除小数（前后均为数字的 `.`）
 */
function isSentenceEnd(text, dotIndex) {
  const ch = text[dotIndex]
  if (ch !== '.' && ch !== '!' && ch !== '?') return false

  // 小数点检查：前为数字 且 后也为数字 → 不是句子结束
  const prev = dotIndex > 0 ? text[dotIndex - 1] : ''
  const next = dotIndex + 1 < text.length ? text[dotIndex + 1] : ''
  if (ch === '.' && /\d/.test(prev) && /\d/.test(next)) return false

  // 结尾 → 句子结束
  if (dotIndex + 1 >= text.length) return true

  // 后跟空白 → 句子结束
  if (/\s/.test(next)) return true

  // 后跟大写字母或带重音的大写 → 句子结束
  if (/[A-ZÀ-ɏ]/.test(next)) return true

  // 后跟非英语字符 → 句子结束
  if (!ENGLISH_CHARS.test(next)) return true

  return false
}

/**
 * 在英文段落内部按句子边界切分
 */
function splitEnglishRun(text) {
  const segments = []
  let buf = ''
  const len = text.length

  for (let i = 0; i < len; i++) {
    const ch = text[i]
    buf += ch
    if (isSentenceEnd(text, i)) {
      segments.push(buf)
      buf = ''
      // 跳过句子间的一个空白字符
      const next = i + 1 < len ? text[i + 1] : ''
      if (/\s/.test(next)) {
        i++
      }
    }
  }

  if (buf.trim()) segments.push(buf)

  return segments.length > 1 ? segments : [text]
}

/**
 * 清理短语——去除首尾标点/空白，但保留句子结束标记 (.!?)
 */
function cleanPhrase(text) {
  let cleaned = text.trim()
  // 去除前导标点（: , ; 等，但不包括 .!?）
  cleaned = cleaned.replace(/^[：:;,，。、\s]+/, '')
  // 去除尾部空白
  cleaned = cleaned.trim()
  return cleaned
}

/**
 * 收集一个块元素内所有文本节点（跳过 SKIP_TAGS 内部 和 已包裹的 .tts-phrase 内部）
 */
function collectTextNodes(block) {
  const nodes = []
  const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT)
  let node
  while ((node = walker.nextNode())) {
    let ancestor = node.parentNode
    let skip = false
    while (ancestor && ancestor !== block) {
      const tag = ancestor.nodeName
      if (SKIP_TAGS.has(tag)) { skip = true; break }
      if (tag === 'SPAN' && ancestor.classList.contains('tts-phrase')) { skip = true; break }
      ancestor = ancestor.parentNode
    }
    if (!skip) nodes.push(node)
  }
  return nodes
}

/**
 * 拼接文本节点为完整字符串
 */
function concatTextNodes(textNodes) {
  return textNodes.map(n => n.textContent).join('')
}

/**
 * 在拼接文本中找出第一个英语短语
 */
function findFirstPhrase(fullText) {
  let cursor = 0
  const len = fullText.length

  while (cursor < len) {
    while (cursor < len && !ENGLISH_CHARS.test(fullText[cursor])) cursor++
    if (cursor >= len) break

    const enStart = cursor
    while (cursor < len && ENGLISH_CHARS.test(fullText[cursor])) cursor++
    const englishRun = fullText.slice(enStart, cursor)

    const sentences = splitEnglishRun(englishRun)
    let runOffset = enStart
    for (const sentence of sentences) {
      const clean = cleanPhrase(sentence)
      if (!clean || !isEnglishText(clean)) {
        runOffset += sentence.length
        continue
      }
      const phraseStart = fullText.indexOf(clean, runOffset)
      if (phraseStart === -1) { runOffset += sentence.length; continue }
      const phraseEnd = phraseStart + clean.length
      return { start: phraseStart, end: phraseEnd, text: clean }
    }
  }
  return null
}

/**
 * 在文本节点序列中定位一段文本并包裹为 <span class="tts-phrase">
 */
function wrapPhraseInNodes(textNodes, phrase) {
  const nodeSpans = []
  let position = 0
  for (const node of textNodes) {
    const len = node.textContent.length
    nodeSpans.push({ node, start: position, end: position + len })
    position += len
  }

  const affectedNodes = []
  for (const ns of nodeSpans) {
    if (ns.end <= phrase.start) continue
    if (ns.start >= phrase.end) break

    const overlapStart = Math.max(ns.start, phrase.start)
    const overlapEnd = Math.min(ns.end, phrase.end)
    affectedNodes.push({
      node: ns.node,
      offsetInNode: overlapStart - ns.start,
      lengthInNode: overlapEnd - overlapStart
    })
  }

  if (affectedNodes.length === 0) return

  // 单节点短语（最常见）
  if (affectedNodes.length === 1) {
    const { node, offsetInNode, lengthInNode } = affectedNodes[0]

    if (offsetInNode > 0) {
      node.splitText(offsetInNode)
    }
    const targetNode = offsetInNode > 0 ? node.nextSibling : node
    if (!targetNode) return

    if (lengthInNode < targetNode.textContent.length) {
      targetNode.splitText(lengthInNode)
    }

    const span = document.createElement('span')
    span.className = 'tts-phrase'
    span.setAttribute('data-phrase', phrase.text)
    const parent = targetNode.parentNode
    if (parent) {
      parent.replaceChild(span, targetNode)
      span.appendChild(targetNode)
    }
    return
  }

  // 多节点短语（跨 <strong>/<em> 等行内标记）
  const first = affectedNodes[0]
  if (first.offsetInNode > 0 && first.offsetInNode < first.node.textContent.length) {
    first.node.splitText(first.offsetInNode)
    first.node = first.node.nextSibling
  }

  const last = affectedNodes[affectedNodes.length - 1]
  const lastCut = last.offsetInNode + last.lengthInNode
  if (lastCut < last.node.textContent.length) {
    last.node.splitText(lastCut)
  }

  const nodesToWrap = []
  let current = first.node
  while (current && current !== last.node.nextSibling) {
    nodesToWrap.push(current)
    current = current.nextSibling
  }

  const span = document.createElement('span')
  span.className = 'tts-phrase'
  span.setAttribute('data-phrase', phrase.text)

  const insertParent = nodesToWrap[0].parentNode
  if (insertParent) {
    insertParent.insertBefore(span, nodesToWrap[0])
    for (const n of nodesToWrap) {
      span.appendChild(n)
    }
  }
}

/**
 * 按块级元素处理：逐短语包裹，每次包裹后重新收集文本节点
 */
function processBlock(block) {
  for (let iter = 0; iter < 200; iter++) {
    const textNodes = collectTextNodes(block)
    if (textNodes.length === 0) break

    const fullText = concatTextNodes(textNodes)
    const phrase = findFirstPhrase(fullText)
    if (!phrase) break

    wrapPhraseInNodes(textNodes, phrase)
  }
}

/**
 * 递归遍历 DOM，对每个块级元素做短语包裹
 */
function walkAndWrap(node) {
  if (node.nodeType !== Node.ELEMENT_NODE) return

  const tag = node.nodeName
  if (SKIP_TAGS.has(tag)) return

  if (BLOCK_TAGS.has(tag)) {
    processBlock(node)
    return
  }

  const children = Array.from(node.childNodes)
  for (const child of children) {
    walkAndWrap(child)
  }
}

/**
 * 将已渲染的 HTML 字符串中的英语句子包裹为可点击的
 * `<span class="tts-phrase" data-phrase="...">`
 *
 * 在 markdown → HTML 之后、v-html 之前调用。
 *
 * @param {string} htmlString - 已渲染的 HTML
 * @returns {string} 包裹后的 HTML
 */
export function wrapEnglishPhrases(htmlString) {
  if (!htmlString || typeof htmlString !== 'string') return ''

  const parser = new DOMParser()
  const doc = parser.parseFromString(htmlString, 'text/html')
  const body = doc.body

  walkAndWrap(body)

  return body.innerHTML
}
