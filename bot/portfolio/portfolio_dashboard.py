import os
import json
import pandas as pd
from dash import Dash, dcc, html, dash_table, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go

from bot.portfolio.portfolio_metrics import PortfolioMetrics

REPORTS_DIR = r"D:\XAU_Bot\reports"
TRADES_LOG = os.path.join(REPORTS_DIR, "trade_log.json")

def render_header(df: pd.DataFrame):
    if df.empty:
        balance = 100000.0
        equity = 100000.0
        realized_pnl = 0.0
        unrealized_pnl = 0.0
        status = "OFFLINE"
        color = "#9ca3af"
    else:
        df = df.sort_values("timestamp")
        balance = float(df["equity"].iloc[0])
        equity = float(df["equity"].iloc[-1])
        realized_pnl = float(df["pnl"].sum())
        unrealized_pnl = float(df["equity"].iloc[-1] - (df["equity"].iloc[0] + realized_pnl))
        status = "SIMULATION" if "SIMULATED" in df["status"].unique() else "LIVE"
        color = "#10b981" if status == "LIVE" else "#f59e0b"

    return html.Div(
        className="header-bar",
        children=[
            html.Div([
                html.Span("💰 Balance: ", className="label"),
                html.Span(f"${balance:,.2f}", className="value")
            ]),
            html.Div([
                html.Span("📊 Equity: ", className="label"),
                html.Span(f"${equity:,.2f}", className="value")
            ]),
            html.Div([
                html.Span("✅ Realized PnL: ", className="label"),
                html.Span(f"${realized_pnl:,.2f}", className="value", style={"color": "#10b981" if realized_pnl >= 0 else "#ef4444"})
            ]),
            html.Div([
                html.Span("📈 Unrealized: ", className="label"),
                html.Span(f"${unrealized_pnl:,.2f}", className="value", style={"color": "#60a5fa" if unrealized_pnl >= 0 else "#ef4444"})
            ]),
            html.Div([
                html.Span("● ", style={"color": color, "fontSize": "22px", "verticalAlign": "middle"}),
                html.Span(status, className="value")
            ])
        ],
        style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "background": "#121826",
            "padding": "10px 18px",
            "borderRadius": "10px",
            "marginBottom": "12px",
            "boxShadow": "0 4px 12px rgba(0,0,0,0.3)"
        }
    )


def load_trades() -> pd.DataFrame:
    if not os.path.exists(TRADES_LOG):
        return pd.DataFrame(columns=[
            "symbol","action","confidence","volatility","volume","price","pnl","status","timestamp","equity"
        ])
    with open(TRADES_LOG, "r") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    # normalize columns if missing
    for col in ["symbol","action","confidence","volatility","volume","price","pnl","status","timestamp","equity"]:
        if col not in df.columns:
            df[col] = None
    # parse timestamp
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    # infer equity if missing
    if df["equity"].isna().all():
        start_equity = 100000.0
        if len(df) and pd.notna(df.iloc[0].get("pnl")):
            try:
                start_equity = float(df.iloc[0].get("equity", float("nan")))
                if pd.isna(start_equity):
                    # try to infer from first pnl
                    first_pnl = float(df.iloc[0]["pnl"])
                    start_equity = 100000.0 - first_pnl
            except Exception:
                start_equity = 100000.0
        df = df.sort_values("timestamp").reset_index(drop=True)
        eq = start_equity + df["pnl"].fillna(0).cumsum()
        df["equity"] = eq
    return df.sort_values("timestamp").reset_index(drop=True)

def load_metrics() -> dict:
    # Uses your existing PortfolioMetrics module
    return PortfolioMetrics().summary()

def win_loss_breakdown(df: pd.DataFrame):
    if df.empty:
        return 0, 0
    wins = int((df["pnl"].fillna(0) > 0).sum())
    losses = int((df["pnl"].fillna(0) < 0).sum())
    return wins, losses

def equity_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty or df["equity"].isna().all():
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", paper_bgcolor="#121826", plot_bgcolor="#121826")
        return fig
    fig = px.line(df, x="timestamp", y="equity", title="Equity Curve")
    fig.update_layout(template="plotly_dark", paper_bgcolor="#121826", plot_bgcolor="#121826", margin=dict(l=20,r=20,t=40,b=20))
    return fig

def winloss_figure(df: pd.DataFrame) -> go.Figure:
    wins, losses = win_loss_breakdown(df)
    fig = px.bar(pd.DataFrame({"Outcome":["Win","Loss"], "Count":[wins, losses]}),
                 x="Outcome", y="Count", title="Win / Loss Distribution")
    fig.update_layout(template="plotly_dark", paper_bgcolor="#121826", plot_bgcolor="#121826", margin=dict(l=20,r=20,t=40,b=20))
    fig.update_traces(marker_line_width=0)
    return fig

def pnl_gauge(df: pd.DataFrame) -> go.Figure:
    if df.empty or df["equity"].isna().all():
        current = 0
        base = 0
    else:
        base = float(df["equity"].iloc[0])
        current = float(df["equity"].iloc[-1])
    daily_pnl = current - base
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=daily_pnl,
        number={"prefix":"$", "valueformat":",.2f"},
        delta={"reference":0, "increasing":{"color":"#16a34a"}, "decreasing":{"color":"#ef4444"}},
        gauge={
            "axis":{"range":[min(-abs(daily_pnl)*1.5, -5000), max(abs(daily_pnl)*1.5, 5000)]},
            "bar":{"color":"#1f6feb"},
        },
        title={"text":"Daily PnL"}
    ))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#121826", margin=dict(l=20,r=20,t=40,b=20))
    return fig

app = Dash(__name__, title="📊 XAU_Bot Portfolio Dashboard")

app.layout = html.Div([
    html.H1("📈 XAU_Bot — Portfolio Dashboard"),

    # ✅ Add this new line below
    html.Div(id="live-header"),

    html.Div(className="controls", children=[
        

        html.Div("Auto-refresh:", style={"color":"#a0a9b8"}),
        dcc.Checklist(
            id="auto_refresh", options=[{"label":" Enabled", "value":"on"}], value=["on"],
            inputStyle={"marginRight":"6px"}
        ),
        html.Div("Interval:", style={"color":"#a0a9b8"}),
        dcc.Dropdown(
            id="refresh_ms",
            options=[
                {"label":"5s","value":5000},
                {"label":"10s","value":10000},
                {"label":"30s","value":30000},
                {"label":"60s","value":60000},
            ],
            value=30000, clearable=False, style={"width":"120px"}
        ),
        html.Button("Refresh Now", id="manual_refresh", n_clicks=0,
                    style={"background":"#1f6feb","color":"white","border":"0","padding":"8px 12px","borderRadius":"10px"})
    ]),
    dcc.Interval(id="interval", interval=30000, n_intervals=0),

    dcc.Tabs(id="tabs", value="tab-overview", children=[
        dcc.Tab(label="Overview", value="tab-overview"),
        dcc.Tab(label="Trades", value="tab-trades"),
        dcc.Tab(label="Settings", value="tab-settings"),
    ]),

    html.Div(id="tab-content", style={"marginTop":"12px"})
])

# -------- tab content callback --------
@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("interval", "n_intervals"),
    Input("manual_refresh", "n_clicks"),
    State("auto_refresh", "value"),
)
def render_tab(tab, n_auto, n_manual, auto_state):
    # Load fresh data each time to keep it live
    df = load_trades()
    metrics = load_metrics()

    # KPI grid
    total_trades = int(metrics.get("total_trades", len(df)))
    win_rate = float(metrics.get("win_rate", ((df["pnl"]>0).mean()*100 if len(df) else 0)))
    expectancy = float(metrics.get("expectancy", df["pnl"].mean() if len(df) else 0))
    total_return = float(metrics.get("total_return", df["pnl"].sum() if len(df) else 0))
    sharpe = metrics.get("sharpe", None)
    drawdown = metrics.get("max_drawdown", None)

    kpi = html.Div(className="kpi", children=[
        html.Div(className="item", children=[html.Div("Total Trades", className="label"), html.Div(f"{total_trades}", className="value")]),
        html.Div(className="item", children=[html.Div("Win Rate", className="label"), html.Div(f"{win_rate:.2f}%", className="value")]),
        html.Div(className="item", children=[html.Div("Expectancy", className="label"), html.Div(f"${expectancy:,.2f}", className="value")]),
        html.Div(className="item", children=[html.Div("Total Return", className="label"), html.Div(f"${total_return:,.2f}", className="value")]),
    ])

    if tab == "tab-overview":
        return html.Div([
            kpi,
            html.Div(style={"height":"12px"}),
            html.Div(className="card", children=[
                html.Div([
                    html.Div([dcc.Graph(figure=equity_figure(df))], style={"width":"49%","display":"inline-block","verticalAlign":"top"}),
                    html.Div([dcc.Graph(figure=winloss_figure(df))], style={"width":"49%","display":"inline-block","verticalAlign":"top","float":"right"}),
                ])
            ]),
            html.Div(style={"height":"12px"}),
            html.Div(className="card", children=[dcc.Graph(figure=pnl_gauge(df))]),
            html.Div(style={"height":"8px"}),
            html.Div(style={"color":"#a0a9b8"}, children=f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        ])

    elif tab == "tab-trades":
        # filter controls
        actions = sorted([x for x in df["action"].dropna().unique()]) if not df.empty else []
        return html.Div([
            html.Div(className="card", children=[
                html.Div("Filters", style={"fontWeight":700, "marginBottom":"8px"}),
                html.Div(className="controls", children=[
                    dcc.Dropdown(
                        id="action_filter", options=[{"label":"All","value":"all"}]+[{"label":a,"value":a} for a in actions],
                        value="all", clearable=False, placeholder="Action"
                    ),
                ])
            ]),
            html.Div(style={"height":"10px"}),
            html.Div(id="trades-table-container")
        ])

    elif tab == "tab-settings":
        return html.Div(className="card", children=[
            html.H3("Settings"),
            html.P("Auto-refresh is controlled at the top bar. UI settings and theme are applied via assets/custom.css."),
            html.P("Coming soon in Phase 3: model selection, training schedule, and rollout strategy.")
        ])

    return html.Div()

# -------- trades table (separate so filters can update without reloading the whole tab) --------
@app.callback(
    Output("trades-table-container", "children"),
    Input("action_filter", "value"),
    Input("interval", "n_intervals"),
    Input("manual_refresh", "n_clicks"),
)
def update_trades_table(action_value, n_auto, n_manual):
    df = load_trades()
    if action_value and action_value != "all":
        df = df[df["action"] == action_value]

    # nice column order if present
    preferred = ["timestamp","symbol","action","confidence","volatility","volume","price","pnl","equity","status"]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    df = df[cols] if cols else df

    # text formatting
    if "confidence" in df.columns:
        df["confidence"] = df["confidence"].map(lambda x: None if pd.isna(x) else round(float(x), 4))
    if "volatility" in df.columns:
        df["volatility"] = df["volatility"].map(lambda x: None if pd.isna(x) else round(float(x), 4))
    if "pnl" in df.columns:
        df["pnl"] = df["pnl"].map(lambda x: None if pd.isna(x) else float(x))

    style_conditional = []
    if "pnl" in df.columns:
        style_conditional += [
            {"if": {"filter_query": "{pnl} > 0", "column_id": "pnl"}, "color": "#16a34a", "fontWeight": "700"},
            {"if": {"filter_query": "{pnl} < 0", "column_id": "pnl"}, "color": "#ef4444", "fontWeight": "700"},
        ]
    if "action" in df.columns:
        style_conditional += [
            {"if": {"filter_query": "{action} = BUY", "column_id": "action"}, "color": "#1f6feb", "fontWeight": "700"},
            {"if": {"filter_query": "{action} = SELL", "column_id": "action"}, "color": "#f59e0b", "fontWeight": "700"},
        ]

    table = dash_table.DataTable(
        data=df.to_dict("records"),
        columns=[{"name": c.capitalize(), "id": c} for c in df.columns],
        page_size=12,
        sort_action="native",
        filter_action="native",
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor":"#0b1020","fontWeight":"700","border":"0"},
        style_data={"backgroundColor":"#121826","color":"#e6edf3","border":"0"},
        style_data_conditional=style_conditional,
    )
    return html.Div(className="card", children=[table])

# -------- interval control from UI --------
@app.callback(
    Output("interval", "interval"),
    Input("refresh_ms", "value"),
    Input("auto_refresh", "value"),
)
def set_interval(ms, auto_state):
    if auto_state and "on" in auto_state:
        return int(ms or 30000)
    # if disabled, set a very large interval
    return 10**9

if __name__ == "__main__":
    app.run(debug=False, port=8050)


