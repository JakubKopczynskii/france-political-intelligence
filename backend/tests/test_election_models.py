from datetime import date

import pytest

from cac40 import CAC40, TICKERS
from services import presidential as P
from services.historical import ANALOGS, analog_impacts
from services.probability_engine import blend, poll_signal_from_presidential
from services.sentiment_fetcher import _keyword_score

POLL_HTML = """
<html><body>
<h2>Sondages concernant le premier tour</h2>
<h3>Année 2026</h3>
<table class="wikitable">
<tr><th rowspan="3">Sondeur</th><th rowspan="3">Date</th><th rowspan="3">Échantillon</th><th></th><th></th><th></th><th rowspan="2">Autres</th></tr>
<tr><th><a href="/wiki/A" title="Jean-Luc Mélenchon">Mélenchon</a> (LFI)</th>
    <th><a href="/wiki/B" title="Édouard Philippe">Philippe</a> (HOR)</th>
    <th><a href="/wiki/C" title="Marine Le Pen">Le Pen</a> (RN)</th></tr>
<tr><td></td><td></td><td></td><td></td></tr>
<tr><td rowspan="2">Ifop</td><td rowspan="2">9-10 novembre</td><td rowspan="2">1 000</td><td>18</td><td>16</td><td>33</td><td>—</td></tr>
<tr><td>19</td><td>—</td><td>35</td><td>—</td></tr>
<tr><td>Elabe</td><td>29 octobre-2 novembre</td><td>1 500</td><td>17,5</td><td>15</td><td>34</td><td>—</td></tr>
</table>
<h2>Sondages concernant le second tour</h2>
<h4>Hypothèse Philippe – Le Pen</h4>
<table class="wikitable">
<tr><th rowspan="3">Sondeur</th><th rowspan="3">Dates</th><th rowspan="3">Échantillon</th><th></th><th></th></tr>
<tr><th><a href="/wiki/B" title="Édouard Philippe">Philippe</a> (HOR)</th><th><a href="/wiki/C" title="Marine Le Pen">Le Pen</a> (RN)</th></tr>
<tr><td></td><td></td></tr>
<tr><td>Ifop</td><td>9-10 novembre 2026</td><td>1 000</td><td>46</td><td>54</td></tr>
</table>
<h4>Hypothèse Mélenchon – Bardella</h4>
<table class="wikitable">
<tr><th rowspan="3">Sondeur</th><th rowspan="3">Dates</th><th rowspan="3">Échantillon</th><th></th><th></th></tr>
<tr><th><a href="/wiki/A" title="Jean-Luc Mélenchon">Mélenchon</a> (LFI)</th><th><a href="/wiki/D" title="Jordan Bardella">Bardella</a> (RN)</th></tr>
<tr><td></td><td></td></tr>
<tr><td>Ifop</td><td>9-10 novembre 2026</td><td>1 000</td><td>30</td><td>70</td></tr>
</table>
</body></html>
"""


@pytest.fixture
def parsed():
    return P.parse_polls(POLL_HTML)


def test_cac40_single_source_of_truth():
    assert len(CAC40) == 40
    assert len(set(TICKERS)) == 40
    assert abs(sum(c["index_weight"] for c in CAC40) - 100) < 0.05
    assert "STMPA.PA" in TICKERS and "STLAP.PA" in TICKERS


def test_first_round_parsing_groups_hypotheses(parsed):
    polls = sorted(parsed["first_round"], key=lambda p: p["date"], reverse=True)
    assert len(polls) == 2
    ifop = polls[0]
    assert ifop["pollster"] == "Ifop" and ifop["date"] == date(2026, 11, 10)
    assert len(ifop["hypotheses"]) == 2
    assert ifop["hypotheses"][0] == {"melenchon": 18.0, "philippe": 16.0, "le pen": 33.0}
    assert "philippe" not in ifop["hypotheses"][1]
    assert polls[1]["date"] == date(2026, 11, 2)
    assert polls[1]["hypotheses"][0]["melenchon"] == 17.5


def test_candidate_blocs(parsed):
    c = parsed["candidates"]
    assert c["le pen"]["bloc"] == "far_right"
    assert c["philippe"]["bloc"] == "centre_right"
    assert c["melenchon"]["bloc"] == "left"


def test_runoff_lookup_uses_rn_alias(parsed):
    table = P._RunoffTable(parsed["second_round"], date(2026, 11, 10), parsed["candidates"])
    share, estimated = table.share("philippe", "le pen")
    assert share == pytest.approx(46.0) and not estimated
    # No Mélenchon–Le Pen poll: falls back to the Mélenchon–Bardella head-to-head
    share, estimated = table.share("le pen", "melenchon")
    assert share == pytest.approx(70.0) and not estimated


def test_simulation_probabilities_are_consistent(parsed):
    result = P.simulate(parsed, today=date(2026, 11, 11), n_sims=4000)
    total_win = sum(c["p_win"] for c in result["candidates"])
    total_runoff = sum(c["p_runoff"] for c in result["candidates"])
    assert total_win == pytest.approx(1.0, abs=1e-3)
    assert total_runoff == pytest.approx(2.0, abs=1e-3)
    assert result["candidates"][0]["name"] == "Le Pen"
    assert sum(result["scenario_signal"].values()) == pytest.approx(1.0, abs=1e-3)


def test_blend_does_not_compound():
    prior = {"centrist": 0.35, "national_rally": 0.25, "left_wing": 0.25, "hung_parliament": 0.15}
    signals = {"polls": {"centrist": 0.1, "national_rally": 0.8, "left_wing": 0.05, "hung_parliament": 0.05}}
    first = blend(prior, signals)
    # Re-running with the same fixed prior gives the same answer — no drift.
    assert blend(prior, signals) == first
    assert abs(sum(first.values()) - 1) < 1e-9


def test_poll_signal_keeps_hung_parliament_prior():
    prior = {"centrist": 0.35, "national_rally": 0.25, "left_wing": 0.25, "hung_parliament": 0.15}
    sig = poll_signal_from_presidential({"scenario_signal": {"centrist": 0.2, "national_rally": 0.7, "left_wing": 0.1}}, prior)
    assert sig["hung_parliament"] == pytest.approx(0.15)
    assert sum(sig.values()) == pytest.approx(1.0)


def test_keyword_matching_is_whole_word():
    assert sum(_keyword_score("Le gouvernement veut concentrer ses efforts").values()) == 0
    assert _keyword_score("Le RN progresse")["national_rally"] == 1


def test_analog_impacts_scale_and_impute():
    cache = {"episodes": [
        {"id": eid, "stocks": {"BNP.PA": {"abnormal_pct": -10.0}, "GLE.PA": {"abnormal_pct": -6.0}}, "index_abnormal_pct": -2.0}
        for eid in {e for cfg in ANALOGS.values() for e in cfg["episodes"]}
    ]}
    impacts = analog_impacts(cache)
    scale = ANALOGS["national_rally"]["scale"]
    assert impacts["national_rally"]["BNP.PA"] == {"impact_pct": -10.0 * scale, "imputed": False}
    # ACA.PA missing → imputed from the Financials sector peers (mean of -10 and -6)
    assert impacts["national_rally"]["ACA.PA"]["impact_pct"] == pytest.approx(-8.0 * scale)
    assert impacts["national_rally"]["ACA.PA"]["imputed"]
