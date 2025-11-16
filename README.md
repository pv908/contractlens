# ContractLens

ContractLens is a containerised FastAPI microservice for automated contract analysis. It uses Gemini Flash for multimodal clause extraction, Qdrant for precedent retrieval, and a rule-augmented reasoning pipeline for clause-level risk scoring and suggested alternative wording. The service is designed for deployment on Google Cloud Run.

---

## Features

**Extraction**

* PDF and DOCX ingestion
* Gemini 2.5 Pro extraction into structured, Pydantic-validated JSON

**Risk Analysis**

* Liability, termination, and governing law assessment
* Rule-augmented scoring (Green, Amber, Red)
* Suggested contract-safe alternative wording

**Precedent Retrieval**

* Embedding with `text-embedding-004`
* Qdrant vector search for nearest precedent clauses

**Deployment**

* Docker container
* Fully compatible with Google Cloud Run
* Environment variables supplied at deploy time

---

## Architecture

```
Browser UI
   ↓
FastAPI service
   ↓
Gemini Flash (extraction)
   ↓
Risk engine (rule-based)
   ↓
Qdrant (precedent search)
```

---

## Local Development

1. Clone and create environment

```
git clone <repo>
cd contractlens
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create `.env`

```
GEMINI_API_KEY=...
QDRANT_URL=...
QDRANT_API_KEY=...
QDRANT_COLLECTION=contract_precedents
GEMINI_MODEL_NAME=gemini-flash-latest
GEMINI_EMBED_MODEL=text-embedding-004
```

3. Seed Qdrant precedents

```
python3 -m app.precedents_seed
```

4. Run locally

```
uvicorn app.main:app --reload --port 8000
```

---

## Docker (Local)

Build:

```
docker build -t contractlens:local .
```

Run:

```
docker run -p 8080:8080 --env-file .env contractlens:local
```

---

## Google Cloud Run Deployment

Build image:

```
gcloud builds submit \
  --tag gcr.io/$(gcloud config get-value project)/contractlens
```

Deploy:

```
gcloud run deploy contractlens \
  --image gcr.io/$(gcloud config get-value project)/contractlens \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY \
  --set-env-vars QDRANT_URL=$QDRANT_URL \
  --set-env-vars QDRANT_API_KEY=$QDRANT_API_KEY \
  --set-env-vars QDRANT_COLLECTION=$QDRANT_COLLECTION \
  --set-env-vars GEMINI_MODEL_NAME=$GEMINI_MODEL_NAME \
  --set-env-vars GEMINI_EMBED_MODEL=$GEMINI_EMBED_MODEL
```

---

## Project Structure

```
app/
  main.py
  config.py
  ingestion.py
  extraction_agent.py
  risk_engine.py
  report_agent.py
  precedent_agent.py
  qdrant_client.py
  precedents_seed.py
Dockerfile
deploy.sh
requirements.txt
README.md
```