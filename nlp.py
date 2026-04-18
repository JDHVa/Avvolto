import re
from collections import Counter
import spacy
from langdetect import detect, LangDetectException
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from pysentimiento import create_analyzer

modelos_spacy: dict = {}
analizador_vader = None
analizador_pysentimiento: dict = {}


def cargar_spacy(idioma: str) -> spacy.Language | None:
    global modelos_spacy

    if idioma in modelos_spacy:
        return modelos_spacy[idioma]

    nombre_modelo = {"en": "en_core_web_sm", "es": "es_core_news_sm"}.get(idioma)
    if not nombre_modelo:
        return None
    try:
        modelo = spacy.load(nombre_modelo, disable=["parser", "ner"])
        modelos_spacy[idioma] = modelo
        return modelo
    except OSError:
        print(f"[nlp] spacy model '{nombre_modelo}' not found download the model")
        return None


def cargar_vader() -> SentimentIntensityAnalyzer:
    global analizador_vader
    if analizador_vader is None:
        analizador_vader = SentimentIntensityAnalyzer()
    return analizador_vader


def cargar_pysentimiento(idioma: str):
    global analizador_pysentimiento
    if idioma not in analizador_pysentimiento:
        try:
            analizador_pysentimiento[idioma] = create_analyzer(
                task="sentiment", lang=idioma
            )
        except:
            print(f"[nlp] pysentimiento could not found '{idioma}")

    return analizador_pysentimiento[idioma]


def detectar_idioma_chat(df) -> str:
    subset = df[~df["es_media"]]["contenido"].dropna()
    muestra = subset.sample(min(200, len(subset)), random_state=42).tolist()
    conteo = Counter()
    for texto in muestra:
        try:
            idioma = detect(texto)
            if idioma in ("es", "en"):
                conteo[idioma] += 1
        except LangDetectException:
            continue

    if not conteo:
        return "en"

    return conteo.most_common(1)[0][0]


STOPWORDS_EXTRA = {
    "en": {
        "ok",
        "okay",
        "yeah",
        "yep",
        "nope",
        "gonna",
        "wanna",
        "gotta",
        "lol",
        "lmao",
        "haha",
        "hahaha",
        "omg",
        "wtf",
        "idk",
        "imo",
        "btw",
        "tbh",
        "ngl",
        "fr",
        "bro",
        "dude",
        "yo",
        "hey",
    },
    "es": {
        "ok",
        "si",
        "no",
        "ya",
        "pues",
        "bueno",
        "vale",
        "claro",
        "oye",
        "ahi",
        "aca",
        "alla",
        "jaja",
        "jajaja",
        "jajajaja",
        "xd",
        "ajá",
        "mhm",
        "aja",
        "wey",
        "güey",
        "bro",
        "ps",
        "pos",
        "ntp",
        "neta",
        "o sea",
        "nd",
        "nel",
        "simon",
        "simón",
        "sale",
    },
}

# Made with gemini since idk all the emoji patron
PATRON_EMOJI = re.compile(
    "[\U0001f600-\U0001f64f"
    "\U0001f300-\U0001f5ff"
    "\U0001f680-\U0001f9ff"
    "\U00002600-\U000027bf"
    "\U0001fa00-\U0001fa6f"
    "\U0001fa70-\U0001faff"
    "\u2600-\u27bf]+",
    flags=re.UNICODE,
)


def limpiar_texto(texto: str) -> str:
    texto = re.sub(r"https?://\S+", "", texto)
    texto = PATRON_EMOJI.sub("", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def tokenizar_y_filtrar(textos: list[str], idioma: str = "en") -> list[str]:
    modelo = cargar_spacy(idioma)
    extra = STOPWORDS_EXTRA.get(idioma, set())

    tokens_limpios = []

    if modelo:
        for doc in modelo.pipe(textos, batch_size=64):
            for token in doc:
                if (
                    not token.is_stop
                    and not token.is_punct
                    and not token.like_url
                    and not token.is_space
                    and len(token.lemma_) > 2
                    and token.lemma_.lower() not in extra
                    and token.lemma_.isalpha()
                ):
                    tokens_limpios.append(token.lemma_.lower())
    else:
        for texto in textos:
            for palabra in texto.lower().split():
                palabra = re.sub(r"[^a-záéíóúüñ]", "", palabra)
                if len(palabra) > 2 and palabra not in extra:
                    tokens_limpios.append(palabra)
    return tokens_limpios


def palabras_significativas(
    df, idioma: str = "en", autor: str = None, top_n: int = 30
) -> list[tuple[str, int]]:
    subset = df[df["autor"] == autor] if autor else df
    subset = subset[~subset["es_media"]]
    textos = [limpiar_texto(t) for t in subset["contenido"].tolist()]
    textos = [t for t in textos if t]
    tokens = tokenizar_y_filtrar(textos, idioma=idioma)
    return Counter(tokens).most_common(top_n)


def sentimiento_en(texto: str) -> dict:
    vader = cargar_vader()
    scores = vader.polarity_scores(texto)

    return {
        "positivo": scores["pos"],
        "negativo": scores["neg"],
        "neutro": scores["neu"],
        "compuesto": scores["compound"],
    }


def sentimiento_es(texto: str) -> dict:
    analizador = cargar_pysentimiento("es")
    if analizador is None:
        return {"positivo": 0.0, "negativo": 0.0, "neutro": 1.0, "compuesto": 0.0}
    try:
        resultado = analizador.predict(texto)
        probas = resultado.probas
        compuesto = probas.get("POS", 0) - probas.get("NEG", 0)
        return {
            "positivo": probas.get("POS", 0.0),
            "negativo": probas.get("NEG", 0.0),
            "neutro": probas.get("NEU", 0.0),
            "compuesto": round(compuesto, 4),
        }
    except Exception:
        return {"positivo": 0.0, "negativo": 0.0, "neutro": 1.0, "compuesto": 0.0}


def analizar_sentimiento(texto: str, idioma: str = "en") -> dict:
    texto = limpiar_texto(texto)
    if not texto:
        return {"positivo": 0.0, "negativo": 0.0, "neutro": 1.0, "compuesto": 0.0}
    return sentimiento_en(texto) if idioma == "en" else sentimiento_es(texto)


def sentimiento_por_participante(df, idioma: str = "en") -> dict[str, dict]:
    resultado = {}
    subset = df[~df["es_media"] & (df["num_palabras"] >= 2)]

    for autor in subset["autor"].unique():
        mensaje_autor = subset[subset["autor"] == autor]["contenido"].tolist()
        scores = [analizar_sentimiento(t, idioma=idioma) for t in mensaje_autor]
        if not scores:
            continue
        promedio_compuesto = sum(s["compuesto"] for s in scores) / len(scores)
        positivos = sum(1 for s in scores if s["compuesto"] >= 0.045)
        negativos = sum(1 for s in scores if s["compuesto"] <= -0.045)
        neutros = len(scores) - positivos - negativos
        total = len(scores)

        if promedio_compuesto >= 0.045:
            tono = "positive"
        elif promedio_compuesto <= -0.045:
            tono = "negative"
        else:
            tono = "neutral"

        resultado[autor] = {
            "promedio_compuesto": round(promedio_compuesto, 4),
            "positivo_pct": round(positivos / total * 100, 1),
            "negativo_pct": round(negativos / total * 100, 1),
            "neutro_pct": round(neutros / total * 100, 1),
            "tono": tono,
        }
    return resultado


def analizar_nlp(df, resultado_analyzer: dict) -> dict:
    idioma = detectar_idioma_chat(df)
    palabras_chat = palabras_significativas(df, idioma=idioma, top_n=30)
    sentimientos = sentimiento_por_participante(df, idioma=idioma)

    palabras_por_autor = {
        autor: palabras_significativas(df, idioma=idioma, autor=autor, top_n=20)
        for autor in df["autor"].unique()
    }

    return {
        "idioma": idioma,
        "palabras_chat": palabras_chat,
        "palabras_por_autor": palabras_por_autor,
        "sentimientos": sentimientos,
    }


if __name__ == "__main__":
    import sys
    from parser import parsear_chat
    from analyzer import analizar, enriquecer_mensajes

    ruta = "".join(sys.argv[1:])
    resultado_parser = parsear_chat(ruta)
    resultado_anl = analizar(resultado_parser)
    df = resultado_anl["mensajes"]
    resultado_nlp = analizar_nlp(df, resultado_anl)

    print(f"Detected language {resultado_nlp['idioma']}")
    print(f" Top 15 messages more used")
    for palabra, count in resultado_nlp["palabras_chat"][:15]:
        print(f"{palabra:25s} {count}")

    print(f" Feelings by each person")
    for autor, info in resultado_nlp["sentimientos"].items():
        print(
            f"  {autor:30s} | tone: {info['tono']:8s} | score: {info['promedio_compuesto']:+.3f} | +{info['positivo_pct']}% -{info['negativo_pct']}% ~{info['neutro_pct']}%"
        )
