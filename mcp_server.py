#!/usr/bin/env python3
"""
France Political Intelligence - Local MCP Server
Read-only stdio MCP server for Claude Code integration.

Usage:
  python3 mcp_server.py

Add to Claude Code settings.json:
  {
    "mcpServers": {
      "france-intel": {
        "command": "python3",
        "args": ["/path/to/france-political-intelligence/mcp_server.py"],
        "env": {}
      }
    }
  }
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timezone

# Add backend to path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, BACKEND_DIR)

API_BASE = "http://localhost:8000"


async def call_api(path: str) -> dict:
    """Call the local FastAPI backend."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}{path}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"error": f"HTTP {resp.status}", "path": path}
    except Exception as e:
        return {"error": str(e), "note": "Backend may not be running. Start with: cd backend && uvicorn main:app --port 8000"}


async def call_api_post(path: str, body: dict) -> dict:
    """POST to the local FastAPI backend."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}{path}",
                json=body,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                return await resp.json()
    except Exception as e:
        return {"error": str(e)}


TOOLS = [
    {
        "name": "get_latest_news",
        "description": "Get the latest news articles from the France Political Intelligence database. Returns articles with topic tags, entities, and relevance scores.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of articles to return (default: 10, max: 50)", "default": 10},
                "topic": {"type": "string", "description": "Filter by topic: politics, fiscal, ecb, energy, defence, trade, macro, companies"}
            }
        }
    },
    {
        "name": "search_news",
        "description": "Search news articles by keyword.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_event_details",
        "description": "Get details of a specific political/economic event.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "Event ID"}
            },
            "required": ["event_id"]
        }
    },
    {
        "name": "get_political_scenarios",
        "description": "Get all four French political scenario frameworks with their assumptions and probabilities.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_scenario_assumptions",
        "description": "Get detailed policy assumptions for a specific scenario.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scenario_id": {"type": "integer", "description": "Scenario ID (1-4)"}
            },
            "required": ["scenario_id"]
        }
    },
    {
        "name": "get_cac40_universe",
        "description": "Get the CAC 40 constituent universe with sector and exposure data.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sector": {"type": "string", "description": "Filter by sector (optional)"}
            }
        }
    },
    {
        "name": "get_company_exposure",
        "description": "Get a company's political scenario exposure and sensitivity data.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Company ticker symbol (e.g. MC, TTE, SAN)"}
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_portfolio_summary",
        "description": "Get the demo portfolio summary with holdings and weights.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "run_stress_test",
        "description": "Run a deterministic stress test on the demo portfolio. Returns P&L by holding and sector.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "market_shock_pct": {"type": "number", "description": "Market shock as decimal (e.g. -0.1 for -10%)"},
                "sovereign_spread_bps": {"type": "number", "description": "Sovereign spread widening in basis points (e.g. 100)"},
                "eur_shock_pct": {"type": "number", "description": "EUR shock as decimal (e.g. -0.05 for -5%)"},
                "ecb_rate_bps": {"type": "number", "description": "ECB rate change in basis points (e.g. 25)"},
                "energy_shock_pct": {"type": "number", "description": "Energy price shock as decimal (e.g. 0.2 for +20%)"}
            }
        }
    },
    {
        "name": "get_ecb_scenarios",
        "description": "Get ECB monetary policy scenarios including successor profiles.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_methodology",
        "description": "Get methodology documentation, model versions, data quality status and limitations.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_forecast_history",
        "description": "Get historical forecast records with outcomes where available.",
        "inputSchema": {"type": "object", "properties": {}}
    }
]


async def handle_tool(name: str, arguments: dict) -> str:
    """Execute a tool call and return result as JSON string."""

    if name == "get_latest_news":
        params = []
        if "limit" in arguments:
            params.append(f"limit={arguments['limit']}")
        if "topic" in arguments:
            params.append(f"topic={arguments['topic']}")
        query = "&".join(params)
        result = await call_api(f"/api/news{'?' + query if query else ''}")

    elif name == "search_news":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        result = await call_api(f"/api/news?search={query}&limit={limit}")

    elif name == "get_event_details":
        event_id = arguments.get("event_id")
        result = await call_api(f"/api/events/{event_id}")

    elif name == "get_political_scenarios":
        result = await call_api("/api/scenarios")
        # Add provenance note
        if isinstance(result, list):
            result = {
                "scenarios": result,
                "provenance_note": "Probabilities are illustrative analyst inputs, not election forecasts.",
                "data_note": "Scenarios are hypothetical frameworks, not predictions."
            }

    elif name == "get_scenario_assumptions":
        scenario_id = arguments.get("scenario_id")
        result = await call_api(f"/api/scenarios/{scenario_id}")

    elif name == "get_cac40_universe":
        params = []
        if "sector" in arguments:
            params.append(f"sector={arguments['sector']}")
        query = "&".join(params)
        result = await call_api(f"/api/companies{'?' + query if query else ''}")

    elif name == "get_company_exposure":
        ticker = arguments.get("ticker", "").upper()
        result = await call_api(f"/api/companies/{ticker}")

    elif name == "get_portfolio_summary":
        result = await call_api("/api/portfolio/demo")
        if "error" not in result:
            result["privacy_note"] = "Portfolio data is local only. Not sent to external services."

    elif name == "run_stress_test":
        # Get demo portfolio first
        portfolio = await call_api("/api/portfolio/demo")
        if "error" in portfolio:
            return json.dumps(portfolio)

        shocks = {}
        if "market_shock_pct" in arguments:
            shocks["market"] = arguments["market_shock_pct"]
        if "sovereign_spread_bps" in arguments:
            shocks["sovereign_spread"] = arguments["sovereign_spread_bps"]
        if "eur_shock_pct" in arguments:
            shocks["eur"] = arguments["eur_shock_pct"]
        if "ecb_rate_bps" in arguments:
            shocks["ecb_rate"] = arguments["ecb_rate_bps"]
        if "energy_shock_pct" in arguments:
            shocks["energy"] = arguments["energy_shock_pct"]

        result = await call_api_post("/api/stress-tests/run", {
            "portfolio_id": portfolio.get("id", 1),
            "shocks": shocks,
            "methodology": "deterministic"
        })
        if "error" not in result:
            result["methodology_note"] = "Deterministic calculation. Not a forecast."

    elif name == "get_ecb_scenarios":
        result = await call_api("/api/ecb")
        if isinstance(result, list):
            result = {
                "ecb_scenarios": result,
                "disclaimer": "Successor profiles are hypothetical. Not predictions of actual ECB appointments."
            }

    elif name == "get_methodology":
        result = await call_api("/api/methodology")

    elif name == "get_forecast_history":
        result = await call_api("/api/model-runs")

    else:
        result = {"error": f"Unknown tool: {name}"}

    return json.dumps(result, default=str, indent=2)


async def main():
    """MCP stdio server main loop."""

    async def send_message(msg: dict):
        line = json.dumps(msg) + "\n"
        sys.stdout.write(line)
        sys.stdout.flush()

    async def read_message() -> dict | None:
        line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        if not line:
            return None
        return json.loads(line.strip())

    # Send capabilities
    await send_message({
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
    })

    while True:
        try:
            msg = await read_message()
            if msg is None:
                break

            msg_id = msg.get("id")
            method = msg.get("method")
            params = msg.get("params", {})

            if method == "initialize":
                await send_message({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "0.1.0",
                        "capabilities": {"tools": {}},
                        "serverInfo": {
                            "name": "france-political-intelligence",
                            "version": "0.1.0"
                        }
                    }
                })

            elif method == "tools/list":
                await send_message({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": TOOLS}
                })

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                try:
                    content = await handle_tool(tool_name, arguments)
                    await send_message({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": content}],
                            "isError": False
                        }
                    })
                except Exception as e:
                    await send_message({
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps({"error": str(e)})}],
                            "isError": True
                        }
                    })

            else:
                await send_message({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                })

        except Exception as e:
            # Log to stderr only
            print(f"MCP server error: {e}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
