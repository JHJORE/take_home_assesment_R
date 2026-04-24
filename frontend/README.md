# Readily — Web UI

Next.js client that renders the questionnaire ↔ policy view. All data comes
from the FastAPI backend at `NEXT_PUBLIC_API_BASE_URL` (default
`http://localhost:8000`); there are no server-side filesystem reads.

## Run it

```bash
# 1. Start the backend (repo root)
cd backend
uvicorn readily.interface.api.app:create_app --factory --reload --port 8000

# 2. Start the frontend
cd ../frontend
npm install
npm run dev                  # opens http://localhost:3000
```

If `data/` at the repo root is empty, the backend falls back to
`backend/sample-data/` and `/info` returns `using_sample: true`; the sidebar
shows a `Sample` badge. Run the pipeline via `readily run` to replace with
real output.

## Endpoint contract

| Method | Path | Purpose |
|--------|---------------------------|-----------------------------------------|
| GET | `/info` | `{ready, using_sample, has_questions, has_policies, has_results}` |
| GET | `/questions` | `TQuestion[]` |
| GET | `/questions/{number}` | `TQuestion` |
| GET | `/policies` | `TPolicyDoc[]` |
| GET | `/policy/{code}/pdf` | streamed PDF |
| GET | `/results?question_number=` | `TQuestionClaimResult[]` |
| POST | `/upload` | stub: stores the PDF under `data/uploads/` |

TS types for the JSON shapes live in `lib/schema.ts` (hand-synced with the
Pydantic entities in `backend/src/readily/domain/entities.py`).

## Status model

Each question row shows one of:

- **●** filled — every extracted claim has a non-contradicting policy match
- **◎** contradiction — the policy conflicts with at least one claim
- **○** unmatched — no policy language was surfaced for at least one claim
