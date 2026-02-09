# 📑 Gemini CV Prompt Detection Backend

A high-performance, containerized FastAPI backend designed to analyze CV/Resume images using the Google Gemini API. This project supports evaluating multiple checklist items (prompts) against a single image upload in a single request.

---

## 🚀 Quick Start

### 1. Prerequisites
* **Docker & Docker Compose**: Installed and running (Docker Desktop for Windows/Mac or Docker Engine for Linux/WSL).
* **Gemini API Key**: Obtain one from https://aistudio.google.com/

### 2. Setup Environment
Clone the repository and prepare your configuration:

```bash
# Clone the project
git clone <repo-link>
cd backend

# Create your local .env file from the template
cp .env.example .env
```

Open the newly created `.env` file and paste your Gemini API key:

```env
GEMINI_API_KEY=your_actual_key_here
```

---

### 3. Launch the Application

Run the following command to build the Docker image and start the service:

```bash
docker-compose up --build
```

Once the service starts:

- API base URL: http://localhost:8000  
- Swagger docs: http://localhost:8000/docs  

You can now send requests to the backend or test endpoints directly from Swagger UI.

---

### 4. Launch the Web App
```bash
cd web
python3 -m http.server 5173
```
open chrome browser and go to http://localhost:5173 click "install"

## API Usage

### 1. Health Check

Verify that the service is running.

```http
GET /health
```

---

### 2. Submit a Job

Submit an image and prompt for processing. Returns a `job_id`.

```http
POST /jobs
```

Request (multipart form-data):

- `prompt` (string, required): The checklist or evaluation prompt
- `image` (file, required): Image to analyze
- `wait_ms` (int, optional, 0–30000):  
  If greater than 0, the request will wait up to the specified time for the job to complete and return the result if available.

Behavior:

- If `wait_ms = 0` → returns immediately with `job_id`
- If `wait_ms > 0` → waits for completion or timeout, then returns status/result

---

### 3. Get Job Status / Long Poll

Check the status of a submitted job or wait for completion.

```http
GET /job/{job_id}?wait_ms=0-30000
```

Behavior:

- Returns immediately if the job is already complete
- Otherwise waits up to `wait_ms` milliseconds
- Returns either:
  - completed result
  - current processing status
  - timeout response

---

## Job Processing Model

Submitted jobs are placed into an in-memory queue and processed by background workers.

Each worker:

- Acquires a concurrency slot via a semaphore
- Calls the Gemini API for image + prompt analysis
- Updates the job status
- Signals completion using an `asyncio.Event`

---

### Runtime Notes

- Data is stored **in memory only**
- Jobs are **lost if the service restarts**
- Active jobs are **never evicted**
- Completed jobs are retained up to a fixed capacity limit

For production deployments:

- Replace the in-memory queue with:
  - Redis
  - Celery / RQ
  - Cloud task systems (Pub/Sub, SQS, etc.)
- Persist job results to a database or object storage
