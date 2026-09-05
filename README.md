# OmniClip Pro — Creator Channel Automation Engine

Paste a raw script or set of notes and get back a full production suite:
a retention/drop-off audit, 3 real (downloadable) thumbnail images generated
from AI-designed blueprints, a B-roll/SFX cue sheet, and cross-platform copy
(YouTube titles, Shorts/Reels hooks, an X thread starter).

## How it's built

- **`main.py`** — Flask server. Serves the frontend and exposes `POST /api/generate`.
- **`engine.py`** — Calls Gemini (`gemini-2.5-flash`) with a Pydantic-constrained
  JSON schema so the model's output is always structured and typed. Retries
  transient failures automatically.
- **`thumbnail_gen.py`** — Takes the AI's thumbnail blueprint (colors, overlay
  text, layout) and renders an **actual PNG image** with Pillow — not just a
  text description of what a thumbnail should look like.
- **`templates/index.html`** — Single-file React (via CDN, no build step)
  frontend that calls the Flask backend.

The API key lives only on the server (Replit Secrets / `.env`) — it's never
sent to or stored in the browser.

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env   # then paste your real Gemini API key into .env
python3 main.py
```

Visit `http://localhost:8080`.

## Deploy on Replit

1. Import this repo into a new Replit (Python template).
2. Open **Tools → Secrets** and add `GEMINI_API_KEY` with your key. Do **not**
   put it in a committed `.env` file.
3. Click **Run** — Replit will use the `.replit` config to run `main.py`,
   which binds to `0.0.0.0` on the port Replit assigns.
4. Use the webview URL Replit gives you as your live demo link.

## Get a Gemini API key

Create one at https://aistudio.google.com/apikey (free tier is enough for a demo).

## Notes for judges

- Every run makes a real Gemini call — there is no mock/demo fallback.
- The 3 thumbnails on the "Visual Thumbnails" tab are real PNGs rendered
  server-side from the model's own color and layout choices, and are
  downloadable directly from the UI.