"""
Single source of truth for CAC40 constituents.

Revenue geography: approximate split from 2023 annual reports (french + euro + global ≈ 100).
Index weight: approximate float-adjusted weight (Nov 2024), normalised below so the index sums to 100%.
Tickers are Yahoo Finance symbols.
"""

_RAW = [
    # ticker,     isin,           name,                        sector,                    subsector,                     fr, eu, gl, weight
    ("AI.PA",    "FR0000120073", "Air Liquide",               "Materials",               "Industrial Gases",            15, 30, 55, 2.8),
    ("AIR.PA",   "NL0000235190", "Airbus",                    "Industrials",             "Aerospace & Defence",         15, 40, 45, 7.0),
    ("CS.PA",    "FR0000120628", "AXA",                       "Financials",              "Insurance",                   25, 40, 35, 2.5),
    ("BNP.PA",   "FR0000131104", "BNP Paribas",               "Financials",              "Banks",                       42, 33, 25, 4.5),
    ("EN.PA",    "FR0000120503", "Bouygues",                  "Industrials",             "Construction & Engineering",  65, 20, 15, 0.9),
    ("CAP.PA",   "FR0000125338", "Capgemini",                 "Information Technology",  "IT Services",                 15, 35, 50, 1.5),
    ("CA.PA",    "FR0000120172", "Carrefour",                 "Consumer Staples",        "Food Retail",                 45, 30, 25, 1.0),
    ("SGO.PA",   "FR0000125007", "Compagnie de Saint-Gobain", "Materials",               "Building Materials",          20, 40, 40, 2.1),
    ("ACA.PA",   "FR0000045072", "Crédit Agricole",           "Financials",              "Banks",                       65, 25, 10, 2.2),
    ("DSY.PA",   "FR0000130650", "Dassault Systèmes",         "Information Technology",  "Software",                    15, 30, 55, 2.3),
    ("EL.PA",    "FR0000121667", "EssilorLuxottica",          "Consumer Discretionary",  "Healthcare Equipment",         5, 20, 75, 4.0),
    ("ERF.PA",   "FR0014000MR3", "Eurofins Scientific",       "Healthcare",              "Life Sciences Tools",         15, 50, 35, 0.7),
    ("RMS.PA",   "FR0000052292", "Hermès International",      "Consumer Discretionary",  "Luxury Goods",                10, 15, 75, 8.5),
    ("KER.PA",   "FR0000121485", "Kering",                    "Consumer Discretionary",  "Luxury Goods",                 8, 15, 77, 2.6),
    ("OR.PA",    "FR0000120321", "L'Oréal",                   "Consumer Staples",        "Personal Products",            5, 20, 75, 5.0),
    ("LR.PA",    "FR0010307819", "Legrand",                   "Industrials",             "Electrical Equipment",        15, 30, 55, 1.3),
    ("MC.PA",    "FR0000121014", "LVMH",                      "Consumer Discretionary",  "Luxury Goods",                10, 15, 75, 11.2),
    ("ML.PA",    "FR001400AJ45", "Michelin",                  "Consumer Discretionary",  "Tyres",                       10, 25, 65, 1.4),
    ("ORA.PA",   "FR0000133308", "Orange",                    "Communication Services",  "Telecoms",                    55, 30, 15, 1.1),
    ("RI.PA",    "FR0000120693", "Pernod Ricard",             "Consumer Staples",        "Beverages",                    5, 15, 80, 1.6),
    ("PUB.PA",   "FR0000130577", "Publicis Groupe",           "Communication Services",  "Advertising",                  5, 15, 80, 2.4),
    ("RNO.PA",   "FR0000131906", "Renault",                   "Consumer Discretionary",  "Automobiles",                 25, 35, 40, 0.8),
    ("SAF.PA",   "FR0000073272", "Safran",                    "Industrials",             "Aerospace & Defence",         15, 25, 60, 3.5),
    ("SAN.PA",   "FR0000120578", "Sanofi",                    "Healthcare",              "Pharmaceuticals",              5, 20, 75, 5.5),
    ("SU.PA",    "FR0000121972", "Schneider Electric",        "Industrials",             "Electrical Equipment",        10, 25, 65, 6.5),
    ("GLE.PA",   "FR0000130809", "Société Générale",          "Financials",              "Banks",                       50, 30, 20, 2.0),
    ("STLAP.PA", "NL00150001Q9", "Stellantis",                "Consumer Discretionary",  "Automobiles",                 10, 40, 50, 1.8),
    ("STMPA.PA", "NL0000226223", "STMicroelectronics",        "Information Technology",  "Semiconductors",               5, 15, 80, 1.2),
    ("TEP.PA",   "FR0000051807", "Teleperformance",           "Industrials",             "Business Services",            5, 15, 80, 0.6),
    ("HO.PA",    "FR0000121329", "Thales",                    "Industrials",             "Aerospace & Defence",         25, 35, 40, 2.2),
    ("TTE.PA",   "FR0000120271", "TotalEnergies",             "Energy",                  "Integrated Oil & Gas",         5, 20, 75, 9.1),
    ("URW.PA",   "FR0013326246", "Unibail-Rodamco-Westfield", "Real Estate",             "Retail REITs",                25, 50, 25, 0.5),
    ("VIE.PA",   "FR0000124141", "Veolia Environnement",      "Utilities",               "Water & Waste",               25, 45, 30, 1.0),
    ("DG.PA",    "FR0000125486", "Vinci",                     "Industrials",             "Construction & Engineering",  45, 30, 25, 2.9),
    ("VIV.PA",   "FR0000127771", "Vivendi",                   "Communication Services",  "Media",                       50, 25, 25, 0.4),
    ("WLN.PA",   "FR0011981968", "Worldline",                 "Information Technology",  "Payment Processing",          25, 55, 20, 0.3),
    ("MT.AS",    "LU1598757687", "ArcelorMittal",             "Materials",               "Steel",                        5, 40, 55, 1.0),
    ("RF.PA",    "FR0000121121", "Eurazeo",                   "Financials",              "Asset Management",            60, 25, 15, 0.3),
    ("ALO.PA",   "FR0010220475", "Alstom",                    "Industrials",             "Rail Transport Equipment",    15, 40, 45, 0.5),
    ("ENGI.PA",  "FR0010208488", "Engie",                     "Utilities",               "Electric & Gas",              35, 40, 25, 2.3),
]

_WEIGHT_TOTAL = sum(r[8] for r in _RAW)

CAC40 = [
    {
        "ticker": t, "isin": isin, "name": name, "sector": sector, "subsector": sub,
        "french_pct": fr, "euro_pct": eu, "global_pct": gl,
        "index_weight": round(w * 100 / _WEIGHT_TOTAL, 3),
    }
    for (t, isin, name, sector, sub, fr, eu, gl, w) in _RAW
]

BY_TICKER = {c["ticker"]: c for c in CAC40}
TICKERS = [c["ticker"] for c in CAC40]
