import os, json, re, hashlib, uuid, time
import requests
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

app = FastAPI(title="VerifiSci API")

# FIX: Explicitly allow your Vercel frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://verifisci-frontend.vercel.app", 
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# FIX: Using the stable 1.5-flash model
GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
              "gemini-3.5-flash:generateContent?key=" + GEMINI_KEY)

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

ANALYSIS_SCHEMA = """Return ONLY valid JSON (no markdown fences) with exactly this shape:
{
  "domain": "short domain label",
  "dataset": {"name": "...", "size": "...", "source": "...", "splits": "...", "note": "..."},
  "models": [{"name": "...", "version": "..."}],
  "settings": {"optimizer": "...", "lr": "...", "batch": "...", "epochs": "...", "seed": "...", "hardware": "..."},
  "results": [{"metric": "...", "reported": "...", "reproduced": "n/a", "status": "match"}],
  "evidence": ["..."],
  "workflow": ["step 1", "step 2"],
  "claims": [{"id": 1, "status": "verified", "text": "...", "location": "...", "evidence": "..."}],
  "relatedWork": [{"title": "...", "why": "..."}]
}
Use "verified" only when the paper's own text fully supports the claim; use "mismatch" for anything the text contradicts or leaves unverifiable (put reason in "evidence"). If the paper has no experiments, fill with "not reported"."""

# FIX: Restored the missing PDF extraction function
def extract_pdf(raw: bytes) -> dict:
    doc = fitz.open(stream=raw, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    return {"pages": len(doc), "text": text, "sha256": hashlib.sha256(raw).hexdigest()}

# FIX: Restored the missing JSON parser
def parse_json_loose(s: str) -> dict:
    s = s.strip()
    s = re.sub(r"^```(json)?|```$", "", s, flags=re.MULTILINE).strip()
    return json.loads(s)

def ask_llm(prompt: str, retries=3) -> str:
    if not GEMINI_KEY:
        raise HTTPException(500, "GEMINI_API_KEY not set.")
    
    for attempt in range(retries):
        try:
            r = requests.post(GEMINI_URL, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=90)
            
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            
            # If 503 (High demand) or 429 (Rate limit), wait and retry
            if r.status_code in [503, 429]:
                wait_time = 5 * (attempt + 1)  # Wait 5s, then 10s, then 15s
                print(f"Gemini API overloaded ({r.status_code}). Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            
            raise HTTPException(502, "LLM error %s: %s" % (r.status_code, r.text[:200]))
            
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                raise HTTPException(502, f"Network error connecting to LLM: {str(e)}")
            time.sleep(5)
            
    raise HTTPException(503, "The AI model is currently experiencing high demand. Please try again in a few minutes.")

@app.post("/analyze")
async def analyze(file: UploadFile):
    raw = await file.read()
    # FIX: Changed limit to 50 MB
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(413, "PDF too large (max 50 MB)")
    
    info = extract_pdf(raw)
    if len(info["text"].strip()) < 100:
        raise HTTPException(422, "No extractable text (scanned PDF?). OCR needed.")
    
    prompt = ANALYSIS_SCHEMA + "\n\nPaper text (%d pages):\n" % info["pages"] + info["text"][:90000]
    analysis = parse_json_loose(ask_llm(prompt))
    paper_id = uuid.uuid4().hex[:12]
    
    try:
        supabase.table("papers").insert({
            "id": paper_id,
            "name": file.filename,
            "sha256": info["sha256"],
            "text": info["text"],
            "analysis": analysis
        }).execute()
    except Exception as e:
        print(f"Supabase error: {e}")
        raise HTTPException(500, "Failed to save data to database.")

    return {"paper_id": paper_id, "file_name": file.filename,
            "pages": info["pages"], **analysis}

class ChatReq(BaseModel):
    paper_id: str
    question: str

@app.post("/chat")
async def chat(req: ChatReq):
    try:
        response = supabase.table("papers").select("*").eq("id", req.paper_id).execute()
        if not response.data:
            raise HTTPException(404, "Paper not found. Re-upload it.")
        p = response.data[0]
    except Exception as e:
        print(f"Supabase error: {e}")
        raise HTTPException(500, "Database connection failed.")

    answer = ask_llm(
        "Answer strictly from this paper. Cite the section. "
        "If unsupported, say NOT FOUND in this paper.\n\n"
        "Paper: " + p["name"] + "\n\n" + p["text"][:90000]
        + "\n\nQuestion: " + req.question)
    return {"answer": answer}

@app.get("/health")
def health():
    return {"ok": True, "llm": bool(GEMINI_KEY), "database": bool(SUPABASE_URL)}
