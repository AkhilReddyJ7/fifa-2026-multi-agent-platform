import type { Prediction, SimulationResult, Team } from '../types'

const BASE = '/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body.slice(0, 300)}`)
  }
  return res.json() as Promise<T>
}

// One fetch shared by every view; teams don't change within a session.
let teamsCache: Promise<{ items: Team[]; total: number }> | null = null

export function listTeams(): Promise<{ items: Team[]; total: number }> {
  teamsCache ??= request<{ items: Team[]; total: number }>('/teams?page_size=100').catch(
    (err) => {
      teamsCache = null // allow retry after a failed load
      throw err
    },
  )
  return teamsCache
}

export function predictMatch(home: string, away: string, stage: string): Promise<Prediction> {
  return request('/predictions', {
    method: 'POST',
    body: JSON.stringify({ home_team: home, away_team: away, stage }),
  })
}

export function runSimulation(nSimulations: number, seed?: number): Promise<SimulationResult> {
  return request('/simulation', {
    method: 'POST',
    body: JSON.stringify({ n_simulations: nSimulations, seed: seed ?? null }),
  })
}

/** Invert the backend's chunk encoding: `\\` then `\n` were escaped, in that order. */
function unescapeChunk(data: string): string {
  return data.replace(/\\(n|\\)/g, (_, c: string) => (c === 'n' ? '\n' : '\\'))
}

/**
 * Stream the analyst's chat response over SSE. The backend emits
 * `[AGENT:<name>]` events as each pipeline agent finishes, then the analyst's
 * text chunks (backslashes and newlines escaped) between `[START]`/`[DONE]`.
 */
export async function streamChat(
  message: string,
  onChunk: (text: string) => void,
  onAgent?: (agent: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
    signal,
  })
  if (!res.ok || !res.body) throw new Error(`chat stream failed: ${res.status}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE events are separated by a blank line
    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''
    for (const event of events) {
      for (const line of event.split('\n')) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6)
        if (data === '[START]' || data === '[DONE]') continue
        const agent = data.match(/^\[AGENT:([\w-]+)\]$/)
        if (agent) {
          onAgent?.(agent[1])
          continue
        }
        onChunk(unescapeChunk(data))
      }
    }
  }
}
