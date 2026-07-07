import type { ReactNode } from 'react'

/**
 * Minimal, dependency-free renderer for the subset of markdown the analyst
 * emits: **bold**, `## headings`, `-`/`*` bullets, `1.` numbered lists, and
 * paragraphs. Everything is built as React nodes (never innerHTML), so
 * untrusted LLM output is safe by construction.
 */

function inline(text: string, keyBase: string): ReactNode[] {
  const parts = text.split(/\*\*([^*]+)\*\*/g)
  return parts.map((part, i) =>
    i % 2 === 1 ? <strong key={`${keyBase}-${i}`}>{part}</strong> : part,
  )
}

export default function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let list: { ordered: boolean; items: string[] } | null = null
  let key = 0

  const flushList = () => {
    if (!list) return
    const items = list.items.map((item, i) => (
      <li key={i} className="ml-4 list-outside" style={{ listStyleType: list!.ordered ? 'decimal' : 'disc' }}>
        {inline(item, `li-${key}-${i}`)}
      </li>
    ))
    blocks.push(list.ordered ? <ol key={key++}>{items}</ol> : <ul key={key++}>{items}</ul>)
    list = null
  }

  for (const raw of text.split('\n')) {
    const line = raw.trimEnd()
    const bullet = line.match(/^\s*[-*]\s+(.*)/)
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)/)
    const heading = line.match(/^(#{1,4})\s+(.*)/)

    if (bullet || numbered) {
      const ordered = Boolean(numbered)
      const item = (bullet ?? numbered)![1]
      if (list && list.ordered !== ordered) flushList()
      list ??= { ordered, items: [] }
      list.items.push(item)
      continue
    }
    flushList()

    if (heading) {
      blocks.push(
        <p key={key++} className="font-semibold" style={{ color: 'var(--ink)' }}>
          {inline(heading[2], `h-${key}`)}
        </p>,
      )
    } else if (line.trim() === '') {
      blocks.push(<div key={key++} className="h-2" />)
    } else {
      blocks.push(<p key={key++}>{inline(line, `p-${key}`)}</p>)
    }
  }
  flushList()

  return <div className="space-y-0.5">{blocks}</div>
}
