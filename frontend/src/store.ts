import { create } from 'zustand'
import { streamChat } from './lib/api'
import type { ChatMessage } from './types'

interface ChatStore {
  messages: ChatMessage[]
  streaming: boolean
  error: string | null
  send: (text: string) => Promise<void>
  clear: () => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  streaming: false,
  error: null,

  send: async (text: string) => {
    if (get().streaming || !text.trim()) return
    set((s) => ({
      messages: [...s.messages, { role: 'user', content: text }, { role: 'assistant', content: '' }],
      streaming: true,
      error: null,
    }))
    try {
      await streamChat(text, (chunk) => {
        set((s) => {
          const messages = [...s.messages]
          const last = messages[messages.length - 1]
          messages[messages.length - 1] = { ...last, content: last.content + chunk }
          return { messages }
        })
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err) })
    } finally {
      set({ streaming: false })
    }
  },

  clear: () => set({ messages: [], error: null }),
}))
