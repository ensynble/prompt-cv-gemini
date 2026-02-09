# 📑 How to run Argus

# i) Backend
A high-performance, containerized FastAPI backend designed to analyze CV/Resume images using the Google Gemini API. This project supports evaluating multiple checklist items (prompts) against a single image upload in a single request.

---

### 1. Prerequisites
* **Docker & Docker Compose**: Installed and running (Docker Desktop for Windows/Mac or Docker Engine for Linux/WSL).
* **Gemini API Key**: Obtain one from https://aistudio.google.com/

### 2. Setup Environment
Clone the repository and prepare your configuration:

```bash
# Clone the project
git clone <repo-link>
cd prompt-cv-gemini

# Create your local .env file from the template
cp .env.example .env
```

Open the newly created `.env` file and paste your Gemini API key:

```env
GEMINI_API_KEY=your_actual_key_here
```

---

### 3. Launch the Backend Service

Run the following command to build the Docker image and start the service:

```bash
docker-compose up --build
```

Once the service starts:

- API base URL: http://localhost:8000  
- Swagger docs: http://localhost:8000/docs  

You can now send requests to the backend or test endpoints directly from Swagger UI.

---

# ii) Launch Argus Web App
```bash
cd web
python3 -m http.server 5173
```
open chrome browser and go to http://localhost:5173 click "install"

