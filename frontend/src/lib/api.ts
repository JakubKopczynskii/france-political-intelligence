import type {
  Article,
  Cac40Matrix,
  Company,
  ECBScenario,
  Event,
  HealthResponse,
  MethodologyInfo,
  Portfolio,
  Scenario,
  SentimentSignals,
  ShockInputs,
  StressTestResult,
} from './types'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') p.set(k, String(v))
  }
  const s = p.toString()
  return s ? `?${s}` : ''
}

export const api = {
  health: () => req<HealthResponse>('/api/health'),

  getNews: (params?: { topic?: string; search?: string; limit?: number; offset?: number }) =>
    req<{ articles: Article[] }>(`/api/news${qs(params ?? {})}`).then(r => r.articles),

  getEvents: (params?: { limit?: number }) =>
    req<{ events: Event[] }>(`/api/events${qs(params ?? {})}`).then(r => r.events),

  refreshFeeds: () =>
    req<{ message: string; articles_added: number }>('/api/feeds/refresh', { method: 'POST' }),

  getScenarios: () =>
    req<{ scenarios: Scenario[] }>('/api/scenarios').then(r => r.scenarios),

  getScenario: (id: number) => req<Scenario>(`/api/scenarios/${id}`),

  updateScenarioProbability: (id: number, probability: number) =>
    req<Scenario>(`/api/scenarios/${id}/probability`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ probability }),
    }),

  getCompanies: (params?: { sector?: string; search?: string }) =>
    req<{ companies: Company[] }>(`/api/companies${qs(params ?? {})}`).then(r => r.companies),

  getCompany: (ticker: string) => req<Company>(`/api/companies/${ticker}`),

  getDemoPortfolio: () => req<Portfolio>('/api/portfolio/demo'),

  getPortfolio: (id: number) => req<Portfolio>(`/api/portfolio/${id}`),

  importPortfolio: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return req<Portfolio>('/api/portfolio/import', { method: 'POST', body: form })
  },

  deletePortfolioData: (id: number) =>
    req<{ message: string }>(`/api/portfolio/${id}`, { method: 'DELETE' }),

  runStressTest: (body: { portfolio_id: number; shocks: ShockInputs; methodology?: string }) =>
    req<StressTestResult>('/api/stress-tests/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  getECBScenarios: () =>
    req<{ scenarios: ECBScenario[] }>('/api/ecb').then(r => r.scenarios),

  getMethodology: () => req<MethodologyInfo>('/api/methodology'),

  getCac40Matrix: () => req<Cac40Matrix>('/api/analysis/cac40-matrix'),

  getSentimentSignals: () => req<SentimentSignals>('/api/analysis/sentiment'),
}
