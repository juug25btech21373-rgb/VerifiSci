import os, json, re, hashlib, uuid, time, socket, random
import requests
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# ==========================================
# 1. FORCE IPv4 (Fixes Render's DNS issue)
# ==========================================
orig_getaddrinfo = socket.getaddrinfo
def getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = getaddrinfo_ipv4

# ==========================================
# 2. INITIALIZE APP & MIDDLEWARE
# ==========================================
app = FastAPI(title="VerifiSci API")

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

# ==========================================
# 3. CONFIG & CLIENTS
# ==========================================
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# The current stable model according to Google AI docs
PRIMARY_MODEL = "gemini-3.8-flash" 
FALLBACK_MODEL = "gemini-3.6-flash"

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

# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================
def extract_pdf(raw: bytes) -> dict:
    doc = fitz.open(stream=raw, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    return {"pages": len(doc), "text": text, "sha256": hashlib.sha256(raw).hexdigest()}

def parse_json_loose(s: str) -> dict:
    s = s.strip()
    s = re.sub(r"^```(json)?|```$", "", s, flags=re.MULTILINE).strip()
    return json.loads(s)

def ask_llm(prompt: str, retries=5) -> str:
    if not GEMINI_KEY:
        raise HTTPException(500, "GEMINI_API_KEY not set.")
    
    # Try the primary model first, fallback if it fails completely
    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL]
    
    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        
        for attempt in range(retries):
            try:
                r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=90)
                
                if r.status_code == 200:
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"]
                
                # Handle Rate Limits (429) and Server Overload (503)
                if r.status_code in [429, 503, 500]:
                    # Exponential backoff with jitter
                    base_delay = 2
                    delay = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                    print(f"{model} busy ({r.status_code}). Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                    continue
                
                # If it's a client error (400, 403, 404), fail immediately for this model
                if r.status_code in [400, 403, 404]:
                    print(f"{model} returned error {r.status_code}: {r.text[:200]}")
                    break # Break inner loop, try next model
                    
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    print(f"Network error on {model}: {str(e)}")
                    break
                time.sleep(5)
                
    # If both models fail after all retries
    raise HTTPException(503, "The AI service is currently experiencing high demand. Please try again in a few minutes.")

# ==========================================
# 5. API ENDPOINTS
# ==========================================
@app.get("/health")
def health():
    return {"ok": True, "llm": bool(GEMINI_KEY), "database": bool(SUPABASE_URL)}

@app.get("/test-dns")
def test_dns():
    try:
        hostname = SUPABASE_URL.replace("https://", "").replace("http://", "").split("/")[0]
        ip = socket.gethostbyname(hostname)
        return {"ok": True, "ip": ip}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/analyze")
async def analyze(file: UploadFile):
    raw = await file.read()
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
