## VerifiSci – Scientific Provenance Platform

VerifiSci is a web app that helps researchers check what a scientific paper actually claims and whether the paper's own text supports those claims. Upload a PDF and VerifiSci extracts the dataset, models, experimental settings, reported results and key claims, flags claims that are contradicted or unverifiable, produces a reproducible workflow, and lets you chat with the paper.

## Live demo: https://verifisci-frontend.vercel.app/
Important – cold start: the backend is hosted on a free Render instance that goes to sleep when idle. The first request after inactivity can take 1–2 minutes while the server wakes up. Please be patient on the first upload or chat message; subsequent requests are fast (analysis of a full paper itself takes roughly 30–90 seconds).

## Table of Contents

- Features
- Architecture
- Tech Stack
- Backend Implementation
- Frontend Implementation
- API Reference
- Data Model
- Getting Started
- Deployment
- Known Limitations & Roadmap

## Features

- PDF ingestion – drag-and-drop or select a research paper PDF.
- Structured analysis – automatically extracts:
                        - Research domain
                        - Dataset (name, size, source, splits, notes)
                        - Models and versions
                        - Experimental settings (optimizer, learning rate, batch size, epochs, seed, hardware)
                        - Reported results with a match/mismatch status
                        - Traceable evidence and a step-by-step reproducible workflow
                        - Related work suggestions
- Claim verification – every detected claim is labelled verified or mismatch, with its location in the paper and supporting evidence. Mismatches are listed in a dedicated panel.
- Paper Assistant chat – ask questions about the paper; answers are grounded strictly in the paper's text with section citations, or the assistant replies NOT FOUND in this paper.
- Save & export – save a project to the session list and export a text report of the claims.
- Light/dark theme, responsive layout, toast notifications and a settings panel for the backend URL.
- Resilient LLM calls – retries with exponential backoff and automatic model fallback.

## Architecture

```mermaid
flowchart LR
    U([User]) --> F["Frontend<br/>React 18 + Tailwind<br/>Vercel"]
    F -->|"POST /analyze (PDF)<br/>POST /chat (question)"| B["Backend<br/>FastAPI + PyMuPDF<br/>Render"]
    B -->|"JSON response"| F
    B -->|"Prompt via generateContent"| G["Google Gemini API"]
    G -->|"Structured JSON / answer"| B
    B -->|"Store / read papers table"| D[("Supabase<br/>PostgreSQL")]
```

## Flow of an analysis
- The user uploads a PDF in the browser.
- The frontend sends it as multipart/form-data to POST /analyze.
- The backend extracts the text with PyMuPDF, builds a prompt containing a strict JSON schema plus the paper text, and calls Gemini.
- The JSON response is parsed, stored in Supabase together with the full text and SHA-256 hash, and returned to the client along with a paper_id.
- For chat, the frontend sends paper_id + question to POST /chat; the backend loads the stored text and asks Gemini to answer only from it.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 (UMD build + in-browser Babel), Tailwind CSS (CDN), Font Awesome, Source Sans 3 |
| Backend | Python, FastAPI, Pydantic, Requests |
| PDF parsing | PyMuPDF (`fitz`) |
| LLM | Google Gemini via the REST `generateContent` endpoint |
| Database | Supabase (PostgreSQL) |
| Hosting | Vercel (frontend), Render (backend) |
