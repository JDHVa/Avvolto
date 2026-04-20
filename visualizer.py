import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import json


# ---------------------------------------------------------------------------
# Design tokens — dark neon aesthetic consistent across all charts
# ---------------------------------------------------------------------------

COLORES_NEON = [
    "#00F5FF",  # cyan
    "#BF5FFF",  # purple
    "#00FF9F",  # green
    "#FF6B6B",  # coral
    "#FFD93D",  # yellow
    "#FF8E53",  # orange
    "#4ECDC4",  # teal
    "#A8FF78",  # lime
]

FONDO = "#050510"
FONDO_PANEL = "rgba(255,255,255,0.04)"
COLOR_TEXTO = "#E0E0FF"
COLOR_GRID = "rgba(255,255,255,0.07)"
FUENTE = "Space Grotesk, sans-serif"

LAYOUT_BASE = dict(
    paper_bgcolor=FONDO,
    plot_bgcolor=FONDO,
    font=dict(family=FUENTE, color=COLOR_TEXTO, size=13),
    margin=dict(l=40, r=40, t=60, b=40),
    legend=dict(
        bgcolor="rgba(255,255,255,0.05)",
        bordercolor="rgba(255,255,255,0.1)",
        borderwidth=1,
    ),
)


def _aplicar_layout(fig, titulo: str = "", alto: int = 400) -> go.Figure:
    """Apply the base dark layout to any figure."""
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text=titulo, font=dict(size=16, color=COLOR_TEXTO), x=0.02),
        height=alto,
        xaxis=dict(gridcolor=COLOR_GRID, zeroline=False, showline=False),
        yaxis=dict(gridcolor=COLOR_GRID, zeroline=False, showline=False),
    )
    return fig


def _color_autor(index: int) -> str:
    return COLORES_NEON[index % len(COLORES_NEON)]


# ---------------------------------------------------------------------------
# Chart 1 — Message share donut
# ---------------------------------------------------------------------------


def grafica_participacion(df_stats: pd.DataFrame) -> str:
    """Donut chart showing each participant's message share."""
    colores = [_color_autor(i) for i in range(len(df_stats))]

    fig = go.Figure(
        go.Pie(
            labels=df_stats["autor"],
            values=df_stats["total_mensajes"],
            hole=0.6,
            marker=dict(colors=colores, line=dict(color=FONDO, width=3)),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>%{value} messages<br>%{percent}<extra></extra>",
        )
    )

    fig.add_annotation(
        text=f"<b>{df_stats['total_mensajes'].sum():,}</b><br><span style='font-size:11px'>messages</span>",
        x=0.5,
        y=0.5,
        font=dict(size=18, color=COLOR_TEXTO),
        showarrow=False,
    )

    _aplicar_layout(fig, "Message Share")
    fig.update_layout(showlegend=True)
    return fig.to_json()


# ---------------------------------------------------------------------------
# Chart 2 — Activity timeline (messages per day)
# ---------------------------------------------------------------------------


def grafica_timeline(timeline_diario: pd.DataFrame) -> str:
    """Area chart of messages per day over the full chat history."""
    fig = go.Figure(
        go.Scatter(
            x=timeline_diario["fecha_solo"],
            y=timeline_diario["total_mensajes"],
            mode="lines",
            fill="tozeroy",
            line=dict(color=COLORES_NEON[0], width=2),
            fillcolor="rgba(0,245,255,0.08)",
            hovertemplate="<b>%{x}</b><br>%{y} messages<extra></extra>",
        )
    )

    _aplicar_layout(fig, "Activity Over Time", alto=300)
    return fig.to_json()


# ---------------------------------------------------------------------------
# Chart 3 — Messages by hour of day (bar)
# ---------------------------------------------------------------------------


def grafica_horas(timeline_hora: pd.DataFrame) -> str:
    """Bar chart showing chat activity by hour (0–23)."""
    horas = timeline_hora["hora"].tolist()
    totales = timeline_hora["total_mensajes"].tolist()

    # Color bars by time block
    colores_barra = []
    for h in horas:
        if 6 <= h < 12:
            colores_barra.append(COLORES_NEON[4])  # yellow = morning
        elif 12 <= h < 19:
            colores_barra.append(COLORES_NEON[0])  # cyan = afternoon
        elif 19 <= h < 24:
            colores_barra.append(COLORES_NEON[2])  # green = night
        else:
            colores_barra.append(COLORES_NEON[1])  # purple = late night

    fig = go.Figure(
        go.Bar(
            x=horas,
            y=totales,
            marker_color=colores_barra,
            hovertemplate="<b>%{x}:00</b><br>%{y} messages<extra></extra>",
        )
    )

    _aplicar_layout(fig, "Activity by Hour", alto=300)
    fig.update_layout(
        xaxis=dict(tickmode="linear", tick0=0, dtick=2, gridcolor=COLOR_GRID),
    )
    return fig.to_json()


# ---------------------------------------------------------------------------
# Chart 4 — Activity by weekday
# ---------------------------------------------------------------------------


def grafica_semana(timeline_semana: pd.DataFrame) -> str:
    """Horizontal bar chart of messages by day of week."""
    dias = timeline_semana["dia_semana"].tolist()
    totales = timeline_semana["total_mensajes"].tolist()

    fig = go.Figure(
        go.Bar(
            x=totales,
            y=dias,
            orientation="h",
            marker=dict(
                color=totales,
                colorscale=[[0, "rgba(0,245,255,0.2)"], [1, COLORES_NEON[0]]],
                showscale=False,
            ),
            hovertemplate="<b>%{y}</b><br>%{x} messages<extra></extra>",
        )
    )

    _aplicar_layout(fig, "Activity by Weekday", alto=320)
    return fig.to_json()


# ---------------------------------------------------------------------------
# Chart 5 — Average response time per participant
# ---------------------------------------------------------------------------


def grafica_tiempos_respuesta(df_stats: pd.DataFrame) -> str:
    """Horizontal bar chart of median response times."""
    df_validos = df_stats[df_stats["promedio_respuesta"].notna()].copy()
    df_validos = df_validos.sort_values("promedio_respuesta")

    colores = [_color_autor(i) for i in range(len(df_validos))]

    def _formatear_minutos(minutos: float) -> str:
        if minutos < 60:
            return f"{minutos:.0f} min"
        return f"{minutos / 60:.1f} h"

    etiquetas = [_formatear_minutos(m) for m in df_validos["promedio_respuesta"]]

    fig = go.Figure(
        go.Bar(
            x=df_validos["promedio_respuesta"],
            y=df_validos["autor"],
            orientation="h",
            marker_color=colores,
            text=etiquetas,
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Median response: %{text}<extra></extra>",
        )
    )

    _aplicar_layout(fig, "Median Response Time", alto=max(300, len(df_validos) * 60))
    return fig.to_json()


# ---------------------------------------------------------------------------
# Chart 6 — Average message length per participant
# ---------------------------------------------------------------------------


def grafica_longitud_mensajes(df_stats: pd.DataFrame) -> str:
    """Bar chart of average words per message per participant."""
    df_sorted = df_stats.sort_values("promedio_palabras", ascending=False)
    colores = [_color_autor(i) for i in range(len(df_sorted))]

    fig = go.Figure(
        go.Bar(
            x=df_sorted["autor"],
            y=df_sorted["promedio_palabras"],
            marker_color=colores,
            text=[f"{v:.1f} words" for v in df_sorted["promedio_palabras"]],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>%{y:.1f} words/msg<extra></extra>",
        )
    )

    _aplicar_layout(fig, "Avg Words per Message", alto=350)
    return fig.to_json()


# ---------------------------------------------------------------------------
# Chart 7 — Top emojis
# ---------------------------------------------------------------------------


def grafica_emojis(emojis_top: list[tuple[str, int]]) -> str:
    """Horizontal bar chart of the most used emojis."""
    if not emojis_top:
        return None

    emojis = [e for e, _ in emojis_top]
    counts = [c for _, c in emojis_top]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=emojis,
            orientation="h",
            marker=dict(
                color=counts,
                colorscale=[[0, "rgba(191,95,255,0.3)"], [1, COLORES_NEON[1]]],
                showscale=False,
            ),
            hovertemplate="%{y}  ×%{x}<extra></extra>",
        )
    )

    _aplicar_layout(fig, "Most Used Emojis", alto=max(300, len(emojis) * 40))
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return fig.to_json()


# ---------------------------------------------------------------------------
# Chart 8 — Top words (word frequency bar)
# ---------------------------------------------------------------------------


def grafica_palabras(
    palabras_top: list[tuple[str, int]], titulo: str = "Top Words"
) -> str:
    """Horizontal bar chart of most frequent meaningful words."""
    if not palabras_top:
        return None

    palabras = [p for p, _ in palabras_top[:20]]
    counts = [c for _, c in palabras_top[:20]]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=palabras,
            orientation="h",
            marker=dict(
                color=counts,
                colorscale=[[0, "rgba(0,255,159,0.2)"], [1, COLORES_NEON[2]]],
                showscale=False,
            ),
            hovertemplate="<b>%{y}</b>  ×%{x}<extra></extra>",
        )
    )

    _aplicar_layout(fig, titulo, alto=max(350, len(palabras) * 28))
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return fig.to_json()


# ---------------------------------------------------------------------------
# Chart 9 — Sentiment per participant
# ---------------------------------------------------------------------------


def grafica_sentimiento(sentimientos: dict) -> str:
    """Stacked bar chart of positive / neutral / negative % per participant."""
    if not sentimientos:
        return None

    autores = list(sentimientos.keys())
    positivos = [sentimientos[a]["positivo_pct"] for a in autores]
    neutros = [sentimientos[a]["neutro_pct"] for a in autores]
    negativos = [sentimientos[a]["negativo_pct"] for a in autores]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Positive",
            x=autores,
            y=positivos,
            marker_color=COLORES_NEON[2],
            hovertemplate="<b>%{x}</b><br>Positive: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Neutral",
            x=autores,
            y=neutros,
            marker_color="rgba(255,255,255,0.2)",
            hovertemplate="<b>%{x}</b><br>Neutral: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Negative",
            x=autores,
            y=negativos,
            marker_color=COLORES_NEON[3],
            hovertemplate="<b>%{x}</b><br>Negative: %{y:.1f}%<extra></extra>",
        )
    )

    _aplicar_layout(fig, "Message Sentiment", alto=380)
    fig.update_layout(barmode="stack")
    return fig.to_json()


# ---------------------------------------------------------------------------
# Main entry point — builds all charts and returns them as JSON strings
# ---------------------------------------------------------------------------


def generar_graficas(resultado_analyzer: dict, resultado_nlp: dict) -> dict:
    """
    Generate all Plotly charts from analyzer and NLP results.
    Returns a dict of chart name -> JSON string (ready to pass to Plotly.react()).
    """
    stats = resultado_analyzer["stats"]
    sentimientos = resultado_nlp.get("sentimientos", {})
    palabras_chat = resultado_nlp.get("palabras_chat", [])
    emojis_top = resultado_analyzer.get("emojis_top", [])

    graficas = {
        "participacion": grafica_participacion(stats),
        "timeline": grafica_timeline(resultado_analyzer["timeline_diario"]),
        "horas": grafica_horas(resultado_analyzer["timeline_hora"]),
        "semana": grafica_semana(resultado_analyzer["timeline_semana"]),
        "respuesta": grafica_tiempos_respuesta(stats),
        "longitud": grafica_longitud_mensajes(stats),
        "emojis": grafica_emojis(emojis_top),
        "palabras": grafica_palabras(palabras_chat, titulo="Top Meaningful Words"),
        "sentimiento": grafica_sentimiento(sentimientos),
    }

    # Per-participant word charts
    palabras_por_autor = resultado_nlp.get("palabras_por_autor", {})
    for autor, palabras in palabras_por_autor.items():
        clave = f"palabras_{autor.lower().replace(' ', '_')}"
        graficas[clave] = grafica_palabras(palabras, titulo=f"Top Words — {autor}")

    # Remove None entries (charts with no data)
    return {k: v for k, v in graficas.items() if v is not None}


# ---------------------------------------------------------------------------
# Quick test — python visualizer.py <path_to_chat.txt>
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from parser import parsear_chat
    from analyzer import analizar
    from nlp import analizar_nlp

    ruta = " ".join(sys.argv[1:])
    resultado_parser = parsear_chat(ruta)
    resultado_anl = analizar(resultado_parser)
    resultado_nlp = analizar_nlp(resultado_anl["mensajes"], resultado_anl)
    graficas = generar_graficas(resultado_anl, resultado_nlp)

    print(f"\nCharts generated: {list(graficas.keys())}")
    print(f"\nAll charts serialized to JSON successfully.")

    # Dump a quick HTML preview to verify charts visually
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
    <style>
        body { background: #050510; color: #E0E0FF; font-family: 'Space Grotesk', sans-serif; }
        .chart { margin: 20px auto; max-width: 900px; }
    </style>
</head>
<body>
"""
    for nombre, json_data in graficas.items():
        html += f'<div class="chart" id="{nombre}"></div>\n'
        html += f'<script>Plotly.react("{nombre}", {json_data})</script>\n'

    html += "</body></html>"

    with open("preview.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("\nPreview saved to preview.html — open it in your browser.")
