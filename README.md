# Backend Service README

## Requirements

-   Python 3.10+
-   Gemini API key
-   FastAPI, Uvicorn, `google-genai`, Pydantic

------------------------------------------------------------------------

## Setup & Run

1.  **(Optional)** Create and activate a virtual environment

``` bash
python -m venv .venv
```

Activate it:

-   macOS / Linux:

``` bash
source .venv/bin/activate
```

-   Windows:

``` bash
.venv\Scripts\activate
```

> Conda is also fine if you prefer.

2.  **Install dependencies**

``` bash
pip install -r requirements.txt
```

3.  **Create `backend/.env`** (or wherever `config.py` reads from)

``` env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3-flash-preview
MAX_IMAGE_BYTES=1000000
ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Notes: - `MAX_IMAGE_BYTES` is specified in bytes - `ALLOW_ORIGINS` is a
comma-separated list of allowed origins (scheme + host + port)

4.  **Run the server**

``` bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

------------------------------------------------------------------------

## API Usage

### 1. Health check

``` http
GET /health
```

### 2. Submit a job (returns job_id)

``` http
POST /jobs
```

-   form-data: `prompt`, `image`
-   Optional: `wait_ms` (0--30000)

If `wait_ms > 0`, the request waits up to the specified time for
completion and returns the current status or result.

### 3. Get job status / long poll

``` http
GET /job/{job_id}?wait_ms=0–30000
```

-   Returns immediately if the job is complete
-   Otherwise waits up to `wait_ms` milliseconds, then returns
    status/result

------------------------------------------------------------------------

## Job Processing Model

Submitted jobs are enqueued and processed by background workers.

Each worker: - Calls Gemini under a concurrency semaphore - Updates job
status - Signals completion via an `asyncio.Event`

Notes: - All data is stored in memory; jobs are lost on restart - Active
jobs are never evicted - Completed jobs are kept up to a fixed limit -
For production use, replace the in-memory queue with Redis or a task
system
