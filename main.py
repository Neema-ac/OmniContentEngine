import os
import traceback

from flask import Flask, jsonify, request, send_from_directory

import engine
from thumbnail_gen import generate_thumbnail_data_uri

app = Flask(__name__, static_folder="static", template_folder="templates")


@app.route("/")
def index():
    return send_from_directory(app.template_folder, "index.html")


@app.route("/api/generate", methods=["POST"])
def generate():
    payload = request.get_json(silent=True) or {}
    script = (payload.get("script") or "").strip()
    pacing = payload.get("pacing") or "High Velocity (Retention Focus)"

    if not script:
        return jsonify({"error": "Script text is required."}), 400
    if len(script) > 8000:
        return jsonify({"error": "Script is too long (max 8000 characters for this demo)."}), 400

    try:
        data = engine.analyze_and_engineer(script, pacing)
    except ValueError as e:
        # Missing/invalid API key - a config problem, not a user error
        return jsonify({"error": str(e)}), 500
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        return jsonify({"error": f"Generation failed, please try again. ({e})"}), 502

    # Render real downloadable PNG thumbnails server-side instead of only
    # returning a text description of what a thumbnail should look like.
    for bp in data.get("thumbnail_blueprints", []):
        try:
            bp["thumbnail_image"] = generate_thumbnail_data_uri(
                overlay_text=bp.get("overlay_text", "VIRAL HOOK"),
                sub_text=bp.get("sub_text", ""),
                primary_hex=bp.get("primary_hex", "#E11D48"),
                secondary_hex=bp.get("secondary_hex", "#111827"),
            )
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            bp["thumbnail_image"] = None

    return jsonify(data)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "gemini_key_configured": bool(os.getenv("GEMINI_API_KEY"))})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)