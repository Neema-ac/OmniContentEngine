import json
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

SYSTEM_INSTRUCTION = """
You are an elite YouTube Growth Engineer, Algorithmic Strategist, and Visual Director.
Analyze the provided video script or rough notes to generate a production-grade distribution
and visual asset suite.

You MUST respond strictly in valid JSON adhering to the schema.
Ensure your outputs provide concrete, actionable director cues and high-signal analytics:
- Retention Analysis: Estimate a 7-point viewer retention curve (percentages, generally
  decreasing from ~100), pacing rating, and the single biggest drop-off risk.
- Production B-Roll Cue Sheet: 4-6 scene-by-scene cut instructions with audio and visual cues.
- Thumbnail Blueprints: exactly 3 distinct visual compositions. For each, provide a real hex
  color for `primary_hex` (the bold accent/background color) and `secondary_hex` (the
  complementary/shadow color) so the colors can be rendered into an actual image -
  do not just describe the colors in words for these two fields.
- High-CTR Platform Copy: platform-native assets for YouTube, Shorts/Reels, and X.
"""


class ThumbnailBlueprint(BaseModel):
    concept_name: str = Field(description="Concept angle, e.g. 'The Fear/Curiosity Gap'")
    overlay_text: str = Field(description="Max 3-4 punchy words to render over the image")
    sub_text: str = Field(description="Short supporting phrase, 2-5 words")
    color_palette: str = Field(description="Human-readable palette name, e.g. 'Crimson Red / Deep Obsidian'")
    primary_hex: str = Field(description="Primary accent hex color, e.g. '#E11D48'")
    secondary_hex: str = Field(description="Secondary/background hex color, e.g. '#111827'")
    focal_subject: str = Field(description="Subject, expression, framing, and lighting instructions")
    composition_layout: str = Field(description="Rule of thirds, left/right split, depth of field")


class ProductionCue(BaseModel):
    timestamp_estimate: str = Field(description="e.g. '00:00 - 00:05'")
    visual_broll: str = Field(description="Camera movement, screen recording, or stock asset cue")
    audio_sfx: str = Field(description="Sound effect, riser, whoosh, or silence pause")


class RetentionAudit(BaseModel):
    virality_score: int = Field(description="Overall virality index from 1 to 100")
    pacing_rating: str = Field(description="e.g. 'Fast', 'Optimal', 'Sluggish'")
    critical_dropoff_risk: str = Field(description="Where viewers are most likely to click away, and the fix")
    hook_strength_analysis: str = Field(description="Evaluation of the opening retention mechanism")
    estimated_retention_curve: list[int] = Field(
        description="Exactly 7 integers (0-100), estimated audience retention over the video"
    )


class AdvancedCampaign(BaseModel):
    retention_audit: RetentionAudit
    thumbnail_blueprints: list[ThumbnailBlueprint] = Field(description="Exactly 3 distinct thumbnail concepts")
    production_cues: list[ProductionCue] = Field(description="4-6 chronological scene/B-roll instructions")
    youtube_titles: list[str] = Field(description="3 high-CTR titles")
    viral_hook_variations: list[str] = Field(description="3 high-retention spoken hooks for Shorts/TikTok")
    x_thread_first_tweet: str = Field(description="Viral hook tweet designed for bookmarks")
    full_export_summary: str = Field(description="Executive recap of the strategy")


def analyze_and_engineer(source_text: str, pacing_goal: str = "High Velocity (Retention Focus)",
                          max_retries: int = 2) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to Replit Secrets (or a local .env file) and restart the app."
        )

    client = genai.Client(api_key=api_key)

    prompt = f"""
    Target Pacing / Velocity: {pacing_goal}

    Source Material:
    \"\"\"{source_text}\"\"\"

    Execute a full production teardown, retention audit, and thumbnail blueprint suite.
    """

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=AdvancedCampaign,
                    temperature=0.7,
                ),
            )
            parsed = json.loads(response.text)

            # Defensive clamp: keep the UI stable even if the model drifts from spec
            curve = parsed.get("retention_audit", {}).get("estimated_retention_curve", [])
            if len(curve) != 7:
                curve = (curve + [max(curve or [60], default=60)] * 7)[:7]
                parsed["retention_audit"]["estimated_retention_curve"] = curve
            parsed["thumbnail_blueprints"] = parsed.get("thumbnail_blueprints", [])[:3]

            return parsed
        except Exception as e:  # noqa: BLE001 - we want to retry on any transient failure
            last_error = e
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
                continue

    raise RuntimeError(f"Gemini generation failed after {max_retries + 1} attempt(s): {last_error}")