import { useEffect, useRef, useState } from 'react'
import { useChatStore } from '../store'
import Markdown from './Markdown'
import { ErrorNote } from './ui'

const AGENT_LABELS: Record<string, string> = {
  orchestrator: 'Routing',
  stats: 'Stats',
  prediction_agent: 'Prediction',
  simulation: 'Simulation',
  research: 'Research',
}

const SUGGESTIONS = [
  'Predict BRA vs ARG',
  'Who are the title favorites?',
  'Analyze GER strengths and weaknesses',
  'ESP vs FRA head to head history',
]

export default function Chat() {
  const { messages, streaming, agents, error, send } = useChatStore()
  const [draft, setDraft] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages])

  const submit = () => {
    const text = draft.trim()
    if (!text || streaming) return
    setDraft('')
    void send(text)
  }

  return (
    <div className="card flex h-[70vh] flex-col">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-5">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-sm" style={{ color: 'var(--ink-2)' }}>
              Ask the analyst about teams, match-ups, or tournament odds.
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => void send(s)}
                  className="card px-3 py-1.5 text-xs hover:opacity-80"
                  style={{ color: 'var(--ink-2)' }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div
              className="max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed"
              style={
                m.role === 'user'
                  ? { background: 'var(--series-1)', color: '#ffffff' }
                  : { background: 'var(--neutral-mid)', color: 'var(--ink)' }
              }
            >
              {m.role === 'assistant' ? (
                m.content ? (
                  <Markdown text={m.content} />
                ) : streaming && i === messages.length - 1 ? (
                  '…'
                ) : (
                  ''
                )
              ) : (
                <span className="whitespace-pre-wrap">{m.content}</span>
              )}
            </div>
          </div>
        ))}
        {streaming && agents.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 text-xs" style={{ color: 'var(--ink-muted)' }}>
            {agents.map((a) => (
              <span key={a} className="card px-2 py-0.5">
                {AGENT_LABELS[a] ?? a} ✓
              </span>
            ))}
            <span className="card px-2 py-0.5">Analyst …</span>
          </div>
        )}
        {error && <ErrorNote message={error} />}
      </div>

      <div className="flex gap-2 border-t p-4" style={{ borderColor: 'var(--grid)' }}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.nativeEvent.isComposing && submit()}
          placeholder="Ask about FIFA 2026…"
          className="card flex-1 px-3 py-2 text-sm outline-none"
          disabled={streaming}
        />
        <button
          onClick={submit}
          disabled={streaming || !draft.trim()}
          className="rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          style={{ background: 'var(--series-1)' }}
        >
          {streaming ? 'Streaming…' : 'Send'}
        </button>
      </div>
    </div>
  )
}
