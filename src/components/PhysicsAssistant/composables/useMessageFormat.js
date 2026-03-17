/**
 * 消息格式化 Composable
 * 处理Markdown和LaTeX渲染
 */

import { onMounted } from 'vue'
import MarkdownIt from 'markdown-it'
import 'katex/dist/katex.min.css'

export function useMessageFormat() {
  let md = null
  let katex = null
  
  // 初始化Markdown和KaTeX
  onMounted(async () => {
    md = new MarkdownIt({
      html: false,
      linkify: true,
      typographer: true,
      breaks: true,
    })
    
    try {
      katex = (await import('katex')).default
    } catch (error) {
      console.warn('KaTeX加载失败，LaTeX公式将不会渲染', error)
    }
  })
  
  // 将 MathML 转换为可读的 LaTeX 格式
  const convertMathMLToLatex = (text) => {
    if (!text.includes('<math')) {
      return text
    }
    
    console.log('检测到 MathML 格式，正在转换为 LaTeX...')
    
    // 使用正则表达式提取 MathML 块
    return text.replace(/<math[^>]*>([\s\S]*?)<\/math>/g, (match, content) => {
      try {
        // 简单的 MathML 到 LaTeX 转换
        let latex = content
          // 移除 XML 标签，只保留内容
          .replace(/<semantics>.*?<\/semantics>/g, '')
          .replace(/<mrow>/g, '{')
          .replace(/<\/mrow>/g, '}')
          .replace(/<mi>([^<]+)<\/mi>/g, '$1')
          .replace(/<mn>([^<]+)<\/mn>/g, '$1')
          .replace(/<mo>([^<]+)<\/mo>/g, '$1')
          .replace(/<mfrac><mrow>([^<]*)<\/mrow><mrow>([^<]*)<\/mrow><\/mfrac>/g, '\\frac{$1}{$2}')
          .replace(/<mfrac>([^<]*)<\/mfrac>/g, '\\frac{$1}')
          .replace(/<msqrt>([^<]*)<\/msqrt>/g, '\\sqrt{$1}')
          .replace(/<msup><mrow>([^<]*)<\/mrow><mrow>([^<]*)<\/mrow><\/msup>/g, '{$1}^{$2}')
          .replace(/<msub><mrow>([^<]*)<\/mrow><mrow>([^<]*)<\/mrow><\/msub>/g, '{$1}_{$2}')
          .replace(/<annotation[^>]*>.*?<\/annotation>/g, '')
          .replace(/<[^>]*>/g, ' ')
          .replace(/\s+/g, ' ')
          .trim()
        
        // 根据 display 属性决定是行内还是块级公式
        if (match.includes('display="block"')) {
          return `$$${latex}$$`
        } else {
          return `$${latex}$`
        }
      } catch (e) {
        console.error('MathML 转换失败:', e)
        // 如果转换失败，至少提取纯文本
        return content.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
      }
    })
  }
  
  // 清理嵌套的 HTML/MathML div 标签
  const cleanMathDivs = (text) => {
    // 移除多余的 math-block 和 katex 包装
    return text
      .replace(/<div class="math-block">(\s*)<span class="katex-display">[\s\S]*?<\/span>(\s*)<\/div>/g, (match) => {
        // 提取 MathML 部分
        const mathMatch = match.match(/<math[^>]*>[\s\S]*?<\/math>/)
        if (mathMatch) {
          return convertMathMLToLatex(mathMatch[0])
        }
        return match
      })
      .replace(/<span class="katex">[\s\S]*?<\/span>/g, (match) => {
        const mathMatch = match.match(/<math[^>]*>[\s\S]*?<\/math>/)
        if (mathMatch) {
          return convertMathMLToLatex(mathMatch[0])
        }
        return match
      })
  }
  
  // 渲染消息内容
  const renderContent = (content) => {
    if (!content) return ''
    if (!md) return content
    
    try {
      // 先转换 MathML 为 LaTeX
      let processed = convertMathMLToLatex(content)
      
      // 清理多余的 HTML div 包装
      processed = cleanMathDivs(processed)
      
      // 保存公式，用占位符替换（避免 Markdown 破坏公式）
      const mathPlaceholders = []
      let placeholderIndex = 0
      
      // 保护块级公式 $$...$$
      processed = processed.replace(/\$\$([\s\S]+?)\$\$/g, (match, formula) => {
        const placeholder = `MATHBLOCK${placeholderIndex}PLACEHOLDER`
        mathPlaceholders.push({
          placeholder,
          formula: formula.trim(),
          isBlock: true
        })
        placeholderIndex++
        return `\n\n${placeholder}\n\n`  // 添加换行确保作为独立块
      })
      
      // 保护行内公式 $...$
      processed = processed.replace(/\$([^\$\n]+?)\$/g, (match, formula) => {
        const placeholder = `MATHINLINE${placeholderIndex}PLACEHOLDER`
        mathPlaceholders.push({
          placeholder,
          formula: formula.trim(),
          isBlock: false
        })
        placeholderIndex++
        return placeholder
      })
      
      // 用 Markdown 渲染（此时公式已被占位符保护）
      processed = md.render(processed)
      
      // 恢复公式并用 KaTeX 渲染
      if (katex) {
        mathPlaceholders.forEach(({ placeholder, formula, isBlock }) => {
          try {
            const rendered = katex.renderToString(formula, {
              displayMode: isBlock,
              throwOnError: false
            })
            if (isBlock) {
              // 使用正则表达式匹配，处理可能的 HTML 包裹
              const regex = new RegExp(`<p>\\s*${placeholder}\\s*</p>|${placeholder}`, 'g')
              processed = processed.replace(
                regex,
                `<div class="math-block">${rendered}</div>`
              )
            } else {
              // 行内公式可能被包裹在各种标签中
              const regex = new RegExp(placeholder, 'g')
              processed = processed.replace(
                regex,
                `<span class="math-inline">${rendered}</span>`
              )
            }
          } catch (e) {
            console.error('KaTeX 渲染失败:', e, formula)
            const regex = new RegExp(placeholder, 'g')
            processed = processed.replace(
              regex,
              `<span class="math-error">${formula}</span>`
            )
          }
        })
      } else {
        // 如果 KaTeX 未加载，至少显示原始公式
        mathPlaceholders.forEach(({ placeholder, formula, isBlock }) => {
          const regex = new RegExp(placeholder, 'g')
          if (isBlock) {
            processed = processed.replace(regex, `$$${formula}$$`)
          } else {
            processed = processed.replace(regex, `$${formula}$`)
          }
        })
      }
      
      return processed
    } catch (error) {
      console.error('内容渲染失败:', error)
      return content
    }
  }
  
  // 获取纯文本（用于复制等）
  const getPlainText = (content) => {
    if (!content) return ''
    return content
      .replace(/\$\$([\s\S]+?)\$\$/g, '$1')
      .replace(/\$([^\$\n]+?)\$/g, '$1')
      .replace(/[*_~`#]/g, '')
  }
  
  return {
    renderContent,
    getPlainText,
  }
}

