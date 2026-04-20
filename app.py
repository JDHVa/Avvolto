import os
import json
import math
import tempfile
from pathlib import Path

import numpy as np
from flask import Flask, request, jsonify, render_template
from flask import current_app

from parser import parsear_chat
from analyzer import analizar
from nlp import analizar_nlp
from visualizer import generar_graficas


def _sanitizar(obj):
    """Recursively convert numpy/date types to JSON-safe Python natives."""
    if isinstance(obj, dict):
        return {k: _sanitizar(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitizar(i) for i in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        f = float(obj)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB max upload
EXTENSIONES_PERMITIDAS = {".txt"}


def _extension_valida(nombre: str) -> bool:
    return Path(nombre).suffix.lower() in EXTENSIONES_PERMITIDAS


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Receives a .txt file upload, runs the full pipeline, and returns JSON
    with all stats, personalities, and chart data.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    archivo = request.files["file"]

    if archivo.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not _extension_valida(archivo.filename):
        return (
            jsonify({"error": "Only .txt files exported from WhatsApp are supported."}),
            400,
        )

    # Save to a temp file so all modules can read it normally
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        archivo.save(tmp.name)
        ruta_tmp = tmp.name

    try:
        # --- Pipeline ---
        resultado_parser = parsear_chat(ruta_tmp)
        resultado_anl = analizar(resultado_parser)
        resultado_nlp = analizar_nlp(resultado_anl["mensajes"], resultado_anl)
        graficas = generar_graficas(resultado_anl, resultado_nlp)

        # --- Build response payload ---
        stats_json = resultado_anl["stats"].to_dict(orient="records")

        fecha_inicio, fecha_fin = resultado_anl["rango_fechas"]

        respuesta = _sanitizar(
            {
                "tipo_chat": resultado_anl["tipo_chat"],
                "participantes": resultado_anl["participantes"],
                "total_mensajes": resultado_anl["total_mensajes"],
                "fecha_inicio": fecha_inicio.strftime("%b %d, %Y"),
                "fecha_fin": fecha_fin.strftime("%b %d, %Y"),
                "idioma": resultado_nlp["idioma"],
                "stats": stats_json,
                "personalidades": resultado_anl["personalidades"],
                "sentimientos": resultado_nlp["sentimientos"],
                "graficas": graficas,
            }
        )

        from flask import Response

        return Response(json.dumps(respuesta), status=200, mimetype="application/json")

    except ValueError as e:
        return jsonify({"error": str(e)}), 422

    except Exception as e:
        app.logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
        return (
            jsonify({"error": "An unexpected error occurred. Please try again."}),
            500,
        )

    finally:
        # Always clean up the temp file
        try:
            os.unlink(ruta_tmp)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
