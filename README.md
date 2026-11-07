# VerifiSci : AI-Powered Research Reproducibility Assistant

**Live Demo:**  (https://verifisci-frontend.vercel.app)
*(Note: Since this is hosted on a free tier, the first request may take 10-15 seconds while the server wakes up).*

## Project Overview
VerifiSci is a full-stack, AI-powered web application designed to tackle the scientific reproducibility crisis. Researchers can upload scientific PDFs to automatically extract datasets, model versions, and experimental settings. The platform uses Google Gemini to verify manuscript claims, flag mismatches, and allows users to chat directly with the paper's context.

## Design & UI/UX Process
The application was designed with an "audit-grade" aesthetic to invoke trust, precision, and transparency for researchers. 
*   **Prototyping:** The initial UI/UX was designed and prototyped using AI-assisted design tools (UXPilot) to rapidly iterate on the three-pane layout (Navigation, Data Canvas, Chat).
*   **Design System:** Features a custom color palette (Sage Green and Warm Charcoal) with fully functional Light and Dark modes. 
*   **Typography:** Uses `Source Sans 3` for optimal readability of dense scientific data, with `FontAwesome` for clean, professional iconography.

## Key Features
*   **PDF Parsing & Hashing:** Extracts text via `PyMuPDF` and generates a SHA-256 hash of the file to ensure provenance tracking.
*   **LLM Claim Verification:** Uses a strict JSON schema prompt with Google Gemini to identify "Verified" claims vs. "Mismatches" (e.g., hidden preprocessing or altered hyperparameters).
*   **Paper Assistant Chat:** A conversational AI that answers questions strictly based on the context of the uploaded paper text.
*   **Persistent Storage:** Securely saves paper analysis and metadata to a Supabase PostgreSQL database.

## System Architecture & Data Flow
This is a fully decoupled, cloud-native application:
1.  **Frontend (Vercel):** The user uploads a PDF.
2.  **Backend (Render):** FastAPI receives the file, extracts text, and hashes it.
3.  **AI Engine (Gemini API):** The text is sent to Google Gemini with a strict JSON schema to extract claims and settings.
4.  **Database (Supabase):** The parsed JSON and file hash are saved to PostgreSQL.

**Tech Stack:**
*   **Frontend:** React (CDN), Tailwind CSS
*   **Backend:** Python, FastAPI, Uvicorn, PyMuPDF
*   **Database:** Supabase (PostgreSQL)
*   **AI:** Google Gemini API
*   **DevOps:** Render, Vercel, UptimeRobot

## Engineering Highlights & Challenges Solved
Deploying this to production involved solving several real-world infrastructure and API challenges:

1.  **LLM Fault Tolerance:** Google's API frequently returns `429 (Too Many Requests)` and `503 (Service Unavailable)` errors. Implemented an **exponential backoff with jitter** retry mechanism in the backend to automatically handle these gracefully without crashing the user experience.
2.  **Database Schema Caching:** Addressed Supabase `PGRST205` errors by utilizing PostgreSQL's `NOTIFY pgrst, 'reload schema';` command to force the API to update its internal schema cache after migrations.
3.  **Cloud DNS Resolution:** Overcame `Errno -2: Name or service not known` errors on Render by forcing the Python environment to resolve the Supabase connection via IPv4 (`socket.AF_INET`), bypassing the platform's default routing issues.
4.  **CORS Security:** Configured strict Cross-Origin Resource Sharing (CORS) policies in FastAPI to ensure only the Vercel frontend can communicate with the backend.
5.  **Free-Tier Optimization:** Utilized UptimeRobot to ping the Render backend every 5 minutes, preventing the free instance from spinning down and ensuring fast response times for users.

## How to Use the App
1.  Open the [Live Demo](https://verifisci-frontend.vercel.app).
2.  Log in (any email/password works for this demo).
3.  Upload a scientific PDF (Max 20MB).
4.  Wait ~15 seconds while the Gemini AI parses the text, extracts claims, and detects mismatches.
5.  Review the extracted datasets, models, and flagged mismatches on the dashboard.
6.  Click the **Chat** button to ask specific questions about the paper (e.g., *"What dataset was used?"*).

## Repository Structure
*   `frontend/index.html` - The complete React single-page application (UI, state management, and API calls).
*   `backend/main.py` - The FastAPI server handling PDF parsing, LLM interactions, and database inserts.
*   `backend/requirements.txt` - Python dependencies.

## Future Roadmap
*   Implement real user authentication using Supabase Auth.
*   Build an interactive, visual Directed Acyclic Graph (DAG) for provenance tracking.
*   Add support for OCR to process scanned/image-only PDFs.
