import os
import json
import requests
import time
from io import BytesIO
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

load_dotenv()

# ==========================================
# ⚙️ SETTINGS
# ==========================================
INPUT_FILE = "data/nsp_scholarship_cards.json"
OUTPUT_FILE = "data/all_scholarships_enriched.json"

# Set to None to run all 31 scholarships
LIMIT = None 

# Wait 30 seconds between Groq calls to avoid Rate Limit (Free Tier)
SLEEP_TIME = 30 

# Your custom Poppler path for Windows
POPPLER_PATH = r"D:\poppler-26.09.0\Library\bin"

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_pdf_text(url):
    """Downloads PDF and extracts text. Uses OCR if it's an image."""
    print("   ⬇️ Downloading PDF...")
    response = requests.get(url, headers=headers, timeout=120)
    response.raise_for_status()
    pdf_bytes = response.content
    
    pdf_text = ""
    # 1. Try normal text
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(pdf_bytes))
        pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        pass

    # 2. If empty, use OCR
    if len(pdf_text.strip()) < 50:
        print("   🖼️ No text found. Using OCR...")
        from pdf2image import convert_from_bytes
        import pytesseract
        from PIL import ImageOps
        
        # Added poppler_path here!
        images = convert_from_bytes(
            pdf_bytes, 
            dpi=300, 
            poppler_path=POPPLER_PATH
        )
        
        ocr_text = ""
        for i, img in enumerate(images, 1):
            img = ImageOps.autocontrast(img.convert("L"))
            text = pytesseract.image_to_string(img, config="--psm 6")
            ocr_text += f"\n--- Page {i} ---\n{text}"
            print(f"      Processed page {i}/{len(images)}")
            
        pdf_text = ocr_text
        
    return pdf_text

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Cannot find {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        scholarships = json.load(f)

    if LIMIT:
        print(f"⚠️ TEST MODE: Only processing first {LIMIT} scholarships.")
        scholarships = scholarships[:LIMIT]

    print(f"📚 Processing {len(scholarships)} scholarships.\n")

    # Start fresh (delete old file to re-run failed ones)
    results = []

    for i, item in enumerate(scholarships, 1):
        name = item.get("scholarship_name", f"Unknown #{i}")
        url = item.get("specifications_url")

        print(f"[{i}/{len(scholarships)}] Processing: {name}")

        if not url:
            print("   ⚠️ No URL found. Skipping.")
            results.append({**item, "extraction_status": "skipped_no_url"})
            continue

        try:
            # 1. Get Text
            pdf_text = get_pdf_text(url)
            print(f"   📝 Extracted {len(pdf_text)} characters.")

            # 2. Prompt
            prompt = f"""
Extract scholarship information from the official guideline text below.
Return ONLY valid JSON with these fields:
{{
  "provider": null,
  "eligibility": [],
  "award_amount": null,
  "education_level": [],
  "eligible_courses": [],
  "required_documents": [],
  "renewal_requirements": [],
  "missing_fields": []
}}

Rules:
- Use only information supported by the supplied text.
- If information is not available, use null for scalar fields and [] for lists.
- Return JSON only, without Markdown fences.

GUIDELINE TEXT:
{pdf_text[:18000]}
"""
            print("   🧠 Sending to Groq...")
            response = llm.invoke(prompt)
            
            # 3. Clean & Parse JSON
            content = response.content.strip()
            if content.startswith("```json"): content = content[7:]
            elif content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            extracted = json.loads(content.strip())

            # 4. Merge and save
            results.append({**item, **extracted, "extraction_status": "ok"})
            print("   ✅ Success!")

            # Save to disk immediately after every successful PDF
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results.append({**item, "extraction_status": "failed", "error": str(e)})
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

        # Sleep to avoid rate limits
        if i < len(scholarships):
            print(f"   💤 Waiting {SLEEP_TIME} seconds to avoid rate limits...\n")
            time.sleep(SLEEP_TIME)

    print(f"\n🎉 Finished! Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()