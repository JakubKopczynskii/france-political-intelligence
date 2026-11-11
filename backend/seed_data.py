import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import Engine
from models import (
    Base, Source, Feed, Article, Event, PoliticalScenario,
    ScenarioAssumption, Company, CompanyExposure, Portfolio,
    Holding, ECBScenario
)
import hashlib
from cac40 import CAC40


SCENARIO_PRIORS = {"centrist": 0.35, "national_rally": 0.25, "left_wing": 0.25, "hung_parliament": 0.15}


def _now():
    return datetime.now(timezone.utc)


def create_tables(engine: Engine):
    Base.metadata.create_all(engine)


def _fp(url: str, title: str) -> str:
    return hashlib.sha256(f"{url}{title}".encode()).hexdigest()


def seed_demo_data(db: Session):
    # --- Sources ---
    sources_data = [
        {"name": "Le Monde", "url": "https://www.lemonde.fr", "source_type": "news", "quality_tier": 1, "language": "fr"},
        {"name": "ECB", "url": "https://www.ecb.europa.eu", "source_type": "institutional", "quality_tier": 1, "language": "en"},
        {"name": "French Government", "url": "https://www.gouvernement.fr", "source_type": "official", "quality_tier": 1, "language": "fr"},
        {"name": "INSEE", "url": "https://www.insee.fr", "source_type": "institutional", "quality_tier": 1, "language": "fr"},
        {"name": "Reuters", "url": "https://www.reuters.com", "source_type": "news", "quality_tier": 1, "language": "en"},
        {"name": "Les Echos", "url": "https://www.lesechos.fr", "source_type": "news", "quality_tier": 1, "language": "fr"},
    ]
    sources = []
    for s in sources_data:
        src = Source(**s)
        db.add(src)
        sources.append(src)
    db.flush()

    # --- Feeds ---
    feed_data = [
        {"source_id": sources[0].id, "feed_url": "https://www.lemonde.fr/rss/une.xml", "topic_tags": json.dumps(["politics", "macro", "france"])},
        {"source_id": sources[1].id, "feed_url": "https://www.ecb.europa.eu/rss/press.html", "topic_tags": json.dumps(["ecb", "macro", "rates"])},
        {"source_id": sources[2].id, "feed_url": "https://www.gouvernement.fr/flux-rss", "topic_tags": json.dumps(["politics", "fiscal", "policy"])},
        {"source_id": sources[4].id, "feed_url": "https://feeds.reuters.com/reuters/businessNews", "topic_tags": json.dumps(["macro", "companies"])},
        {"source_id": sources[5].id, "feed_url": "https://www.lesechos.fr/rss/rss_une.xml", "topic_tags": json.dumps(["macro", "companies", "fiscal"])},
    ]
    feeds = []
    for f in feed_data:
        feed = Feed(**f, health_status="unchecked")
        db.add(feed)
        feeds.append(feed)
    db.flush()

    # --- Political Scenarios ---
    scenarios_data = [
        {
            "name": "centrist",
            "display_name": "Centrist / Pro-European Continuity",
            "description": "A centrist government continues France's pro-European orientation, maintaining reform agenda on labour markets and pensions while pursuing fiscal consolidation within EU frameworks. Business-friendly policies support investment and competitiveness.",
            "political_assumptions": json.dumps({
                "government_type": "Centrist coalition",
                "eu_orientation": "strongly pro-EU",
                "reform_capacity": "moderate",
                "coalition_stability": "medium-high"
            }),
            "policy_assumptions": json.dumps({
                "fiscal": "Gradual deficit reduction towards 3% GDP target. Continued EU fiscal rules compliance.",
                "corporate_tax": "Stable corporate tax rate around 25%, potential targeted incentives for green investment.",
                "labour": "Labour market flexibility reforms maintained. No major reversal of recent pension reforms.",
                "energy": "Nuclear investment program continues. Renewable energy targets maintained.",
                "defence": "NATO commitment upheld. Defence spending at approximately 2% GDP.",
                "trade": "Strong EU single market support. No protectionist measures against EU partners.",
                "eu_relations": "Active role in EU decision-making. Support for EU capital markets union."
            }),
            "implementation_feasibility": "medium",
            "feasibility_evidence": "Requires maintaining parliamentary coalition. Historical centrist governments have faced challenges on structural reforms.",
            "time_horizon": "2 to 5 years",
            "economic_channels": json.dumps([
                "Stable sovereign spread environment (OAT-Bund ~50-80bps)",
                "Moderate corporate tax stability",
                "Continued EU structural funds access",
                "Stable EUR/USD assumption"
            ]),
            "sector_sensitivities": json.dumps({
                "Financials": "Neutral to mildly positive: stable sovereign risk",
                "Industrials": "Positive: continued investment programs",
                "Energy": "Positive: nuclear program continuity",
                "Consumer": "Neutral: moderate wage growth",
                "Real Estate": "Mildly negative: ongoing rate normalisation"
            }),
            "fiscal_considerations": "Target: deficit below 3% GDP. Debt stabilization required. EU fiscal rules compliance essential.",
            "sources": json.dumps(["Illustrative scenario — not a prediction", "Based on published centrist party platforms"]),
            "invalidating_assumptions": json.dumps([
                "Loss of parliamentary majority",
                "Severe recession requiring large fiscal stimulus",
                "EU institutional crisis",
                "Energy price shock"
            ]),
            "probability": 0.35,
            "probability_label": "Illustrative analyst input — not a forecast",
        },
        {
            "name": "national_rally",
            "display_name": "National Rally-Led Government",
            "description": "A National Rally-led government implements its published programme including immigration restrictions, energy price controls, VAT reductions on fuel and energy, and targeted spending increases. EU relations become more transactional.",
            "political_assumptions": json.dumps({
                "government_type": "NR-led majority or coalition",
                "eu_orientation": "eurosceptic but not exit",
                "reform_capacity": "medium — requires parliamentary majority",
                "coalition_stability": "uncertain"
            }),
            "policy_assumptions": json.dumps({
                "fiscal": "Increased public spending on energy price controls and social measures. Higher deficit risk. Tension with EU fiscal rules.",
                "corporate_tax": "Potential changes to windfall profit taxes on energy sector. Some corporate tax adjustments possible.",
                "labour": "Protection of purchasing power focus. Potential reversal of pension reform elements.",
                "energy": "Energy price controls for households. Nuclear maintained. Increased state intervention.",
                "defence": "Potential NATO relationship adjustment. Bilateral approach preferred.",
                "trade": "Protectionist preferences, especially on agriculture. Prioritise French producers.",
                "eu_relations": "Transactional EU relationship. Opposition to deeper integration. Budget contribution scrutiny."
            }),
            "implementation_feasibility": "low",
            "feasibility_evidence": "Many NR proposals face EU treaty constraints, constitutional council review, and parliamentary arithmetic challenges. Based on published 2024 NR programme.",
            "time_horizon": "1 to 3 years",
            "economic_channels": json.dumps([
                "Sovereign spread widening (OAT-Bund potentially +100-200bps under stress)",
                "EUR weakness on EU uncertainty",
                "Higher borrowing costs for corporates and state",
                "Energy sector intervention risk"
            ]),
            "sector_sensitivities": json.dumps({
                "Financials": "Negative: higher sovereign risk, potential regulatory changes",
                "Energy": "Mixed: price controls negative for margins, state support positive",
                "Consumer": "Short-term positive from price controls, medium-term uncertain",
                "Industrials": "Negative: higher financing costs",
                "Real Estate": "Negative: wider spreads, higher rates"
            }),
            "fiscal_considerations": "High deficit risk. EU excessive deficit procedure likely. Sovereign spread sensitivity elevated.",
            "sources": json.dumps([
                "Illustrative scenario — not a prediction",
                "NR 2024 election programme (published, attributable)",
                "Independent fiscal analysis of NR proposals"
            ]),
            "invalidating_assumptions": json.dumps([
                "Failure to win majority",
                "Constitutional court blocking key measures",
                "Market pressure forcing policy reversal",
                "EU fiscal enforcement action"
            ]),
            "probability": 0.25,
            "probability_label": "Illustrative analyst input — not a forecast",
        },
        {
            "name": "left_wing",
            "display_name": "Left-Wing Coalition (NFP/NUPES-style)",
            "description": "A left-wing coalition government pursues higher minimum wage, wealth taxes, public investment in green transition, reversal of pension reforms, and expansion of public services. Significant tension with EU fiscal framework.",
            "political_assumptions": json.dumps({
                "government_type": "NFP-style left coalition",
                "eu_orientation": "pro-EU on social agenda, critical on fiscal rules",
                "reform_capacity": "medium — internal coalition tensions possible",
                "coalition_stability": "uncertain — diverse coalition"
            }),
            "policy_assumptions": json.dumps({
                "fiscal": "Large public investment program. Reversal of pension reforms increases spending. Wealth taxes and higher corporate levies as offset. Likely EU fiscal rule breach.",
                "corporate_tax": "Higher corporate taxation, especially for large companies and financial sector. Windfall profit taxes extended.",
                "labour": "Minimum wage increase to EUR 1,600/month (illustrative). Pension reform reversal. Expanded public sector employment.",
                "energy": "Accelerated renewable transition. State-led green investment. Critique of nuclear expansion beyond existing program.",
                "defence": "NATO commitment maintained but defence spending priorities debated.",
                "trade": "Support for EU-level social standards in trade agreements. Critical of some free trade agreements.",
                "eu_relations": "Active on social and green agenda. Critical of current EU fiscal rules framework."
            }),
            "implementation_feasibility": "low",
            "feasibility_evidence": "Internal coalition disagreements historically challenging. EU fiscal rules create hard constraints. Constitutional and parliamentary arithmetic limits. Based on NFP 2024 published programme.",
            "time_horizon": "1 to 3 years",
            "economic_channels": json.dumps([
                "Corporate profitability pressure from higher taxes",
                "Sovereign spread widening on fiscal concerns",
                "Potential EUR impact",
                "Labour cost increases for domestically-exposed companies"
            ]),
            "sector_sensitivities": json.dumps({
                "Financials": "Negative: higher taxation, sovereign risk",
                "Consumer": "Mixed: wage growth positive for domestics, margin pressure",
                "Energy": "Mixed: green transition positive for renewables, uncertainty on nuclear",
                "Industrials": "Negative: higher labour costs, taxes",
                "Healthcare": "Mildly negative: pricing pressure"
            }),
            "fiscal_considerations": "Structural deficit likely to increase. EU excessive deficit procedure probable. High debt sustainability risk in adverse scenario.",
            "sources": json.dumps([
                "Illustrative scenario — not a prediction",
                "NFP 2024 election programme (published)",
                "Independent fiscal costing of NFP proposals"
            ]),
            "invalidating_assumptions": json.dumps([
                "Coalition breakdown",
                "Market pressure forcing austerity",
                "Constitutional barriers to key measures",
                "EU fiscal enforcement"
            ]),
            "probability": 0.25,
            "probability_label": "Illustrative analyst input — not a forecast",
        },
        {
            "name": "hung_parliament",
            "display_name": "Hung Parliament / Political Deadlock",
            "description": "No stable majority can govern. A minority or technical government operates with limited legislative capacity. Major reforms blocked. Policy paralysis with elevated political risk premium.",
            "political_assumptions": json.dumps({
                "government_type": "Minority/technical government",
                "eu_orientation": "default continuation of existing EU positions",
                "reform_capacity": "very low",
                "coalition_stability": "very low — confidence votes, potential snap elections"
            }),
            "policy_assumptions": json.dumps({
                "fiscal": "Budget passage extremely difficult. Risk of government shutdown or continuing resolutions. Deficit may drift higher by default.",
                "corporate_tax": "Likely status quo — no majority for reform in either direction.",
                "labour": "Legislative paralysis. Existing rules continue.",
                "energy": "Continuity by default. No new major legislation.",
                "defence": "Continuity.",
                "trade": "EU-level decisions continue. No new bilateral trade measures.",
                "eu_relations": "French voice in EU negotiations weakened by domestic instability."
            }),
            "implementation_feasibility": "high",
            "feasibility_evidence": "Hung parliament scenario has occurred in France historically. 2024 legislative elections produced fragmented assembly.",
            "time_horizon": "6 to 18 months — likely snap elections",
            "economic_channels": json.dumps([
                "Political risk premium on French assets",
                "Sovereign spread widening (uncertainty premium)",
                "Investment delays from policy uncertainty",
                "EUR mildly weaker on political instability"
            ]),
            "sector_sensitivities": json.dumps({
                "Financials": "Negative: elevated sovereign risk premium",
                "Real Estate": "Negative: uncertainty on planning and rates",
                "Consumer": "Mildly negative: confidence impact",
                "Industrials": "Mildly negative: investment delays",
                "Defensive": "Relative outperformance expected"
            }),
            "fiscal_considerations": "Deficit drift likely without active budget management. Rating agency scrutiny elevated.",
            "sources": json.dumps([
                "Illustrative scenario — not a prediction",
                "Historical French parliamentary fragmentation precedents",
                "2024 French legislative election outcomes"
            ]),
            "invalidating_assumptions": json.dumps([
                "Unexpected coalition formation",
                "Presidential dissolution of parliament",
                "External shock forcing cross-party consensus"
            ]),
            "probability": 0.15,
            "probability_label": "Illustrative analyst input — not a forecast",
        },
    ]

    scenarios = []
    for s in scenarios_data:
        scenario = PoliticalScenario(**s, prior_probability=s["probability"], last_updated=_now())
        db.add(scenario)
        scenarios.append(scenario)
    db.flush()

    # --- Scenario Assumptions ---
    assumptions_data = [
        # Centrist
        {"scenario_id": scenarios[0].id, "category": "fiscal", "assumption_text": "France maintains deficit reduction path targeting below 3% GDP within 3 years.", "information_type": "assumption", "source_name": "Illustrative", "confidence": "medium"},
        {"scenario_id": scenarios[0].id, "category": "eu", "assumption_text": "France complies with EU fiscal rules framework and participates actively in EU governance.", "information_type": "assumption", "source_name": "Illustrative", "confidence": "medium"},
        {"scenario_id": scenarios[0].id, "category": "energy", "assumption_text": "New nuclear build programme (Flamanville successors) proceeds per government plan.", "information_type": "assumption", "source_name": "French Government energy plan (published)", "confidence": "medium"},
        # NR
        {"scenario_id": scenarios[1].id, "category": "fiscal", "assumption_text": "Energy price controls for households cost estimated 10-15bn EUR annually (illustrative).", "information_type": "assumption", "source_name": "Independent fiscal estimate — illustrative", "confidence": "low"},
        {"scenario_id": scenarios[1].id, "category": "eu", "assumption_text": "France-EU relationship becomes transactional, slowing EU capital markets union.", "information_type": "assumption", "source_name": "Illustrative", "confidence": "low"},
        # Left
        {"scenario_id": scenarios[2].id, "category": "labour", "assumption_text": "Minimum wage increase to EUR 1,600/month adds approximately 15-20bn EUR to wage costs (illustrative).", "information_type": "assumption", "source_name": "Illustrative — based on published NFP proposals", "confidence": "low"},
        {"scenario_id": scenarios[2].id, "category": "fiscal", "assumption_text": "Pension reform reversal increases annual pension spending by approximately 12bn EUR (illustrative estimate).", "information_type": "assumption", "source_name": "Illustrative", "confidence": "low"},
        # Hung
        {"scenario_id": scenarios[3].id, "category": "fiscal", "assumption_text": "Without budget majority, deficit could drift to 5-6% GDP within 2 years by default.", "information_type": "assumption", "source_name": "Illustrative", "confidence": "low"},
    ]
    for a in assumptions_data:
        db.add(ScenarioAssumption(**a))
    db.flush()

    # --- Companies (CAC 40 constituents as of 2024) ---
    cac40_data = [
        {
            "ticker": c["ticker"], "isin": c["isin"], "name": c["name"], "sector": c["sector"],
            "subsector": c["subsector"], "french_revenue_pct": c["french_pct"],
            "european_revenue_pct": c["euro_pct"], "global_revenue_pct": c["global_pct"],
            "revenue_source": "Approximate split from 2023 annual reports",
        }
        for c in CAC40
    ]

    companies = []
    for c in cac40_data:
        company = Company(
            **c,
            listing_currency="EUR",
            index_member="CAC40",
            is_synthetic_exposure=True,
            data_as_of=_now(),
        )
        db.add(company)
        companies.append(company)
    db.flush()

    # --- Illustrative synthetic company exposures ---
    # A few example exposures clearly labelled synthetic
    exposure_examples = [
        {"company_ticker": "BNP.PA", "shock_type": "sovereign_spread", "sensitivity_coefficient": -0.015, "confidence": "low", "rationale": "Banks exposed to French sovereign via OAT holdings and funding costs. SYNTHETIC ILLUSTRATIVE."},
        {"company_ticker": "GLE.PA", "shock_type": "sovereign_spread", "sensitivity_coefficient": -0.015, "confidence": "low", "rationale": "Banks exposed to French sovereign. SYNTHETIC ILLUSTRATIVE."},
        {"company_ticker": "ACA.PA", "shock_type": "sovereign_spread", "sensitivity_coefficient": -0.012, "confidence": "low", "rationale": "Banks exposed to French sovereign. SYNTHETIC ILLUSTRATIVE."},
        {"company_ticker": "TTE.PA", "shock_type": "energy", "sensitivity_coefficient": 0.8, "confidence": "low", "rationale": "Integrated oil & gas benefits from higher energy prices. SYNTHETIC ILLUSTRATIVE."},
        {"company_ticker": "ENGI.PA", "shock_type": "energy", "sensitivity_coefficient": 0.3, "confidence": "low", "rationale": "Utility has mixed energy exposure. SYNTHETIC ILLUSTRATIVE."},
        {"company_ticker": "AIR.PA", "shock_type": "eur", "sensitivity_coefficient": 0.4, "confidence": "low", "rationale": "Aerospace exporter benefits from weaker EUR. SYNTHETIC ILLUSTRATIVE."},
        {"company_ticker": "SAF.PA", "shock_type": "eur", "sensitivity_coefficient": 0.4, "confidence": "low", "rationale": "Aerospace/defence exporter. SYNTHETIC ILLUSTRATIVE."},
        {"company_ticker": "URW.PA", "shock_type": "ecb_rate", "sensitivity_coefficient": -0.02, "confidence": "low", "rationale": "Real estate REIT highly sensitive to rate changes. SYNTHETIC ILLUSTRATIVE."},
    ]
    ticker_to_company = {c.ticker: c for c in companies}
    for e in exposure_examples:
        ticker = e.pop("company_ticker")
        company = ticker_to_company.get(ticker)
        if company:
            exp = CompanyExposure(company_id=company.id, is_synthetic=True, source="Illustrative synthetic assumption — not actual research", **e)
            db.add(exp)
    db.flush()

    # --- Demo Portfolio ---
    portfolio = Portfolio(
        name="Demo Portfolio (SYNTHETIC)",
        is_demo=True,
        total_value=1_000_000.0,
        currency="EUR",
        source="demo",
    )
    db.add(portfolio)
    db.flush()

    holdings_data = [
        {"symbol": "MC.PA", "company_name": "LVMH", "quantity": 150.0, "market_value": 200000.0, "weight": 0.20, "sector": "Consumer Discretionary"},
        {"symbol": "TTE.PA", "company_name": "TotalEnergies", "quantity": 2000.0, "market_value": 120000.0, "weight": 0.12, "sector": "Energy"},
        {"symbol": "AIR.PA", "company_name": "Airbus", "quantity": 500.0, "market_value": 90000.0, "weight": 0.09, "sector": "Industrials"},
        {"symbol": "SAN.PA", "company_name": "Sanofi", "quantity": 1000.0, "market_value": 90000.0, "weight": 0.09, "sector": "Healthcare"},
        {"symbol": "BNP.PA", "company_name": "BNP Paribas", "quantity": 1500.0, "market_value": 80000.0, "weight": 0.08, "sector": "Financials"},
        {"symbol": "OR.PA", "company_name": "L'Oréal", "quantity": 200.0, "market_value": 70000.0, "weight": 0.07, "sector": "Consumer Staples"},
        {"symbol": "SU.PA", "company_name": "Schneider Electric", "quantity": 400.0, "market_value": 70000.0, "weight": 0.07, "sector": "Industrials"},
    ]
    # Note: weights above sum to 0.72. Add cash to make 1.0
    holdings_data.append({"symbol": "CASH", "company_name": "Cash (EUR)", "quantity": None, "market_value": 280000.0, "weight": 0.28, "sector": None, "asset_type": "cash"})

    for h in holdings_data:
        asset_type = h.pop("asset_type", "equity")
        holding = Holding(portfolio_id=portfolio.id, currency="EUR", asset_type=asset_type, **h)
        db.add(holding)
    db.flush()

    # --- ECB Scenarios ---
    ecb_scenarios = [
        {
            "profile_name": "continuity",
            "description": "ECB leadership and policy remain on current trajectory: gradual normalisation, data-dependence, 2% inflation target. Policy rate changes driven by inflation/growth data, not political considerations.",
            "policy_rate_delta_bps": 0.0,
            "eur_impact_pct": 0.0,
            "oat_bund_spread_delta_bps": 0.0,
            "bank_margin_impact_pct": 0.0,
            "is_verified_fact": False,
            "sources": json.dumps(["Hypothetical profile — illustrative only. ECB independence means actual decisions depend on data."]),
        },
        {
            "profile_name": "hawkish",
            "description": "New ECB leadership with relatively more hawkish stance: higher rates for longer, stricter inflation target adherence, potentially slower QE reinvestment unwinding stops sooner.",
            "policy_rate_delta_bps": 50.0,
            "eur_impact_pct": 1.5,
            "oat_bund_spread_delta_bps": 15.0,
            "bank_margin_impact_pct": 0.5,
            "is_verified_fact": False,
            "sources": json.dumps(["Hypothetical profile — illustrative only. No specific successor candidate implied."]),
        },
        {
            "profile_name": "dovish",
            "description": "New ECB leadership with relatively more dovish stance: quicker rate cuts, more accommodative monetary conditions, greater tolerance for above-target inflation during transition.",
            "policy_rate_delta_bps": -50.0,
            "eur_impact_pct": -1.5,
            "oat_bund_spread_delta_bps": -10.0,
            "bank_margin_impact_pct": -0.5,
            "is_verified_fact": False,
            "sources": json.dumps(["Hypothetical profile — illustrative only. No specific successor candidate implied."]),
        },
        {
            "profile_name": "institutional_uncertainty",
            "description": "Prolonged leadership transition creates institutional uncertainty. Policy direction unclear. Market risk premium increases until new leadership establishes credibility.",
            "policy_rate_delta_bps": 0.0,
            "eur_impact_pct": -1.0,
            "oat_bund_spread_delta_bps": 25.0,
            "bank_margin_impact_pct": -0.3,
            "is_verified_fact": False,
            "sources": json.dumps(["Hypothetical profile — illustrative only."]),
        },
    ]
    for es in ecb_scenarios:
        db.add(ECBScenario(**es, last_updated=_now()))
    db.flush()

    # --- Synthetic Articles & Events ---
    articles_seed = [
        {
            "title": "[SYNTHETIC DEMO] France announces 2025 budget with 4.4% deficit target",
            "url": "https://demo.example.com/article/1",
            "content_snippet": "SYNTHETIC DEMO DATA. The French government presented its 2025 budget with a deficit target of 4.4% of GDP, citing slower growth and higher defence spending. This is illustrative demo content.",
            "published_at": datetime(2024, 9, 15, 10, 0, tzinfo=timezone.utc),
            "language": "en",
            "topic_tags": json.dumps(["fiscal", "macro", "politics"]),
            "entities": json.dumps(["French Government", "Ministère de l'Économie"]),
            "policy_tags": json.dumps(["budget", "deficit", "fiscal_policy"]),
            "affected_sectors": json.dumps(["Financials", "Utilities", "Industrials"]),
            "affected_companies": json.dumps([]),
            "relevance_score": 0.9,
            "source_quality": 1,
            "is_synthetic": True,
        },
        {
            "title": "[SYNTHETIC DEMO] ECB holds rates at 3.4%, signals data-dependent path",
            "url": "https://demo.example.com/article/2",
            "content_snippet": "SYNTHETIC DEMO DATA. The ECB Governing Council voted to hold the deposit facility rate at 3.4%. President Lagarde reiterated the data-dependent approach to future decisions.",
            "published_at": datetime(2024, 10, 17, 14, 0, tzinfo=timezone.utc),
            "language": "en",
            "topic_tags": json.dumps(["ecb", "macro", "rates"]),
            "entities": json.dumps(["ECB", "Christine Lagarde"]),
            "policy_tags": json.dumps(["interest_rates", "monetary_policy"]),
            "affected_sectors": json.dumps(["Financials", "Real Estate", "Utilities"]),
            "affected_companies": json.dumps([]),
            "relevance_score": 0.95,
            "source_quality": 1,
            "is_synthetic": True,
        },
        {
            "title": "[SYNTHETIC DEMO] French political parties present competing economic visions",
            "url": "https://demo.example.com/article/3",
            "content_snippet": "SYNTHETIC DEMO DATA. French political parties have outlined their economic programmes ahead of potential elections, with significant differences on fiscal policy, taxation, and EU relations.",
            "published_at": datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc),
            "language": "en",
            "topic_tags": json.dumps(["politics", "fiscal", "macro"]),
            "entities": json.dumps(["Assemblée Nationale", "French political parties"]),
            "policy_tags": json.dumps(["election", "fiscal_policy", "taxation"]),
            "affected_sectors": json.dumps(["Financials", "Energy", "Consumer"]),
            "affected_companies": json.dumps([]),
            "relevance_score": 0.85,
            "source_quality": 2,
            "is_synthetic": True,
        },
        {
            "title": "[SYNTHETIC DEMO] TotalEnergies Q3 results beat estimates",
            "url": "https://demo.example.com/article/4",
            "content_snippet": "SYNTHETIC DEMO DATA. TotalEnergies reported Q3 earnings above analyst estimates, citing strong LNG trading results. Capital allocation unchanged.",
            "published_at": datetime(2024, 10, 25, 7, 30, tzinfo=timezone.utc),
            "language": "en",
            "topic_tags": json.dumps(["companies", "energy"]),
            "entities": json.dumps(["TotalEnergies"]),
            "policy_tags": json.dumps(["energy_regulation", "corporate_results"]),
            "affected_sectors": json.dumps(["Energy"]),
            "affected_companies": json.dumps(["TTE.PA"]),
            "relevance_score": 0.7,
            "source_quality": 2,
            "is_synthetic": True,
        },
        {
            "title": "[SYNTHETIC DEMO] France sovereign rating under review — illustrative scenario",
            "url": "https://demo.example.com/article/5",
            "content_snippet": "SYNTHETIC DEMO DATA. Illustrative scenario: French sovereign credit outlook placed on review following budget concerns and political fragmentation. OAT spreads widen.",
            "published_at": datetime(2024, 11, 5, 16, 0, tzinfo=timezone.utc),
            "language": "en",
            "topic_tags": json.dumps(["fiscal", "macro", "politics"]),
            "entities": json.dumps(["French Government", "Agence France Trésor"]),
            "policy_tags": json.dumps(["sovereign_risk", "deficit", "fiscal_policy"]),
            "affected_sectors": json.dumps(["Financials", "Real Estate"]),
            "affected_companies": json.dumps(["BNP.PA", "GLE.PA", "ACA.PA"]),
            "relevance_score": 0.95,
            "source_quality": 1,
            "is_synthetic": True,
        },
    ]

    # Use feed_id from first feed
    articles = []
    for a in articles_seed:
        fp = _fp(a["url"], a["title"])
        article = Article(
            feed_id=feeds[0].id,
            fingerprint=fp,
            retrieved_at=_now(),
            **a,
        )
        db.add(article)
        articles.append(article)
    db.flush()

    # --- Events ---
    event1 = Event(
        headline="[SYNTHETIC DEMO] France 2025 Budget: 4.4% Deficit Target",
        description="The French government announced its 2025 budget with a 4.4% GDP deficit target, raising fiscal sustainability concerns. SYNTHETIC DEMO DATA.",
        event_category="fiscal",
        political_actors=json.dumps(["French Government", "Ministère de l'Économie"]),
        policy_tags=json.dumps(["budget", "deficit", "fiscal_policy"]),
        affected_sectors=json.dumps(["Financials", "Utilities", "Industrials"]),
        affected_companies=json.dumps([]),
        verification_status="reported",
        information_type="reported_claim",
        source_article_ids=json.dumps([articles[0].id]),
        novelty_score=0.8,
        time_horizon="short_term",
        uncertainties="Parliamentary approval uncertain. Final figures subject to revision.",
        is_synthetic=True,
    )
    db.add(event1)

    event2 = Event(
        headline="[SYNTHETIC DEMO] French Political Fragmentation: Fiscal Risk Scenario",
        description="Political fragmentation increases fiscal risk premium on French assets. OAT-Bund spreads widening in stress scenario. SYNTHETIC DEMO DATA.",
        event_category="politics",
        political_actors=json.dumps(["Assemblée Nationale", "Multiple political parties"]),
        policy_tags=json.dumps(["election", "sovereign_risk", "fiscal_policy"]),
        affected_sectors=json.dumps(["Financials", "Real Estate", "Energy"]),
        affected_companies=json.dumps(["BNP.PA", "GLE.PA", "ACA.PA"]),
        verification_status="unverified",
        information_type="scenario",
        source_article_ids=json.dumps([articles[2].id, articles[4].id]),
        novelty_score=0.9,
        time_horizon="medium_term",
        uncertainties="Scenario outcome highly uncertain. Election timing unknown.",
        is_synthetic=True,
    )
    db.add(event2)
    db.flush()

    db.commit()
    print("Demo data seeded successfully.")


def reset_demo_data(db: Session):
    """Delete all data and re-seed demo data."""
    # Delete in reverse dependency order
    from models import (
        AIAnalysis, StressTestResult, StressTest, Holding, Portfolio,
        CompanyExposure, Company, ScenarioAssumption, PoliticalScenario,
        ECBScenario, Event, Article, Feed, Source, Forecast
    )
    for model in [AIAnalysis, StressTestResult, StressTest, Holding, Portfolio,
                  CompanyExposure, Company, ScenarioAssumption, PoliticalScenario,
                  ECBScenario, Event, Article, Feed, Source, Forecast]:
        db.query(model).delete()
    db.commit()
    seed_demo_data(db)
