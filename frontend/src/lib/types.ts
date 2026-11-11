export interface HealthResponse {
  status: string
  version: string
  db_ok: boolean
  timestamp: string
  mode: string
  demo_mode: boolean
  article_count: number
  event_count: number
  last_refresh: string | null
}

export interface Scenario {
  id: number
  name: string
  display_name: string
  description: string
  probability: number
  probability_label: string
  political_assumptions: Record<string, string>
  policy_assumptions: Record<string, string>
  implementation_feasibility: string
  time_horizon: string
  sector_sensitivities: Record<string, number>
  fiscal_considerations: string
  invalidating_assumptions: string[]
  last_updated: string
  sources: string[]
}

export interface Article {
  id: number
  title: string
  url: string
  content_snippet: string
  published_at: string | null
  retrieved_at: string
  language: string
  source_name: string
  source_quality: number
  relevance_score: number
  importance_label: 'HIGH' | 'MEDIUM' | 'LOW'
  image_url: string | null
  topic_tags: string[]
  entities: string[]
  policy_tags: string[]
  affected_sectors: string[]
  affected_companies: string[]
  is_duplicate: boolean
  is_synthetic: boolean
  information_type: string
  event_id: number | null
}

export interface Event {
  id: number
  headline: string
  description: string
  event_category: string
  political_actors: string[]
  policy_tags: string[]
  affected_sectors: string[]
  source_name: string
  source_url: string
  published_at: string | null
  verification_status: string
  novelty_score: number
  time_horizon: string
  is_synthetic: boolean
}

export interface Company {
  id: number
  ticker: string
  name: string
  sector: string
  subsector: string | null
  isin: string | null
  listing_currency: string
  index_member: string | null
  french_revenue_pct: number | null
  european_revenue_pct: number | null
  global_revenue_pct: number | null
  revenue_source: string | null
  is_synthetic_exposure: boolean
  data_as_of: string | null
  data_quality_note: string | null
}

export interface Holding {
  symbol: string
  company_name: string
  quantity: number | null
  market_value: number
  weight: number
  currency: string
  sector: string | null
  asset_type: string
}

export interface Portfolio {
  id: number
  name: string
  is_demo: boolean
  total_value: number
  currency: string
  holdings: Holding[]
  created_at: string
}

export interface ShockInputs {
  sovereign_spread: number
  eur: number
  ecb_rate: number
  energy: number
}

export interface HoldingContribution {
  symbol: string
  pnl_pct: number
  pnl_eur: number
  sector: string
  weight: number
}

export interface SectorContribution {
  sector: string
  pnl_pct: number
  pnl_eur: number
}

export interface StressTestResult {
  test_id: number
  portfolio_id: number
  portfolio_name: string
  portfolio_pnl_pct: number
  portfolio_pnl_eur: number
  holding_contributions: HoldingContribution[]
  sector_contributions: SectorContribution[]
  shocks_applied: ShockInputs
  methodology: string
  best_holding: string
  worst_holding: string
  disclaimer: string
}

export interface ECBScenario {
  id: number
  profile_name: string
  description: string
  policy_rate_delta_bps: number
  eur_impact_pct: number
  oat_bund_spread_delta_bps: number
  bank_margin_impact_pct: number
  is_verified_fact: boolean
  sources: string[]
  last_updated: string
  disclaimer: string
}

export interface MethodologyInfo {
  version: string
  methodology_name: string
  data_cutoff: string
  timestamp: string
  ai_provider: string | null
  model: string | null
  data_summary: Record<string, unknown>
  information_types: Array<{ type: string; description: string }>
  evidence_hierarchy: string[]
  scenario_methodology: Record<string, unknown>
  financial_methodology: Record<string, unknown>
  model_warnings: string[]
  limitations: string[]
}

export interface Cac40MatrixScenario {
  slug: string
  display_name: string
  probability: number | null
  macro_shocks: {
    sovereign_spread_bps: number
    eur_pct: number
    ecb_rate_bps: number
    energy_pct: number
  }
}

export interface Cac40MatrixRow {
  ticker: string
  name: string
  sector: string
  subsector: string | null
  impacts: Record<string, number>
  expected_impact_pct: number
  cac_weight: number
  french_revenue_pct: number
  global_revenue_pct: number
  live_price: number | null
}

export interface Cac40Matrix {
  scenarios: Cac40MatrixScenario[]
  companies: Cac40MatrixRow[]
  methodology: string
  disclaimer: string
}

export type InformationType =
  | 'verified_fact'
  | 'reported_claim'
  | 'model_interpretation'
  | 'assumption'
  | 'scenario'
  | 'forecast'

export interface SentimentSource {
  available: boolean
  signal: Record<string, number>
}

export interface SentimentSignals {
  probabilities: Record<string, number>
  sources: Record<string, SentimentSource>
  sources_active: string[]
  prior: Record<string, number>
  methodology: string
}
