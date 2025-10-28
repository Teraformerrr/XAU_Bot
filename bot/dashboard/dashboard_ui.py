# ============================================================
# XAU_Bot Live Dashboard — Phase 4 → Step 4.6
# Execution Control Dock + Live PnL/WinRate Visualization
# Author: Mohamed Jamshed
# ============================================================

import os
import json
import pandas as pd
from datetime import datetime
from dash import Dash, html, dcc
from dash.dependencies import Input, Output
from dash import no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from loguru import logger

# ============================================================
# Control File Interface (Dashboard ↔ Scheduler)
# ============================================================
CONTROL_FILE = "trade_control.json"

def write_control_state():
    """Save current control state to JSON for scheduler access."""
    try:
        with open(CONTROL_FILE, "w") as f:
            json.dump({
                "is_running": control_state["is_running"],
                "mode": control_state["mode"]
            }, f, indent=2)
    except Exception as e:
        logger.error(f"Error writing control file: {e}")

def read_control_state():
    """Read scheduler state from JSON (for UI sync)."""
    if not os.path.exists(CONTROL_FILE):
        return {"is_running": False, "mode": "PAPER"}
    try:
        with open(CONTROL_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"is_running": False, "mode": "PAPER"}


# ============================================================
# Initialize App
# ============================================================
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "XAU_Bot Live Dashboard (PnL + WinRate)"

# ============================================================
# Global Control State (Execution Dock)
# ============================================================
control_state = {
    "is_running": False,
    "mode": "PAPER",      # PAPER or LIVE
    "last_heartbeat": None,
}

def toggle_trading():
    """Toggle trading ON/OFF."""
    control_state["is_running"] = not control_state["is_running"]
    return control_state["is_running"]

def toggle_mode():
    """Switch between PAPER and LIVE."""
    control_state["mode"] = "LIVE" if control_state["mode"] == "PAPER" else "PAPER"
    return control_state["mode"]

def update_heartbeat():
    """Update heartbeat timestamp."""
    control_state["last_heartbeat"] = datetime.utcnow().strftime("%H:%M:%S")

# ============================================================
# Helper Functions
# ============================================================
def read_live_equity():
    """Load latest equity from portfolio_state.json"""
    path = os.path.join("portfolio_state.json")
    if not os.path.exists(path):
        return 0.0, datetime.utcnow().strftime("%H:%M:%S")
    try:
        with open(path, "r") as f:
            data = json.load(f)
        equity = round(data.get("equity", 0.0), 2)
        ts = data.get("timestamp", datetime.utcnow().strftime("%H:%M:%S"))
        logger.debug(f"Live equity from portfolio_state.json → {equity} @ {ts}")
        return equity, ts
    except Exception as e:
        logger.error(f"Error reading portfolio_state.json: {e}")
        return 0.0, datetime.utcnow().strftime("%H:%M:%S")

def read_pnl_data():
    """Load pnl_history.csv"""
    path = os.path.join("reports", "pnl_history.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["time", "pnl"])
    try:
        df = pd.read_csv(path)
        df["time"] = pd.to_datetime(df["time"], errors="ignore")
        return df
    except Exception as e:
        logger.error(f"Error reading pnl_history.csv: {e}")
        return pd.DataFrame(columns=["time", "pnl"])

    # ============================================================
    # Read AI Decision Logs
    # ============================================================
    def read_ai_decisions():
        """Load recent AI decisions for display."""
        path = os.path.join("reports", "logs", "ai_decisions.csv")
        if not os.path.exists(path):
            return pd.DataFrame(columns=["time", "action", "confidence", "volatility"])
        try:
            df = pd.read_csv(path)
            df["time"] = pd.to_datetime(df["time"], errors="ignore")
            df = df.tail(10).iloc[::-1]  # show last 10, newest first
            return df
        except Exception as e:
            logger.error(f"Error reading ai_decisions.csv: {e}")
            return pd.DataFrame(columns=["time", "action", "confidence", "volatility"])

        # ============================================================
        # Read Trade Execution Logs (NDJSON format)
        # ============================================================
        def read_trade_executions():
            """Read the latest executed trades from JSON log."""
            path = os.path.join("reports", "trades_history.json")
            if not os.path.exists(path):
                return pd.DataFrame(columns=[
                    "timestamp", "symbol", "action", "volume",
                    "price", "pnl", "status", "confidence",
                    "volatility", "equity"
                ])
            try:
                records = []
                with open(path, "r") as f:
                    for line in f:
                        if line.strip():
                            records.append(json.loads(line))
                df = pd.DataFrame(records)
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="ignore")
                df = df.sort_values("timestamp", ascending=False).head(10)
                return df
            except Exception as e:
                logger.error(f"Error reading trades_history.json: {e}")
                return pd.DataFrame(columns=[
                    "timestamp", "symbol", "action", "volume",
                    "price", "pnl", "status", "confidence",
                    "volatility", "equity"
                ])


def read_winrate_data():
    """Load winrate_history.csv"""
    path = os.path.join("reports", "winrate_history.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["time", "win_rate"])
    try:
        df = pd.read_csv(path)
        df["time"] = pd.to_datetime(df["time"], errors="ignore")
        return df
    except Exception as e:
        logger.error(f"Error reading winrate_history.csv: {e}")
        return pd.DataFrame(columns=["time", "win_rate"])

# ============================================================
# Layout
# ============================================================
app.layout = html.Div(
    [
        html.H2("💹 XAU_Bot Live Dashboard (PnL + WinRate)", style={"color": "#FFD700"}),

        # ───────────────────────────────────────────────
        # Execution Control Dock
        # ───────────────────────────────────────────────
        html.Div(
            [
                html.H4("🧠 Execution Control Dock", style={"marginBottom": "10px"}),

                html.Div(
                    [
                        html.Button(
                            "Start Trading",
                            id="btn-start",
                            n_clicks=0,
                            style={
                                "backgroundColor": "#28a745",
                                "color": "white",
                                "marginRight": "10px",
                                "padding": "10px 20px",
                                "borderRadius": "8px",
                                "fontWeight": "bold",
                            },
                        ),
                        html.Button(
                            "Switch to LIVE Mode",
                            id="btn-mode",
                            n_clicks=0,
                            style={
                                "backgroundColor": "#007bff",
                                "color": "white",
                                "marginRight": "10px",
                                "padding": "10px 20px",
                                "borderRadius": "8px",
                                "fontWeight": "bold",
                            },
                        ),
                        html.Span(
                            "Heartbeat: ⏳",
                            id="heartbeat",
                            style={
                                "fontWeight": "bold",
                                "color": "#ffcc00",
                                "marginLeft": "15px",
                                "fontSize": "16px",
                            },
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "marginBottom": "10px"},
                ),
            ],
            style={
                "border": "1px solid #444",
                "borderRadius": "10px",
                "padding": "12px",
                "backgroundColor": "#1e1e1e",
                "color": "white",
                "marginBottom": "25px",
            },
        ),


# ───────────────────────────────────────────────
# AI Decision Log Dock
# ───────────────────────────────────────────────
html.Div(
    [
        html.H4("🤖 AI Decision Log", style={"marginBottom": "10px", "color": "#00FFFF"}),
        html.Div(id="ai-log-container"),
    ],
    style={
        "border": "1px solid #333",
        "borderRadius": "10px",
        "padding": "12px",
        "backgroundColor": "#1b1b1b",
        "color": "white",
        "marginBottom": "25px",
        "maxHeight": "300px",
        "overflowY": "auto",
    },
),


# ───────────────────────────────────────────────
# Real-Time Trade Execution Dock + Summary
# ───────────────────────────────────────────────
html.Div(
    [
        html.H4("💼 Real-Time Trade Execution Log", style={"color": "#FFA500", "marginBottom": "10px"}),

        # ── Summary Row
        html.Div(
            id="trade-summary",
            style={
                "marginBottom": "10px",
                "fontWeight": "bold",
                "color": "#00FFFF",
                "fontSize": "15px",
            },
        ),

        # ── Filter Dropdown
        html.Div(
            [
                dcc.Dropdown(
                    id="trade-filter",
                    options=[
                        {"label": "All Trades", "value": "ALL"},
                        {"label": "Open Trades", "value": "OPEN"},
                        {"label": "Closed Trades", "value": "CLOSED"},
                    ],
                    value="ALL",
                    clearable=False,
                    style={"width": "220px", "color": "#000"},
                ),
            ],
            style={"marginBottom": "10px"},
        ),

        # ── Scrollable Trade List
        html.Div(id="trade-log-container"),
    ],
    style={
        "border": "1px solid #444",
        "borderRadius": "10px",
        "padding": "12px",
        "backgroundColor": "#1b1b1b",
        "color": "white",
        "marginBottom": "25px",
        "maxHeight": "400px",
        "overflowY": "auto",
    },
),



        # ───────────────────────────────────────────────
        # Metrics Display
        # ───────────────────────────────────────────────
        html.Div(
            [
                html.H4("📊 Portfolio Metrics", style={"color": "#00ff99"}),
                html.Div(id="live-equity-display", style={"marginBottom": "10px"}),
                html.Div(id="timestamp-display"),
            ],
            style={
                "border": "1px solid #333",
                "borderRadius": "10px",
                "padding": "15px",
                "backgroundColor": "#202020",
                "color": "white",
            },
        ),

        # ───────────────────────────────────────────────
        # Charts
        # ───────────────────────────────────────────────
        html.Div(
            [
                dcc.Graph(id="pnl-chart"),
                dcc.Graph(id="winrate-chart"),
                dcc.Interval(
                    id="interval-component",
                    interval=5 * 1000,  # 5 seconds
                    n_intervals=0,
                ),
            ]
        ),
    ],
    style={"padding": "20px", "backgroundColor": "#111"},
)

# ============================================================
# Callback: Live Trade Execution Log + Summary + Filter
# ============================================================

@app.callback(
    Output("trade-log-container", "children"),
    Output("trade-summary", "children"),
    Input("interval-component", "n_intervals"),
    Input("trade-filter", "value"),
)
def update_trade_log(n, filter_value):
    df = read_trade_executions()
    if df.empty:
        return html.Div("No trades logged yet.", style={"color": "#888"}), "No data"

    # ── Filtering
    if filter_value != "ALL":
        df = df[df["status"].str.upper() == filter_value.upper()]

    # ── Summary Stats
    total_pnl = df["pnl"].sum()
    total_trades = len(df)
    closed_df = df[df["status"].str.upper() == "CLOSED"]
    wins = closed_df[closed_df["pnl"] > 0]
    win_rate = (len(wins) / len(closed_df) * 100) if len(closed_df) > 0 else 0
    open_trades = len(df[df["status"].str.upper() == "OPEN"])

    summary = (
        f"💰 Total PnL: {total_pnl:+.2f}  |  🏆 Win Rate: {win_rate:.1f}%  |  📂 Open Trades: {open_trades}"
    )

    # ── Display Rows
    rows = []
    for _, r in df.iterrows():
        color = "#28a745" if r["action"] == "BUY" else "#dc3545" if r["action"] == "SELL" else "#ffcc00"
        pnl_color = "#00FF00" if r["pnl"] >= 0 else "#FF5555"
        rows.append(
            html.Div(
                [
                    html.Span(f"{r['timestamp']} | ", style={"color": "#888"}),
                    html.Span(f"{r['symbol']} ", style={"color": "#00BFFF"}),
                    html.Span(f"{r['action']}", style={"color": color, "fontWeight": "bold"}),
                    html.Span(f" | vol={r['volume']} @ {r['price']:.2f} ", style={"color": "#ccc"}),
                    html.Span(f"| PnL: {r['pnl']:+.2f} ", style={"color": pnl_color}),
                    html.Span(f"Eq: {r['equity']:.2f} ", style={"color": "#FFD700"}),
                    html.Span(f"({r['status']})", style={"color": "#999"}),
                ],
                style={"marginBottom": "3px", "fontSize": "15px"},
            )
        )

    return rows, summary




# ============================================================
# Callbacks for Charts + Live Updates
# ============================================================

@app.callback(
    Output("live-equity-display", "children"),
    Output("timestamp-display", "children"),
    Output("pnl-chart", "figure"),
    Output("winrate-chart", "figure"),
    Input("interval-component", "n_intervals"),
)
def update_dashboard(n):
    """Live update loop."""
    equity, ts = read_live_equity()
    pnl_df = read_pnl_data()
    wr_df = read_winrate_data()

    update_heartbeat()

    pnl_fig = {
        "data": [
            {
                "x": pnl_df["time"],
                "y": pnl_df["pnl"],
                "type": "line",
                "name": "PnL",
            }
        ],
        "layout": {
            "title": "💰 Profit & Loss Trend",
            "paper_bgcolor": "#111",
            "plot_bgcolor": "#111",
            "font": {"color": "white"},
        },
    }

    winrate_fig = {
        "data": [
            {
                "x": wr_df["time"],
                "y": wr_df["win_rate"],
                "type": "line",
                "name": "WinRate",
                "line": {"color": "#00FFAA"},
            }
        ],
        "layout": {
            "title": "🏆 Win Rate Trend",
            "paper_bgcolor": "#111",
            "plot_bgcolor": "#111",
            "font": {"color": "white"},
        },
    }

    equity_text = f"💼 Current Equity: ${equity:,.2f}"
    timestamp_text = f"⏱ Last Updated: {ts}"
    return equity_text, timestamp_text, pnl_fig, winrate_fig


# ============================================================
# Callbacks for Execution Control Dock (Scheduler Integration)
# ============================================================

@app.callback(
    Output("btn-start", "children"),
    Output("btn-start", "style"),
    Input("btn-start", "n_clicks"),
    prevent_initial_call=True,
)
def on_start_click(n):
    running = toggle_trading()
    write_control_state()  # 🔥 persist change
    if running:
        style = {
            "backgroundColor": "#dc3545",
            "color": "white",
            "padding": "10px 20px",
            "borderRadius": "8px",
            "fontWeight": "bold",
        }
        label = "Pause Trading"
    else:
        style = {
            "backgroundColor": "#28a745",
            "color": "white",
            "padding": "10px 20px",
            "borderRadius": "8px",
            "fontWeight": "bold",
        }
        label = "Start Trading"
    return label, style


@app.callback(
    Output("btn-mode", "children"),
    Output("btn-mode", "style"),
    Input("btn-mode", "n_clicks"),
    prevent_initial_call=True,
)
def on_mode_click(n):
    mode = toggle_mode()
    write_control_state()  # 🔥 persist change
    if mode == "LIVE":
        style = {
            "backgroundColor": "#ff8800",
            "color": "white",
            "padding": "10px 20px",
            "borderRadius": "8px",
            "fontWeight": "bold",
        }
        label = "Switch to PAPER Mode"
    else:
        style = {
            "backgroundColor": "#007bff",
            "color": "white",
            "padding": "10px 20px",
            "borderRadius": "8px",
            "fontWeight": "bold",
        }
        label = "Switch to LIVE Mode"
    return label, style



@app.callback(
    Output("heartbeat", "children"),
    Input("interval-component", "n_intervals"),
)
def update_heartbeat_status(n):
    update_heartbeat()
    symbol = "💓" if control_state["is_running"] else "💤"
    text = f"Heartbeat: {symbol} {control_state['last_heartbeat']} | Mode: {control_state['mode']}"
    return text


# ============================================================
# Callback: Live AI Decision Log Updates
# ============================================================

@app.callback(
    Output("ai-log-container", "children"),
    Input("interval-component", "n_intervals"),
)
def update_ai_log(n):
    df = read_ai_decisions()
    if df.empty:
        return html.Div("No AI decisions logged yet.", style={"color": "#888"})

    rows = []
    for _, r in df.iterrows():
        color = "#28a745" if r["action"] == "BUY" else "#dc3545" if r["action"] == "SELL" else "#ffcc00"
        rows.append(
            html.Div(
                [
                    html.Span(f"{r['time']}  |  ", style={"color": "#999"}),
                    html.Span(f"{r['action']}", style={"color": color, "fontWeight": "bold"}),
                    html.Span(f"  |  conf={r['confidence']:.2f}  vol={r['volatility']:.2f}", style={"color": "#ccc"}),
                ],
                style={"marginBottom": "3px", "fontSize": "15px"},
            )
        )

    return rows



# ============================================================
# Main Entry
# ============================================================
if __name__ == "__main__":
    logger.info("🚀 Starting XAU_Bot Live Dashboard (PnL + WinRate + Control Dock)")
    app.run(debug=True)

