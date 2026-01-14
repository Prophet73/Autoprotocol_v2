"""
Test manager_analytics_construction_prompt on result_transcript.docx
"""
import json
import os
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai
from docx import Document

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set in environment")

genai.configure(api_key=GEMINI_API_KEY)

# Load prompts
PROMPTS_PATH = Path(__file__).parent.parent.parent / "Autoportocol" / "prompts.json"
with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)

def extract_transcript_from_docx(docx_path: str) -> str:
    """Extract text from a .docx file."""
    doc = Document(docx_path)
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)

def run_manager_analytics_prompt(transcript_text: str) -> dict:
    """Run the manager_analytics_construction_prompt on transcript text."""
    prompt_config = PROMPTS["manager_analytics_construction_prompt"]

    system_role = prompt_config["system_role"]
    task_description = prompt_config["task_description"]
    rules_and_structure = prompt_config["rules_and_structure"]
    final_instruction = prompt_config["final_instruction"].format(transcript_text=transcript_text)

    # Build full prompt
    full_prompt = f"""
{system_role}

{task_description}

{rules_and_structure}

{final_instruction}
"""

    print("=" * 60)
    print("SENDING TO GEMINI API")
    print("=" * 60)
    print(f"Transcript length: {len(transcript_text)} chars")
    print("=" * 60)

    # Call Gemini
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(
        full_prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.3,
        )
    )

    # Parse response
    response_text = response.text
    print("\nRAW RESPONSE:")
    print("=" * 60)
    print(response_text)
    print("=" * 60)

    try:
        result = json.loads(response_text)
        return result
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return {"raw_response": response_text}

def main():
    # Path to test file
    docx_path = Path(__file__).parent.parent / "_test_media" / "result_transcript.docx"

    if not docx_path.exists():
        print(f"File not found: {docx_path}")
        return

    print(f"Reading transcript from: {docx_path}")
    transcript_text = extract_transcript_from_docx(str(docx_path))

    print(f"\nTranscript extracted: {len(transcript_text)} chars")
    print("=" * 60)
    print("TRANSCRIPT PREVIEW (first 500 chars):")
    print("=" * 60)
    print(transcript_text[:500])
    print("...")
    print("=" * 60)

    # Run the prompt
    result = run_manager_analytics_prompt(transcript_text)

    print("\n" + "=" * 60)
    print("PARSED RESULT:")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Save result
    output_path = Path(__file__).parent / "test_manager_prompt_result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nResult saved to: {output_path}")

if __name__ == "__main__":
    main()
