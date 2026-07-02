/**
 * phraseExtractor 单元测试
 * 重点覆盖 wrapEnglishPhrases —— span 包裹逻辑
 */
import { describe, it, expect } from 'vitest'
import { wrapEnglishPhrases, isEnglishText, extractEnglishPhrase, extractSentence } from './phraseExtractor'

// ──────────────────────────────────────
//  wrapEnglishPhrases
// ──────────────────────────────────────

describe('wrapEnglishPhrases', () => {
  it('空字符串 / null 返回空字符串', () => {
    expect(wrapEnglishPhrases('')).toBe('')
    expect(wrapEnglishPhrases(null)).toBe('')
    expect(wrapEnglishPhrases(undefined)).toBe('')
  })

  it('纯中文不包裹', () => {
    const input = '<p>你好，欢迎来到英语课堂</p>'
    const result = wrapEnglishPhrases(input)
    expect(result).not.toContain('tts-phrase')
    expect(result).toContain('你好')
  })

  it('单句英语包裹为一个 span', () => {
    const input = '<p>Hello, how are you?</p>'
    const result = wrapEnglishPhrases(input)
    expect(result).toContain('class="tts-phrase"')
    expect(result).toContain('data-phrase="Hello, how are you?"')
  })

  it('多句英语按句子边界切分为多个 span', () => {
    const input = '<p>Hello! How are you? I am fine.</p>'
    const result = wrapEnglishPhrases(input)
    const spans = result.match(/class="tts-phrase"/g)
    expect(spans.length).toBe(3)
    expect(result).toContain('data-phrase="Hello!"')
    expect(result).toContain('data-phrase="How are you?"')
    expect(result).toContain('data-phrase="I am fine."')
  })

  it('中英混合：中文跳过，英文包裹', () => {
    const input = '<p>老师: Hello, welcome! 欢迎来到课堂。</p>'
    const result = wrapEnglishPhrases(input)
    expect(result).toContain('data-phrase="Hello, welcome!"')
    const zhPart = result.slice(result.indexOf('欢迎'))
    expect(zhPart).not.toContain('tts-phrase')
  })

  it('代码块内容不包裹 (pre/code)', () => {
    const input = '<pre><code>console.log("hello world")</code></pre><p>Great job!</p>'
    const result = wrapEnglishPhrases(input)
    const codeBlock = result.slice(0, result.indexOf('</pre>'))
    expect(codeBlock).not.toContain('tts-phrase')
    expect(result).toContain('data-phrase="Great job!"')
  })

  it('行内 code 跳过', () => {
    const input = '<p>Use <code>npm install</code> to start. Then run the app.</p>'
    const result = wrapEnglishPhrases(input)
    const codePart = result.slice(result.indexOf('<code>'), result.indexOf('</code>'))
    expect(codePart).not.toContain('tts-phrase')
  })

  it('小数不触发句子切分，但句尾.后跟空格+大写时切分', () => {
    const input = '<p>The value is 3.14 and pi is about 3.14159. This is amazing.</p>'
    const result = wrapEnglishPhrases(input)
    expect(result).toContain('data-phrase="The value is 3.14 and pi is about 3.14159."')
    expect(result).toContain('data-phrase="This is amazing."')
  })

  it('markdown 渲染后的 HTML 正常包裹（跨 strong/em）', () => {
    const input = '<p>Hello! I\'m <strong>Sarah</strong>, the receptionist.</p><p>How can I <em>help</em> you today?</p>'
    const result = wrapEnglishPhrases(input)
    expect(result).toContain('data-phrase="Hello!"')
    expect(result).toContain('data-phrase="I\'m Sarah, the receptionist."')
    expect(result).toContain('data-phrase="How can I help you today?"')
    expect(result).toContain('<strong>Sarah</strong>')
    expect(result).toContain('<em>help</em>')
  })

  it('emoji 作为边界不包裹在英语中', () => {
    const input = '<p>📢 Tom: Hello, welcome to my shop!</p>'
    const result = wrapEnglishPhrases(input)
    expect(result).toContain('📢')
    expect(result).toContain('data-phrase')
  })

  it('不生成空短语 span', () => {
    const input = '<p>！！！</p>'
    const result = wrapEnglishPhrases(input)
    expect(result).not.toContain('tts-phrase')
  })
})

// ──────────────────────────────────────
//  isEnglishText
// ──────────────────────────────────────

describe('isEnglishText', () => {
  it('纯英文字符串返回 true', () => {
    expect(isEnglishText('Hello world')).toBe(true)
  })

  it('纯中文返回 false', () => {
    expect(isEnglishText('你好世界')).toBe(false)
  })

  it('过短文本需要至少 2 个英文字母', () => {
    expect(isEnglishText('a')).toBe(false)
    expect(isEnglishText('ab')).toBe(true)
  })

  it('空字符串返回 false', () => {
    expect(isEnglishText('')).toBe(false)
    expect(isEnglishText(null)).toBe(false)
  })
})

// ──────────────────────────────────────
//  extractEnglishPhrase （向后兼容）
// ──────────────────────────────────────

describe('extractEnglishPhrase', () => {
  function makeElement(html) {
    const div = document.createElement('div')
    div.innerHTML = html
    return div
  }

  it('从点击文本节点中提取英文短语', () => {
    const el = makeElement('<p>Hello world</p>')
    const textNode = el.querySelector('p').firstChild
    const phrase = extractEnglishPhrase(el, textNode, 6)
    expect(phrase).toBe('Hello world')
  })

  it('遇到中文字符停止扫描', () => {
    const el = makeElement('<p>Hello 你好 world</p>')
    const textNode = el.querySelector('p').firstChild
    const phrase = extractEnglishPhrase(el, textNode, 2)
    expect(phrase).toBe('Hello')
  })
})

// ──────────────────────────────────────
//  extractSentence
// ──────────────────────────────────────

describe('extractSentence', () => {
  it('从文本中间提取所在句子', () => {
    const text = 'Hi there. How are you? I am fine.'
    const pos = text.indexOf('are')
    const sentence = extractSentence(text, pos)
    expect(sentence).toBe('How are you?')
  })

  it('首句提取', () => {
    const text = 'First. Second. Third.'
    expect(extractSentence(text, 2)).toBe('First.')
  })
})
