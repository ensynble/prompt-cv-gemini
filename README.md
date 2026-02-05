# Prompt-CV Backend (FastAPI + Gemini)
This document provides a concise overview of the Prompt-CV backend service, including what it does, how to run it locally, and how to use the API.

## Overview
Prompt-CV is a lightweight FastAPI backend that accepts an image and a checklist-style prompt, processes them asynchronously using Google Gemini, and returns a structured JSON result. Jobs are handled through an in-memory queue with optional long polling.

## Key Features
•	Asynchronous job queue with bounded size
•	Background worker processing with Gemini concurrency limits
•	Submit-and-wait or submit-and-poll API patterns
•	Event-based long polling (no busy polling)
•	Upload size limits and basic security gating

## Requirements
•	Python 3.10+
•	Gemini API key
•	FastAPI, Uvicorn, google-genai, Pydantic

## Setup & Run
1. **(Optional)* Create and activate a virtual environment.
•	python -m venv .venv
•	source .venv/bin/activate (macOS/Linux) or .venv\Scripts\activate (Windows)
(Conda is also fine if you prefer.)
2. Install dependencies:
•	pip install -r requirements.txt
3. Create backend/.env (or wherever your config.py reads it):
GEMINI_API_KEY=your_key_here
GEMINI_MODEL= gemini-3-flash-preview
MAX_IMAGE_BYTES=1000000
ALLOW_ORIGINS= http://localhost:5173,http://127.0.0.1:5173
*Notes*:
•	MAX_IMAGE_BYTES is in bytes
•	ALLOW_ORIGINS is a comma-separated list of origins (scheme + host + port)
4. Run the server:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

## API Usage
1.	Health check:
 GET /health
2.	Submit a job (returns job_id):
•	POST/jobs(form-data: prompt, image)
•	Optional: wait_ms(0-30000)
If wait_ms > 0, the request waits up to that time for completion and returns the current status/result.
3.	Get job status / long poll
GET /job/{job_id}?wait_ms=0–30000
Returns immediately if done; otherwise waits up to wait_ms for completion, then returns status/result.

## Job Processing Model
Submitted jobs are enqueued and processed by background workers. Each worker calls Gemini under a concurrency semaphore, updates job status, and signals completion via an asyncio event.
*Notes*
•	All data is in-memory; jobs are lost on restart.
•	Active jobs are never evicted; completed jobs are kept up to a fixed limit.
•	For production use, replace the queue with Redis or a task system.

