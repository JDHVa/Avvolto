import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import json

Colores = [
    "#00F5FF",
    "#BF5FFF",
    "#00FF9F",
    "#FF6B6B",
    "#FFD93D",
    "#FF8E53",
    "#4ECDC4",
    "#A8FF78",
]

fondo = "#050510"
fondo_panel = "rgba(255,255,255,0.04)"
color_texto = "#E0E0FF"
color_grid = "rgba(255,255,255,0.07)"
fuente = "Space Grotesk, sans-serif"

layout = dict(
    paper_bgcolor=fondo,
    plot_bgcolor=fondo,
    font=dict(family=fuente, color=color_texto, size=13),
    margin=dict(l=40, r=40, t=60, b=40),
    legend=dict(
        bgcolor="rgba(255,255,255,0.05)",
        bordercolor="rgba(255,255,255,0.1)",
        borderwidth=1,
    ),
)


def aplicar_layout(fig, titulo: str = "", alto: int = 400) -> go.Figure:
    fig.update_layout(
        **layout,
        title=dict(text=titulo, font=dict(size=16, color=color_texto), x=0.02),
        height=alto,
        xaxis=dict(gridcolor=color_grid, zeroline=False, showline=False),
        yaxis=dict(gridcolor=color_grid, zeroline=False, showline=False),
    )
    return fig


def color_autor(index: int) -> str:
    return Colores[index % len(Colores)]


def grafica_participante(df_stats: pd.DataFrame) -> str:
    color = [color_autor(i) for i in range(len(df_stats))]

    fig = go.Figure(
        go.Pie(
            labels=df_stats["autor"],
            values=df_stats["total_mensajes"],
            hole=0.6,
            marker=dict(colors=color, line=dict(color=fondo, width=3)),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>%{value} messages<br>%{percent}<extra></extra>",
        )
    )
    fig.add_annotation(
        text=f"<b>{df_stats['total_mensajes'].sum():,}</b><br><span style='font-size:11px'>messages</span>",
        x=0.5,
        y=0.5,
        font=dict(size=18, color=color_texto),
        showarrow=False,
    )

    aplicar_layout(fig, "Message Share")
    fig.update_layout(showlegend=True)
    return fig.to_json()


def grafica_timeline(timeline_diario: pd.DataFrame) -> str:
    fig = go.Figure(
        go.Scatter(
            x=timeline_diario["fecha_solo"],
            y=timeline_diario["total_mensajes"],
            mode="lines",
            fill="tozeroy",
            line=dict(color=Colores[0], width=2),
            fillcolor="rgba(0,245,255,0.08)",
            hovertemplate="<b>%{x}</b><br>%{y} messages<extra></extra>",
        )
    )
    aplicar_layout(fig, "Activity Over the time", alto=300)
    return fig.to_json()


def grafica_horas(timeline_hora: pd.DataFrame) -> str:
    horas = timeline_hora["hora"].tolist()
    totales = timeline_hora["total_mensajes"].tolist()

    colores_barra = []

    for h in horas:
        if 6 <= h < 12:
            colores_barra.append(Colores[4])
        elif 12 <= h < 19:
            colores_barra.append(Colores[0])
        elif 19 <= h < 24:
            colores_barra.append(Colores[2])
        else:
            colores_barra.append(Colores[1])

    fig = go.Figure(
        go.Bar(
            x=horas,
            y=totales,
            marker_color=colores_barra,
            hovertemplate="<b>%{x}:00</b><br>%{y} messages<extra></extra>",
        )
    )

    aplicar_layout(fig, "Activity by hour", alto=300)
    fig.update_layout(
        xaxis=dict(tickmode="linear", tick0=0, dtick=2, gridcolor=color_grid),
    )
    return fig.to_json()


def grafica_semana(timeline_semana: pd.DataFrame) -> str:
    dias = timeline_semana["dia_semana"].tolist()
    totales = timeline_semana["total_mensajes"].tolist()

    fig = go.Figure(
        go.Bar(
            x=totales,
            y=dias,
            orientation="h",
            marker=dict(
                color=totales,
                colorscale=[[0, "rgba(0,245,255,0.2)"], [1, Colores[0]]],
                showscale=False,
            ),
            hovertemplate="<b>%{y}</b><br>%{x} messages<extra></extra>",
        )
    )
    aplicar_layout(fig, "Activity by Weekday", alto=320)
    return fig.to_json()


def grafica_tiempos_respuesta(df_stats: pd.DataFrame) -> str:
    df_validos = df_stats[df_stats["promedio_respuesta"].notna()].copy()
    df_validos = df_validos.sort_values("promedio_respuesta")

    colors = [color_autor(i) for i in range(len(df_validos))]

    def formatear_minutos(minutos: float) -> str:
        if minutos < 60:
            return f"{minutos:.0f} min"
        return f"{minutos / 60:.1f} h"

    etiquetas = [formatear_minutos(m) for m in df_validos["promedio_respuesta"]]

    fig = go.Figure(
        go.Bar(
            x=df_validos["promedio_respuesta"],
            y=df_validos["autor"],
            orientation="h",
            marker_color=colors,
            text=etiquetas,
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Median response: %{text}<extra></extra>",
        )
    )

    aplicar_layout(fig, "Median Response Time", alto=max(360, len(df_validos) * 60))
    return fig.to_json()


def graficar_longitud_mensajes(df_stats: pd.DataFrame) -> str:
    df_sorted = df_stats.sort_values("promedio_palabras", ascending=False)
    colors = [color_autor(i) for i in range(len(df_sorted))]

    fig = go.Figure(
        go.Bar(
            x=df_sorted["autor"],
            y=df_sorted["promedio_palabras"],
            marker_color=colors,
            text=[f"{v:.1f} words" for v in df_sorted["promedio_palabras"]],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>%{y:.1f} words/msg<extra></extra>",
        )
    )

    aplicar_layout(fig, "Avg Words per Message", alto=350)
    return fig.to_json()


def grafica_emojis(emoji_top: list[tuple[str, int]]) -> str:
    if not emoji_top:
        return None

    emojis = [e for e, _ in emoji_top]
    counts = [c for e, c in emoji_top]

    fig = go.Figure(
        go.Bar(
            x=counts,
            y=emojis,
            orientation="h",
            marker=dict(
                color=counts,
                colorscale=[[0, "rgba(191,95,255,0.3)"], [1, Colores[1]]],
                showscale=False,
            ),
            hovertemplate="%{y}  ×%{x}<extra></extra>",
        )
    )
    aplicar_layout(fig, "Most emojis used", alto=max(400, len(emojis) * 40))
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return fig.to_json()


def grafica_palabras(
    palabras_top: list[tuple[str, int]], titulo: str = "Top Words"
) -> str:
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
                colorscale=[[0, "rgba(0,255,159,0.2)"], [1, Colores[2]]],
                showscale=False,
            ),
            hovertemplate="<b>%{y}</b>  ×%{x}<extra></extra>",
        )
    )

    aplicar_layout(fig, titulo, alto=max(350, len(palabras) * 28))
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return fig.to_json()


def grafica_sentimiento(sentimientos: dict) -> str:
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
            marker_color=Colores[2],
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
            marker_color=Colores[3],
            hovertemplate="<b>%{x}</b><br>Negative: %{y:.1f}%<extra></extra>",
        )
    )

    aplicar_layout(fig, "Message Sentiment", alto=360)
    fig.update_layout(barmode="stack")
    return fig.to_json()


def generar_graficas(resultado_analyzer: dict, resultado_nlp: dict) -> dict:
    stats = resultado_analyzer["stats"]
    sentimientos = resultado_nlp.get("sentimientos", {})
    palabras_chat = resultado_nlp.get("palabras_chat", {})
    emojis_top = resultado_analyzer.get("emojis_top", {})
    graficas = {
        "participacion": grafica_participante(stats),
        "timeline": grafica_timeline(resultado_analyzer["timeline_diario"]),
        "horas": grafica_horas(resultado_analyzer["timeline_hora"]),
        "semana": grafica_semana(resultado_analyzer["timeline_semana"]),
        "respuesta": grafica_tiempos_respuesta(stats),
        "longitud": graficar_longitud_mensajes(stats),
        "emojis": grafica_emojis(emojis_top),
        "palabras": grafica_palabras(palabras_chat, titulo="Top Meaningful Words"),
        "sentimiento": grafica_sentimiento(sentimientos),
    }

    palabras_por_autor = resultado_nlp.get("palabras_por_autor", {})
    for autor, palabras in palabras_por_autor.items():
        clave = f"palabras_{autor.lower().replace(' ', '_')}"
        graficas[clave] = grafica_palabras(palabras, titulo=f"Top Words — {autor}")

    return {k: v for k, v in graficas.items() if v is not None}


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
