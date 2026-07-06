export interface Team {
  id: number
  name: string
  fifa_code: string
  confederation: string
  group_label: string | null
  elo_rating: number
  form_index: number | null
}

export interface Paginated<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface Prediction {
  home_team: string
  away_team: string
  home_code: string
  away_code: string
  home_win_prob: number
  draw_prob: number
  away_win_prob: number
  expected_home_goals: number
  expected_away_goals: number
  confidence: number
  model_version: string
  explainability: string
  analyst_summary: string
}

export interface SimulationResult {
  run_uuid: string
  n_simulations: number
  win_probabilities: Record<string, number>
  final_probabilities: Record<string, number>
  semifinal_probabilities: Record<string, number>
  top_5_favorites: [string, number][]
  analyst_summary: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}
