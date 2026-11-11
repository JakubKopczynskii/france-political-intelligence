from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base


def _now():
    return datetime.now(timezone.utc)


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(512), nullable=False)
    source_type = Column(String(50), nullable=False)  # "official", "news", "institutional"
    quality_tier = Column(Integer, default=3)  # 1-5
    language = Column(String(10), default="fr")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)

    feeds = relationship("Feed", back_populates="source")


class Feed(Base):
    __tablename__ = "feeds"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    feed_url = Column(String(512), nullable=False)
    topic_tags = Column(Text, default="[]")  # JSON list
    last_fetched_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    article_count = Column(Integer, default=0)
    health_status = Column(String(50), default="unknown")
    created_at = Column(DateTime, default=_now)

    source = relationship("Source", back_populates="feeds")
    articles = relationship("Article", back_populates="feed")


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_article_fingerprint"),
    )

    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, ForeignKey("feeds.id"), nullable=True)
    title = Column(Text, nullable=False)
    url = Column(String(1024), unique=True, nullable=False)
    content_snippet = Column(Text, default="")
    published_at = Column(DateTime, nullable=True)
    retrieved_at = Column(DateTime, default=_now)
    language = Column(String(10), default="fr")
    fingerprint = Column(String(64), nullable=False, index=True, unique=True)
    topic_tags = Column(Text, default="[]")  # JSON list
    entities = Column(Text, default="[]")  # JSON list
    policy_tags = Column(Text, default="[]")  # JSON list
    affected_sectors = Column(Text, default="[]")  # JSON list
    affected_companies = Column(Text, default="[]")  # JSON list
    image_url = Column(String(1024), nullable=True)
    relevance_score = Column(Float, default=0.0)
    source_quality = Column(Integer, default=3)
    is_duplicate = Column(Boolean, default=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    is_synthetic = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)

    feed = relationship("Feed", back_populates="articles")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    headline = Column(Text, nullable=False)
    description = Column(Text, default="")
    event_category = Column(String(100), nullable=False)
    political_actors = Column(Text, default="[]")  # JSON list
    policy_tags = Column(Text, default="[]")  # JSON list
    affected_sectors = Column(Text, default="[]")  # JSON list
    affected_companies = Column(Text, default="[]")  # JSON list
    verification_status = Column(String(50), default="unverified")
    information_type = Column(String(100), default="reported_claim")
    source_article_ids = Column(Text, default="[]")  # JSON list
    novelty_score = Column(Float, default=0.5)
    time_horizon = Column(String(50), default="medium_term")
    uncertainties = Column(Text, default="")
    is_synthetic = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)


class PoliticalScenario(Base):
    __tablename__ = "political_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    political_assumptions = Column(Text, default="{}")  # JSON
    policy_assumptions = Column(Text, default="{}")  # JSON
    implementation_feasibility = Column(String(50), default="unknown")
    feasibility_evidence = Column(Text, default="")
    time_horizon = Column(String(100), default="medium_term")
    economic_channels = Column(Text, default="[]")  # JSON list
    sector_sensitivities = Column(Text, default="{}")  # JSON
    fiscal_considerations = Column(Text, default="")
    sources = Column(Text, default="[]")  # JSON list
    invalidating_assumptions = Column(Text, default="[]")  # JSON list
    probability = Column(Float, default=0.25)
    probability_label = Column(String(255), default="illustrative analyst input")
    prior_probability = Column(Float, nullable=True)  # fixed analyst prior; never overwritten by signal blending
    last_updated = Column(DateTime, default=_now)
    created_at = Column(DateTime, default=_now)

    assumptions = relationship("ScenarioAssumption", back_populates="scenario")
    probability_revisions = relationship("ProbabilityRevision", back_populates="scenario", order_by="ProbabilityRevision.revised_at.desc()")


class ScenarioAssumption(Base):
    __tablename__ = "scenario_assumptions"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("political_scenarios.id"), nullable=False)
    category = Column(String(100), nullable=False)
    assumption_text = Column(Text, nullable=False)
    information_type = Column(String(100), default="assumption")
    source_url = Column(String(512), default="")
    source_name = Column(String(255), default="")
    confidence = Column(String(20), default="medium")
    is_editable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)

    scenario = relationship("PoliticalScenario", back_populates="assumptions")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, nullable=False)
    isin = Column(String(20), nullable=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100), nullable=False)
    subsector = Column(String(100), default="")
    listing_currency = Column(String(10), default="EUR")
    index_member = Column(String(50), default="CAC40")
    index_since = Column(DateTime, nullable=True)
    french_revenue_pct = Column(Float, nullable=True)
    european_revenue_pct = Column(Float, nullable=True)
    global_revenue_pct = Column(Float, nullable=True)
    revenue_source = Column(String(255), nullable=True)
    is_synthetic_exposure = Column(Boolean, default=False)
    data_as_of = Column(DateTime, nullable=True)
    data_quality_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)

    exposures = relationship("CompanyExposure", back_populates="company")


class CompanyExposure(Base):
    __tablename__ = "company_exposures"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    scenario_id = Column(Integer, ForeignKey("political_scenarios.id"), nullable=True)
    shock_type = Column(String(100), nullable=False)
    sensitivity_coefficient = Column(Float, nullable=False)
    confidence = Column(String(20), default="low")
    source = Column(String(255), default="illustrative synthetic assumption")
    is_synthetic = Column(Boolean, default=True)
    rationale = Column(Text, default="")
    created_at = Column(DateTime, default=_now)

    company = relationship("Company", back_populates="exposures")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    is_demo = Column(Boolean, default=True)
    total_value = Column(Float, default=0.0)
    currency = Column(String(10), default="EUR")
    source = Column(String(50), default="demo")
    created_at = Column(DateTime, default=_now)

    holdings = relationship("Holding", back_populates="portfolio")
    stress_tests = relationship("StressTest", back_populates="portfolio")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    company_name = Column(String(255), default="")
    quantity = Column(Float, nullable=True)
    market_value = Column(Float, nullable=False)
    weight = Column(Float, nullable=False)
    currency = Column(String(10), default="EUR")
    asset_type = Column(String(50), default="equity")
    sector = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_now)

    portfolio = relationship("Portfolio", back_populates="holdings")


class StressTest(Base):
    __tablename__ = "stress_tests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    scenario_id = Column(Integer, ForeignKey("political_scenarios.id"), nullable=True)
    shocks = Column(Text, default="{}")  # JSON dict
    methodology = Column(String(50), default="deterministic")
    mc_seed = Column(Integer, nullable=True)
    mc_paths = Column(Integer, nullable=True)
    mc_horizon_days = Column(Integer, nullable=True)
    run_at = Column(DateTime, default=_now)
    created_at = Column(DateTime, default=_now)

    portfolio = relationship("Portfolio", back_populates="stress_tests")
    result = relationship("StressTestResult", back_populates="stress_test", uselist=False)


class StressTestResult(Base):
    __tablename__ = "stress_test_results"

    id = Column(Integer, primary_key=True, index=True)
    stress_test_id = Column(Integer, ForeignKey("stress_tests.id"), nullable=False)
    portfolio_pnl_pct = Column(Float, nullable=False)
    portfolio_pnl_eur = Column(Float, nullable=False)
    best_scenario_name = Column(String(255), nullable=True)
    worst_scenario_name = Column(String(255), nullable=True)
    holding_contributions = Column(Text, default="[]")  # JSON list
    sector_contributions = Column(Text, default="[]")  # JSON list
    var_95 = Column(Float, nullable=True)
    expected_shortfall_95 = Column(Float, nullable=True)
    mc_percentiles = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, default=_now)

    stress_test = relationship("StressTest", back_populates="result")


class ECBScenario(Base):
    __tablename__ = "ecb_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    profile_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    policy_rate_delta_bps = Column(Float, default=0.0)
    eur_impact_pct = Column(Float, default=0.0)
    oat_bund_spread_delta_bps = Column(Float, default=0.0)
    bank_margin_impact_pct = Column(Float, default=0.0)
    is_verified_fact = Column(Boolean, default=False)
    sources = Column(Text, default="[]")  # JSON list
    last_updated = Column(DateTime, default=_now)
    created_at = Column(DateTime, default=_now)


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=_now)
    information_cutoff = Column(DateTime, nullable=True)
    target_description = Column(Text, nullable=False)
    horizon = Column(String(100), nullable=False)
    methodology = Column(String(255), nullable=False)
    model_version = Column(String(100), default="0.1.0")
    inputs_summary = Column(Text, default="")
    predicted_value = Column(Float, nullable=True)
    predicted_range_low = Column(Float, nullable=True)
    predicted_range_high = Column(Float, nullable=True)
    realized_outcome = Column(Float, nullable=True)
    evaluation_date = Column(DateTime, nullable=True)


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    provider = Column(String(50), default="none")
    model_name = Column(String(255), default="none")
    prompt_version = Column(String(50), default="0.1.0")
    information_cutoff = Column(DateTime, nullable=True)
    facts_extracted = Column(Text, default="[]")  # JSON
    interpretations = Column(Text, default="[]")  # JSON
    uncertainties = Column(Text, default="")
    human_review_required = Column(Boolean, default=False)
    raw_response = Column(Text, default="")
    is_valid = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)


class DataFetchLog(Base):
    """Tracks when each data type was last successfully fetched. Used for same-day skip on restart."""
    __tablename__ = "data_fetch_log"

    id = Column(Integer, primary_key=True)
    fetch_type = Column(String(100), nullable=False, index=True)  # "rss_feeds" | "market_prices" | "polymarket_probs"
    fetched_date = Column(String(10), nullable=False)  # ISO date YYYY-MM-DD
    record_count = Column(Integer, default=0)
    status = Column(String(20), default="ok")  # "ok" | "error" | "partial"
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PriceCache(Base):
    """Daily closing prices fetched from Yahoo Finance (yfinance). No API key required."""
    __tablename__ = "price_cache"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=True)
    currency = Column(String(10), default="EUR")
    price_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    source = Column(String(50), default="yfinance")


class ProbabilityRevision(Base):
    """Audit log for every change to a scenario's probability."""
    __tablename__ = "probability_revision"

    id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, ForeignKey("political_scenarios.id"), nullable=False)
    old_probability = Column(Float, nullable=False)
    new_probability = Column(Float, nullable=False)
    source = Column(String(50), nullable=False)  # "analyst" | "polymarket" | "import"
    source_detail = Column(Text, nullable=True)
    rationale = Column(Text, nullable=True)
    revised_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    scenario = relationship("PoliticalScenario", back_populates="probability_revisions")


class DataCache(Base):
    """JSON results of expensive fetch/compute jobs (polls, historical episodes, market risk)."""
    __tablename__ = "data_cache"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    payload = Column(Text, nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ProbabilitySnapshot(Base):
    """One row per day per kind ("scenarios" | "presidential") for history charts."""
    __tablename__ = "probability_snapshot"

    id = Column(Integer, primary_key=True)
    kind = Column(String(30), nullable=False, index=True)
    snapshot_date = Column(String(10), nullable=False, index=True)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
