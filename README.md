# CodeMix NLP — Indian Code-Mixed Text Intelligence Platform

> Production-grade NLP platform for detecting **sarcasm** and **misinformation** in Indian code-mixed text (Hinglish, Tanglish) using multilingual transformers with full explainability.

[![CI](https://github.com/yourorg/codemix-nlp/actions/workflows/ci.yml/badge.svg)](https://github.com/yourorg/codemix-nlp/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## Features

| Feature | Details |
|---|---|
| **Multi-task NLP** | Simultaneous sarcasm + misinformation detection |
| **Multilingual** | XLM-RoBERTa-large, trained on Hinglish & Tanglish |
| **Explainability** | SHAP token attribution + self-attention heatmaps |
| **Real-time API** | FastAPI with sub-200 ms inference (cached) |
| **Batch processing** | Async Celery queue for up to 100 texts |
| **Auth** | JWT (HS256) + API key support |
| **Full-stack** | Next.js 14 App Router + Radix UI + Framer Motion |
| **Caching** | Redis SHA-256 hash cache (3600 s TTL) |
| **Async DB** | PostgreSQL 15 + SQLAlchemy 2.0 async |

---

## Architecture

```
┌──────────────┐     ┌────────────────────────────────────┐
│  Next.js 14  │────▶│  FastAPI  /api/v1                   │
│  (port 3000) │     │  ├── /auth  (register, login)       │
└──────────────┘     │  ├── /analyze  (single, batch)      │
                     │  ├── /users  (me, history, api-key) │
                     │  └── /analytics  (stats)            │
                     └───────────┬────────────────────────-┘
                                 │
              ┌──────────────────┼──────────────────────┐
              │                  │                      │
        ┌─────▼──────┐   ┌──────▼──────┐   ┌──────────▼────────┐
        │ PostgreSQL │   │    Redis    │   │  Celery Worker    │
        │ (async)    │   │  (cache)   │   │  (batch tasks)    │
        └────────────┘   └────────────┘   └───────────────────┘
                                                    │
                                          ┌─────────▼──────────┐
                                          │  XLM-RoBERTa-large │
                                          │  (multi-task head) │
                                          └────────────────────┘
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- NVIDIA GPU (optional, CPU fallback available)

### 1. Clone & configure

```bash
git clone https://github.com/yourorg/codemix-nlp.git
cd codemix-nlp
cp .env.example .env
# Edit .env: set JWT_SECRET_KEY, DATABASE_URL, REDIS_URL
```

### 2. Launch all services

```bash
docker compose up -d
```

Services started:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: port 5432
- **Redis**: port 6379

### 3. (Optional) Train the model

```bash
# Generate synthetic 10K dataset + fine-tune XLM-RoBERTa
docker compose exec backend python -m ml.training.train

# Or locally:
cd backend
python -m ml.data.preprocess    # generates data/
python -m ml.training.train     # saves checkpoint to models/
```

---

## Development Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### Run tests

```bash
# Backend
cd backend
pip install pytest pytest-asyncio httpx aiosqlite
pytest

# Frontend  
cd frontend
npm test
```

---

## API Reference

### Authentication

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "Password1",
  "full_name": "Arjun Sharma"
}
```

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=Password1
```

### Single Analysis

```http
POST /api/v1/analyze
Authorization: Bearer <token>   # optional
Content-Type: application/json

{
  "text": "Haan bilkul, Modi ji ne toh desh ka bohot vikas kar diya 🙄"
}
```

**Response:**
```json
{
  "id": "uuid",
  "text": "...",
  "sarcasm": {
    "score": 0.87,
    "label": "SARCASTIC",
    "confidence": "HIGH"
  },
  "misinformation": {
    "score": 0.12,
    "label": "CREDIBLE",
    "confidence": "HIGH"
  },
  "model_version": "xlm-roberta-large-codemix-v1",
  "language": "hinglish",
  "processing_time_ms": 145.3,
  "is_cached": false
}
```

### Get Explanation

```http
POST /api/v1/analyze/explain
Content-Type: application/json

{ "text": "..." }
```

Returns SHAP token attribution values + attention weight matrix.

### Batch Analysis (authenticated)

```http
POST /api/v1/analyze/batch
Authorization: Bearer <token>
Content-Type: application/json

{ "texts": ["text1", "text2", ...] }
```

Returns `job_id` for async processing via Celery.

### API Key Usage

```http
GET /api/v1/users/me
X-API-Key: cmk_your_api_key_here
```

---

## Model Architecture

```
Input Text
    │
    ▼
XLM-RoBERTa-large  (first 6 layers frozen)
    │
    ├──▶ ClassificationHead ──▶ Sarcasm (0/1)
    │       Dense → GELU → LayerNorm → Dropout → Linear
    │
    └──▶ ClassificationHead ──▶ Misinformation (0/1)
            Dense → GELU → LayerNorm → Dropout → Linear

Loss = 0.5 × CrossEntropy(sarcasm) + 0.5 × CrossEntropy(misinfo)
```

**Training config:**
- Base: `xlm-roberta-large`
- Optimizer: AdamW, lr=2e-5, weight decay=0.01
- Scheduler: Linear warmup (500 steps)
- Batch size: 16
- Epochs: 5, early stopping patience=2
- Frozen layers: first 6 of 24

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI routers
│   │   ├── core/            # config, database, security
│   │   ├── middleware/      # rate limiting, logging
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic v2 schemas
│   │   ├── services/        # business logic, ML service
│   │   └── tasks/           # Celery tasks
│   ├── ml/
│   │   ├── data/            # preprocessing, synthetic data gen
│   │   ├── models/          # MultiTaskCodeMixModel
│   │   └── training/        # HuggingFace Trainer
│   ├── tests/               # pytest async tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/                 # Next.js 14 App Router pages
│   ├── components/          # UI, layout, analysis, dashboard
│   ├── lib/                 # api.ts, types.ts, store.ts, utils.ts
│   ├── hooks/               # use-toast
│   ├── styles/              # globals.css design tokens
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── .env.example
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `JWT_SECRET_KEY` | HS256 signing secret (min 32 chars) | — |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL | `30` |
| `MODEL_PATH` | Fine-tuned checkpoint path | `./ml/models/checkpoint` |
| `RATE_LIMIT_REQUESTS` | Requests per window | `60` |
| `RATE_LIMIT_WINDOW` | Window in seconds | `60` |
| `CELERY_BROKER_URL` | Celery broker | Redis URL |

---

## Performance

| Metric | Value |
|---|---|
| P50 inference latency | ~120 ms (GPU) / ~800 ms (CPU) |
| Cache hit latency | ~5 ms |
| Batch throughput | ~50 texts/sec (GPU) |
| Synthetic dataset F1 | Sarcasm: ~0.84 / Misinfo: ~0.81 |

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Commit with conventional commits: `git commit -m 'feat: add XYZ'`
4. Push and open a PR

---

## License

MIT © 2024 CodeMix NLP
