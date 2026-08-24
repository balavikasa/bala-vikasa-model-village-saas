from __future__ import annotations

from flask import abort, current_app, request
from flask_login import current_user

from .models import Role
from .services.monitoring import dashboard_series


PALETTE = {
    "navy": "#1F4E5F",
    "saffron": "#E8A93A",
    "green": "#5B8C5E",
    "clay": "#C1543C",
    "paper": "#F3F1EA",
    "ink": "#182327",
}


def init_dash(app):
    """Mount the Plotly Dash monitoring surface at ``/dash/``.

    The import is delayed so CLI/import/test tasks that do not need Dash still start
    with a clear fallback when the optional frontend dependency is unavailable.
    """

    try:
        from dash import Dash, Input, Output, dcc, html
        import plotly.graph_objects as go
    except ImportError:
        @app.get("/dash/")
        def dash_missing():
            if not current_user.is_authenticated:
                abort(401)
            return (
                "<main style='font-family:system-ui;padding:2rem'>"
                "<h1>Dashboard dependency missing</h1>"
                "<p>Install the project requirements, then restart the application.</p>"
                "</main>",
                503,
            )
        return None

    @app.before_request
    def protect_dash():
        if request.path.startswith("/dash/"):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in {Role.ADMIN, Role.PM, Role.PC}:
                abort(403)

    dash = Dash(
        __name__,
        server=app,
        url_base_pathname=app.config.get("DASH_URL_BASE_PATHNAME", "/dash/"),
        assets_folder=str((__import__("pathlib").Path(__file__).parent / "dash_assets")),
        title="Model Village Analytics",
        update_title="Updating…",
        suppress_callback_exceptions=True,
    )

    graph_config = {
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    }

    dash.layout = html.Main(
        className="dash-shell",
        children=[
            html.Header(
                className="dash-header",
                children=[
                    html.Div(
                        [
                            html.P("LIVE PROGRAM MONITORING", className="dash-eyebrow"),
                            html.H1("2026–27 model village analytics"),
                        ]
                    ),
                    html.Div(id="dash-scope", className="dash-scope"),
                ],
            ),
            dcc.Interval(id="dash-refresh", interval=60_000, n_intervals=0),
            html.Section(id="dash-kpis", className="dash-kpi-grid"),
            html.Section(
                className="dash-chart-grid",
                children=[
                    dcc.Graph(id="status-chart", config=graph_config, className="dash-card"),
                    dcc.Graph(id="cluster-chart", config=graph_config, className="dash-card"),
                    dcc.Graph(id="gender-chart", config=graph_config, className="dash-card"),
                    dcc.Graph(id="committee-chart", config=graph_config, className="dash-card"),
                ],
            ),
        ],
    )

    def empty_figure(title: str):
        figure = go.Figure()
        figure.update_layout(
            title=title,
            paper_bgcolor=PALETTE["paper"],
            plot_bgcolor=PALETTE["paper"],
            font={"family": "Inter, sans-serif", "color": PALETTE["ink"]},
            annotations=[{"text": "No data in this scope", "showarrow": False, "x": 0.5, "y": 0.5}],
            xaxis={"visible": False},
            yaxis={"visible": False},
        )
        return figure

    @dash.callback(
        Output("dash-scope", "children"),
        Output("dash-kpis", "children"),
        Output("status-chart", "figure"),
        Output("cluster-chart", "figure"),
        Output("gender-chart", "figure"),
        Output("committee-chart", "figure"),
        Input("dash-refresh", "n_intervals"),
    )
    def refresh(_tick):
        if not current_user.is_authenticated:
            abort(401)
        data = dashboard_series(current_user._get_current_object())
        counts = data["counts"]

        cards = [
            ("Villages", counts["villages"]),
            ("Committees", counts["committees"]),
            ("Action plans", counts["action_plans"]),
            ("Attendance", counts["attendance_entries"]),
            ("Special programs", counts["specials_entries"]),
            ("Special participants", counts["participants"]),
        ]
        kpis = [
            html.Article(
                className="dash-kpi",
                children=[html.Span(label), html.Strong(f"{value:,}")],
            )
            for label, value in cards
        ]

        status = data["status_breakdown"]
        if status:
            status_fig = go.Figure(
                go.Bar(
                    x=list(status.keys()),
                    y=list(status.values()),
                    marker_color=[
                        {
                            "On-time": PALETTE["green"],
                            "Early": PALETTE["saffron"],
                            "Postponed": PALETTE["clay"],
                            "Failure": "#7F2F2F",
                            "Scheduled": PALETTE["navy"],
                            "Due today": PALETTE["saffron"],
                            "Draft": "#8A8D8F",
                        }.get(key, PALETTE["navy"])
                        for key in status
                    ],
                    hovertemplate="%{x}: %{y}<extra></extra>",
                )
            )
            status_fig.update_layout(title="Action-plan status", showlegend=False)
        else:
            status_fig = empty_figure("Action-plan status")

        cluster = data["cluster_breakdown"]
        if cluster:
            cluster_fig = go.Figure(
                go.Pie(
                    labels=list(cluster.keys()),
                    values=list(cluster.values()),
                    hole=0.58,
                    marker_colors=[PALETTE["navy"], PALETTE["saffron"]],
                    textinfo="label+value",
                    hovertemplate="%{label}: %{value}<extra></extra>",
                )
            )
            cluster_fig.update_layout(title="Villages by cluster", showlegend=False)
        else:
            cluster_fig = empty_figure("Villages by cluster")

        gender = data["gender_distribution"]
        if sum(gender.values()):
            gender_fig = go.Figure(
                go.Bar(
                    x=list(gender.values()),
                    y=list(gender.keys()),
                    orientation="h",
                    marker_color=[PALETTE["navy"], PALETTE["saffron"]],
                    hovertemplate="%{y}: %{x}<extra></extra>",
                )
            )
            gender_fig.update_layout(title="Attendance by gender", showlegend=False)
        else:
            gender_fig = empty_figure("Attendance by gender")

        committees = data["committee_aggregates"]
        if committees:
            ordered = sorted(committees.items(), key=lambda item: item[1], reverse=True)[:12]
            committee_fig = go.Figure(
                go.Bar(
                    x=[item[1] for item in ordered],
                    y=[item[0] for item in ordered],
                    orientation="h",
                    marker_color=PALETTE["green"],
                    hovertemplate="%{y}: %{x}<extra></extra>",
                )
            )
            committee_fig.update_layout(title="Action plans by committee type", showlegend=False)
            committee_fig.update_yaxes(autorange="reversed")
        else:
            committee_fig = empty_figure("Action plans by committee type")

        for figure in (status_fig, cluster_fig, gender_fig, committee_fig):
            figure.update_layout(
                margin={"l": 48, "r": 24, "t": 60, "b": 48},
                paper_bgcolor=PALETTE["paper"],
                plot_bgcolor=PALETTE["paper"],
                font={"family": "Inter, sans-serif", "color": PALETTE["ink"]},
                title_font={"family": "Fraunces, serif", "size": 21},
                transition={"duration": 250},
            )

        profile = current_user.pc if current_user.role == Role.PC else None
        scope_label = profile.cluster.value if profile else "All clusters"
        return scope_label, kpis, status_fig, cluster_fig, gender_fig, committee_fig

    return dash
