import base64
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()


def image_to_data_url(image_path: str) -> str:
    """
    Converts a local image to a data URL (base64).
    This avoids needing to host the image somewhere public.
    """
    p = Path(image_path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Normalize format a bit (helps with odd formats / huge images)
    img = Image.open(p).convert("RGB")
    img.thumbnail((1600, 1600))  # keep detail, reduce size
    tmp_path = p.with_suffix(".tmp.jpg")
    img.save(tmp_path, format="JPEG", quality=90)

    b64 = base64.b64encode(tmp_path.read_bytes()).decode("utf-8")
    tmp_path.unlink(missing_ok=True)
    return f"data:image/jpeg;base64,{b64}"


def main(image_path: str):
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
    )

    schema = {
        "input_type": "place_photo | not_a_place | ambiguous",
        "place_guess": {
            "name": "string | null",
            "city": "string | null",
            "country": "string | null"
        },
        "confidence": "number between 0 and 1",
        "what_i_see": ["bullet strings of visible evidence"],
        "significance": [
            "If place_photo and confident: factual significance bullets (history/culture/architecture). "
            "If not_a_place or ambiguous: explain why significance can't be determined."
        ],
        "response": "one friendly paragraph summary"
    }

    prompt = f"""
You are a careful image analyst. The user provides ONLY a photo.

Task:
1) Decide if this photo is a PLACE or NOT A PLACE (object/person/food/document/etc.) or AMBIGUOUS.
2) If it is a place, guess the most likely location (name/city/country) and explain the evidence.
3) If you cannot identify confidently, say ambiguous and do NOT invent details.
4) Provide significance ONLY when you are confident it’s a real identified place.
5) Output MUST be valid JSON matching this schema exactly:
{json.dumps(schema, indent=2)}

No extra keys. No markdown. Output only JSON.
"""

    data_url = image_to_data_url(image_path)

    msg = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
    )

    result = llm.invoke([msg]).content

    # Print raw; you can json.loads it later in your next iteration
    print(result)
    


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python base_pipeline.py path/to/image.jpg")
        sys.exit(1)
    main(sys.argv[1])
