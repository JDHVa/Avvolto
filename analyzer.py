import re
import pandas as pd
import numpy as np
from collections import Counter

PATRONE_EMOJI = re.compile(
    "[\U0001f600-\U0001f64f"
    "\U0001f300-\U0001f5ff"
    "\U0001f680-\U0001f9ff"
    "\U00002600-\U000027bf"
    "\U0001fa00-\U0001fa6f"
    "\U0001fa70-\U0001faff"
    "\u2600-\u27bf]+",
    flags=re.UNICODE,
)


def extraer_emojis(texto: str) -> list[str]:
    return PATRONE_EMOJI.findall(texto)


def contar_palabras(texto: str) -> int:
    texto = PATRONE_EMOJI.sub("", texto).strip()
    return len(texto.split()) if texto else 0


def enriquecer_mensajes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["num_palabras"] = df["contenido"].apply(contar_palabras)
    df["emojis"] = df["contenido"].apply(extraer_emojis)
    df["num_emojis"] = df["emojis"].apply(len)
    df["es_solo_emoji"] = df.apply(
        lambda r: r["num_emojis"] > 0 and r["num_palabras"] == 0 and not r["es_media"],
        axis=1,
    )

    def bloque_hora(hora: int) -> str:
        if 0 <= hora < 6:
            return "Morning"
        elif 6 <= hora < 12:
            return "Afternoon"
        elif 12 <= hora < 18:
            return "Evening"
        else:
            return "Night"

    df["hora_bloque"] = df["hora"].apply(bloque_hora)
    return df


def calcular_tiempos_respuesta(df: pd.DataFrame) -> pd.DataFrame:
    registros = []
    for i in range(1, len(df)):
        actual = df.iloc[i]
        anterior = df.iloc[i - 1]
        if actual["autor"] != anterior["autor"]:
            delta = (actual["fecha"] - anterior["fecha"]).total_seconds() / 60
            if 0 < delta <= 1440:
                registros.append(
                    {
                        "autor": actual["autor"],
                        "minutos_respuesta": delta,
                        "fecha": actual["fecha"],
                    }
                )
    return pd.DataFrame(registros)


def estadisticas_por_persona(
    df: pd.DataFrame, df_respuestas: pd.DataFrame
) -> pd.DataFrame:
    stats = []
    for autor in df["autor"].unique():
        mensajes_autor = df[df["autor"] == autor]
        respuestas_autor = (
            df_respuestas[df_respuestas["autor"] == autor]
            if not df_respuestas.empty
            else pd.DataFrame()
        )

        hora_favorita = (
            mensajes_autor["hora"].mode().iloc[0] if not mensajes_autor.empty else None
        )
        dia_favorito = (
            mensajes_autor["dia_semana"].mode().iloc[0]
            if not mensajes_autor.empty
            else None
        )
        promedio_respuesta = (
            respuestas_autor["minutos_respuesta"].median()
            if not respuestas_autor.empty
            else np.nan
        )

        stats.append(
            {
                "autor": autor,
                "total_mensajes": len(mensajes_autor),
                "total_palabras": mensajes_autor["num_palabras"].sum(),
                "promedio_palabras": (round(mensajes_autor["num_palabras"].mean(), 1)),
                "total_emojis": mensajes_autor["num_emojis"].sum(),
                "mensajes_media": mensajes_autor["es_media"].sum(),
                "hora_favorita": hora_favorita,
                "dia_favorito": dia_favorito,
                "hora_favorita": hora_favorita,
                "dia_favorito": dia_favorito,
                "promedio_respuesta": (
                    round(promedio_respuesta, 1)
                    if not np.isnan(promedio_respuesta)
                    else None
                ),
            }
        )

        df_stats = pd.DataFrame(stats)
        df_stats["porcentaje_mensajes"] = (
            df_stats["total_mensajes"] / df_stats["total_mensajes"].sum() * 100
        ).round(1)

    return df_stats.sort_values("total_mensajes", ascending=False).reset_index(
        drop=True
    )


PERSONALIDADES = {
    "el_rapido": "Always Quick to Reply",
    "el_fantasma": "The Ghost",
    "el_novelista": "The Novelist",
    "el_lacónico": "Man of Few Words",
    "el_comico": "The Comedian",
    "el_noctambulo": "Night Owl",
    "el_madrugador": "Early Bird",
    "el_iniciador": "The Initiator",
    "el_silencioso": "The Lurker",
}


def detectar_personalidad(
    df: pd.DataFrame, df_stats: pd.DataFrame, df_respuestas: pd.DataFrame
) -> dict[str, dict]:
    personalidad_asignada = {}
    mediana_respuesta = (
        df_respuestas["minutos_respuesta"].median() if not df_respuestas.empty else None
    )
    mediana_palabras = df_stats["promedio_palabras"].median()

    df_sorted = df.sort_values("fecha").reset_index(drop=True)
    inicios = [0]

    for i in range(1, len(df_sorted)):
        gap = (
            df_sorted.iloc[i]["fecha"] - df_sorted.iloc[i - 1]["fecha"]
        ).total_seconds() / 3600
        if gap >= 1:
            inicios.append(i)
    autores_inicio = df_sorted.iloc[inicios]["autor"].value_counts()

    for _, fila in df_stats.iterrows():
        autor = fila["autor"]
        scores = {}

        if mediana_respuesta and fila["promedio_respuesta"] is not None:
            ratio_respusta = fila["promedio_respuesta"] / mediana_respuesta
            if ratio_respusta < 0.4:
                scores["el_rapido"] = 3
            elif ratio_respusta > 3.0:
                scores["el_fantasma"] = 3

        if mediana_palabras > 0:
            ratio_palabras = fila["promedio_palabras"] / mediana_palabras
            if ratio_palabras > 1.8:
                scores["el_novelista"] = 2
            elif ratio_palabras < 0.4:
                scores["el_lacónico"] = 2

        if fila["total_mensajes"] > 0:
            ratio_emojis = fila["total_emojis"] / fila["total_mensajes"]
            if ratio_emojis > 1.5:
                scores["el_comediante"] = 2

        mensajes_autor = df[df["autor"] == autor]
        if not mensajes_autor.empty:
            hora_pico = mensajes_autor["hora"].value_counts().idxmax()
            bloques = mensajes_autor["hora_bloque"].value_counts(normalize=True)
            if bloques.get("laten_night", 0) > 0.3:
                scores["el_noctambulo"] = 2
            elif bloques.get("morning", 0) > 0.3 and hora_pico < 9:
                scores["el_madrugador"] = 2

        if autor in autores_inicio.index:
            proporcion_inicios = autores_inicio[autor] / len(inicios)
            if proporcion_inicios > 0.4:
                scores["el_iniciador"] = 2

        if fila["porcentaje_mensajes"] < 5:
            scores["el_silencioso"] = 1

        if scores:
            clave = max(scores, key=scores.get)
        else:
            clave = "el_lacónico"

        personalidad_asignada[autor] = {
            "clave": clave,
            "etiqueta": PERSONALIDADES[clave],
        }

    return personalidad_asignada


def actividad_por_dia(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("fecha_solo")
        .size()
        .reset_index(name="total_mensajes")
        .sort_values("fecha_solo")
    )


def actividad_por_hora(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("hora")
        .size()
        .reindex(range(24), fill_value=0)
        .reset_index(name="total_mensajes")
    )


def actividad_por_dia_semana(df: pd.DataFrame) -> pd.DataFrame:
    orden = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    return (
        df.groupby("dia_semana")
        .size()
        .reindex(orden, fill_value=0)
        .reset_index(name="total_mensajes")
    )


def palabras_frecuentes(
    df: pd.DataFrame, autor: str = None, top_n: int = 20
) -> list[tuple[str, int]]:
    subset = df[df["autor"] == autor] if autor else df
    subset = subset[~subset["es_media"]]

    texto_completo = " ".join(subset["contenido"].tolist()).lower()
    texto_limpio = PATRONE_EMOJI.sub("", texto_completo)
    palabras = re.findall(r"\b[a-záéíóúüñ]{2,}\b", texto_limpio)

    return Counter(palabras).most_common(top_n)


def emojis_frecuentes(
    df: pd.DataFrame, autor: str = None, top_n: int = 10
) -> list[tuple[str, int]]:
    subset = df[df["autor"] == autor] if autor else df
    todos = [emoji for lista in subset["emojis"] for emoji in lista]
    return Counter(todos).most_common(top_n)


def analizar(resultado_parser: dict) -> dict:

    df = resultado_parser["mensajes"]
    participantes = resultado_parser["participantes"]
    tipo_chat = resultado_parser["tipo_chat"]

    df = enriquecer_mensajes(df)

    df_respuestas = calcular_tiempos_respuesta(df)

    df_stats = estadisticas_por_persona(df, df_respuestas)
    personalidades = detectar_personalidad(df, df_stats, df_respuestas)

    return {
        "tipo_chat": tipo_chat,
        "participantes": participantes,
        "total_mensajes": resultado_parser["total_mensajes"],
        "rango_fechas": resultado_parser["rango_fechas"],
        "mensajes": df,
        "stats": df_stats,
        "respuestas": df_respuestas,
        "personalidades": personalidades,
        "timeline_diario": actividad_por_dia(df),
        "timeline_hora": actividad_por_hora(df),
        "timeline_semana": actividad_por_dia_semana(df),
        "palabras_top": palabras_frecuentes(df, top_n=30),
        "emojis_top": emojis_frecuentes(df, top_n=10),
    }


if __name__ == "__main__":
    import sys
    from parser import parsear_chat

    ruta = " ".join(sys.argv[1:])
    resultado_parser = parsear_chat(ruta)
    resultado = analizar(resultado_parser)

    print(f"\n=== STATS PER PARTICIPANT ===")
    print(resultado["stats"].to_string())

    print(f"\n=== PERSONALITIES ===")
    for autor, info in resultado["personalidades"].items():
        print(f"  {autor:30s} -> {info['etiqueta']}")

    print(f"\n=== TOP 10 WORDS ===")
    for palabra, count in resultado["palabras_top"][:10]:
        print(f"  {palabra:20s} {count}")

    print(f"\n=== TOP EMOJIS ===")
    for emoji, count in resultado["emojis_top"]:
        print(f"  {emoji}  {count}")
