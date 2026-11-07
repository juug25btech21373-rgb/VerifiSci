# VerifiSci
An AI-powered Research Reproducibility Assistant. Upload scientific PDFs to automatically extract datasets, models, and experimental settings, verify claims for mismatches, and chat with an AI to uncover hidden details. Built with FastAPI, React, Gemini, and Supabase.

## Features
- **PDF Analysis:** Upload a manuscript to automatically extract datasets, model versions, and experimental settings using Google Gemini.
- **Claim Verification:** Detects claims made in the paper and cross-references them to flag mismatches or unverified statements.
- **Reproducibility Workflow:** Automatically generates a step-by-step workflow based on the paper's methodology.
- **Paper Assistant Chat:** Ask questions directly about the uploaded paper (e.g., "What learning rate was used?" or "Why was Claim 2 flagged?").
- **Export & Save:** Export the analysis as a text report.
- **Dark Mode:** Fully responsive UI with light and dark themes.

## Tech Stack
- **Frontend:** React (via CDN), Tailwind CSS, FontAwesome
- **Backend:** FastAPI (Python), PyMuPDF
- **AI:** Google Gemini API
- **Database:** Supabase (PostgreSQL)

## Project Structure
- `/frontend` - Contains the single-page React application (`index.html`).
- `/backend` - Contains the FastAPI server (`main.py`).

## Local Development Setup

### Backend Setup
1. Navigate to the backend folder: `cd backend`
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Set your environment variables (or hardcode them in `main.py` for testing):
   - `GEMINI_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
4. Start the server: `python -m uvicorn main:app --reload`

### Frontend Setup
1. Navigate to the frontend folder: `cd frontend`
2. Open `index.html` in your web browser.
3. Click the **Settings** gear icon in the app and ensure the Backend API URL is set to `http://localhost:8000`.

## Deployment
- **Backend:** Deployed via **Render** (Root directory: `backend`, Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`).
- **Frontend:** Deployed via **Vercel** (Root directory: `frontend`).
