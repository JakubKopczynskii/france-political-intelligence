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
  ai: {
    summary: string | null
    market_relevance: string | null
    sentiment: string | null
    scenario_signals: Record<string, number> | null
  } | null
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
  prior_probability: number | null
  macro_shocks: {
    sovereign_spread_bps: number
    eur_pct: number
    energy_pct: number
  }
}

export type ImpactMethod = 'factor' | 'historical'

export interface EpisodeStockReturn {
  raw_pct: number
  abnormal_pct: number
  beta: number
}

export interface EpisodeMeta {
  id: string
  label: string
  start: string
  end: string
  description: string
  trading_start: string
  trading_end: string
  cac_pct: number | null
  dax_pct: number
  eu_banks_pct: number | null
  index_abnormal_pct: number | null
}

export interface Episode extends EpisodeMeta {
  stocks: Record<string, EpisodeStockReturn>
}

export interface AnalogMeta {
  episodes: Record<string, number>
  episode_labels: Record<string, string>
  scale: number
  confidence: string
  rationale: string
}

export interface Cac40MatrixRow {
  ticker: string
  name: string
  sector: string
  subsector: string | null
  impacts: Record<string, number>
  impacts_historical: Record<string, number>
  impacts_factor?: Record<string, number>
  historical_imputed: boolean
  expected_impact_pct: number
  expected_impact_historical_pct: number | null
  episode_returns: Record<string, EpisodeStockReturn>
  cac_weight: number
  french_revenue_pct: number
  global_revenue_pct: number
  live_price: number | null
}

export interface Cac40Matrix {
  scenarios: Cac40MatrixScenario[]
  companies: Cac40MatrixRow[]
  index_impact: Record<ImpactMethod, Record<string, number>>
  historical_available: boolean
  historical_computed_at: string | null
  analogs: Record<string, AnalogMeta>
  episodes: EpisodeMeta[]
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
  weight: number
}

export interface SentimentSignals {
  probabilities: Record<string, number>
  sources: Record<string, SentimentSource>
  sources_active: string[]
  prior: Record<string, number>
  weights: Record<string, number>
  methodology: string
}

export type Bloc = 'far_right' | 'centre_right' | 'left' | 'other'

export interface PresidentialCandidate {
  key: string
  name: string
  full_name: string
  party: string
  bloc: Bloc
  bloc_label: string
  poll_avg: number
  poll_min: number
  poll_max: number
  hypotheses_tested: number
  hypotheses_share: number
  p_runoff: number
  p_win: number
}

export interface PresidentialMatchup {
  a: string
  b: string
  probability: number
  a_poll_share: number
  estimated: boolean
  a_win_prob: number
}

export interface Mover {
  ticker: string
  name: string
  impact_pct: number
}

export interface Presidential {
  available: boolean
  message?: string
  source_url: string
  computed_at: string
  first_round_date: string
  second_round_date: string
  days_to_first_round: number
  window: { from: string; to: string; n_polls: number; n_hypotheses: number }
  n_first_round_polls_total: number
  n_second_round_polls_total: number
  n_sims: number
  candidates: PresidentialCandidate[]
  matchups: PresidentialMatchup[]
  blocs: Record<Bloc, number>
  bloc_labels: Record<Bloc, string>
  runoff_polls: { a: string; b: string; a_share: number; n: number; latest: string; stale: boolean }[]
  history: { dates: string[]; series: Record<string, (number | null)[]>; names: Record<string, string> }
  assumptions: Record<string, string | number>
  market: {
    bloc_impacts: Record<string, { scenario: string; factor_pct: number | null; historical_pct: number | null }>
    expected_index_pct: Record<ImpactMethod, number | null>
    movers: Record<string, { worst: Mover[]; best: Mover[]; method: ImpactMethod }>
    note: string
  }
}

export interface CalendarEvent {
  date: string
  title: string
  kind: string
  detail: string
}

export interface RiskComponent {
  id: string
  label: string
  unit: string
  description: string
  value: number
  as_of: string
  percentile: number
  reference_value: number | null
  reference_percentile: number | null
  worst_value: number
  worst_date: string
  series: { date: string; value: number }[]
  source: string
}

export interface MarketRisk {
  available: boolean
  message?: string
  computed_at: string
  composite: { score: number; label: string; reference_score: number | null; reference_label: string }
  components: RiskComponent[]
  method: string
  model_comparison: {
    blended_disruptive_probability: number
    presidential_far_right_win: number | null
    presidential_left_win: number | null
    note: string
  }
}

export interface ElectionHistory {
  scenario_snapshots: { date: string; probabilities: Record<string, number>; prior: Record<string, number>; sources_active: string[] }[]
  presidential_snapshots: { date: string; p_win: Record<string, number>; blocs: Record<Bloc, number> }[]
  revisions: { date: string | null; scenario: string; old: number; new: number; source: string; rationale: string | null }[]
  poll_history: Presidential['history'] | null
}

export interface ElectionExposure {
  portfolio_id: number
  portfolio_name: string
  total_value: number
  scenarios: Cac40MatrixScenario[]
  methods: ImpactMethod[]
  summary: Partial<Record<ImpactMethod, {
    scenario_pct: Record<string, number>
    scenario_eur: Record<string, number>
    expected_pct: number
    presidential_expected_pct: number | null
    worst_scenario: string
    top_detractors: { symbol: string; name: string; contribution_pct: number }[]
  }>>
  holdings: {
    symbol: string
    name: string
    sector: string | null
    weight: number
    basis: string
    impacts: Partial<Record<ImpactMethod, Record<string, number | null>>>
    contribution_pct: Partial<Record<ImpactMethod, Record<string, number>>>
  }[]
  presidential_blocs: Partial<Record<Bloc, number>>
  disclaimer: string
}
