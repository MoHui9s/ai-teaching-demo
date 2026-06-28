import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';

hljs.configure({
  languages: ['python', 'javascript', 'typescript', 'java', 'cpp', 'bash', 'json', 'markdown'],
  ignoreUnescapedHTML: true,
});

marked.setOptions({
  highlight: (code, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value;
    }
    return hljs.highlightAuto(code).value;
  },
  breaks: true,
  gfm: true,
});

export function renderMarkdown(text) {
  const html = marked.parse(text);
  const cleanHtml = DOMPurify.sanitize(html);
  return cleanHtml;
}

export function renderCodeBlock(content) {
  const container = document.createElement('div');
  container.innerHTML = renderMarkdown(content);

  container.querySelectorAll('pre > code').forEach((codeBlock) => {
    const pre = codeBlock.parentElement;
    const header = document.createElement('div');
    header.className = 'code-header';

    const lang = codeBlock.className.match(/language-(\w+)/)?.[1] || 'text';
    const langLabel = document.createElement('span');
    langLabel.textContent = lang;
    header.appendChild(langLabel);

    const copyBtn = document.createElement('button');
    copyBtn.textContent = '📋 Copy';
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(codeBlock.textContent).then(() => {
        copyBtn.textContent = '✓ Copied';
        setTimeout(() => {
          copyBtn.textContent = '📋 Copy';
        }, 2000);
      });
    });
    header.appendChild(copyBtn);

    pre.insertBefore(header, codeBlock);
  });

  return container.innerHTML;
}