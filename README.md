# DSPRO 2

DSPRO 2 is a real-estate recommendation prototype. Users enter a few hard
constraints, swipe through apartment images to express visual preferences, then
receive ranked apartment recommendations. The app also records feedback so the
different recommendation strategies can be compared in the analytics view.

## What is included

- FastAPI backend for onboarding images, recommendations, feedback collection,
  and analytics.
- Next.js frontend for the hard-facts form, image onboarding, recommendation
  feed, and analytics dashboard.
- Preprocessed apartment data, image folders, and precomputed embedding stores
  used by the recommenders.
- Selenium scraper for collecting apartment listings and images from ImmoScout24.
- Preprocessing and embedding scripts/notebooks used to build the data artifacts.

## Tech stack

- Backend: Python 3.12, FastAPI, Uvicorn, PyTorch, Google Gemini API.
- Frontend: Next.js, React, TypeScript, Tailwind CSS.
- Scraping: Selenium, Chrome, Requests.
- Tooling: uv for Python dependencies, npm for frontend dependencies, Docker
  Compose for running both services together.

## Repository structure

```text
.
|-- src/app/                 # FastAPI application and recommender service
|-- src/scraping/            # Selenium web scraper
|-- frontend/                # Next.js application
|-- data/                    # Listing data, images, selected onboarding images
|-- embedding/               # Embedding stores and embedding/cluster scripts
|-- preprocess_pipeline/     # Data cleaning and image selection pipeline
|-- exploration/             # Experiment notebooks and scripts
|-- docker-compose.dev.yml   # Local development Docker Compose setup
|-- docker-compose.yml       # Production-style Compose setup (used for data collection)
`-- pyproject.toml           # Python project dependencies and lint settings
```

The backend entrypoint is `src/app/main.py`. The root-level `main.py` is only a
small placeholder script and is not used to run the web app.

## Required data

The backend expects these files and folders to exist:

- `data/cleaned_apartements_pt_aligned.jsonl`
- `data/images/`
- `data/selected_images/`
- `embedding/gemini_embeddings_clustered.pt`

Feedback submitted through the app is written to `data/feedback.jsonl`. That
file is ignored by git.

For Docker runs, make sure `data/selected_images/` contains files or symlinks
that resolve inside the container. If selected images are missing, recreate them
from the project root after `data/images/` is available:

```bash
uv run python populate_selected_images.py
```

## Selenium web scraper

The scraper in `src/scraping/run_scraper.py` collects apartment listings from
ImmoScout24 and downloads listing images. It uses Selenium to drive Chrome and
Requests to download image files.

Requirements:

- Google Chrome installed locally.
- Python dependencies installed with `uv sync`.
- Network access to ImmoScout24 and to image URLs.

Run the scraper from the project root so its relative output paths resolve
correctly:

```bash
uv sync
uv run python src/scraping/run_scraper.py --num-start-page 0 --num-pages-to-scrape 5
```

CLI options:

- `--num-start-page`: number of result pages to skip before scraping. The
  default is `0`, which starts on the first result page.
- `--num-pages-to-scrape`: number of result pages to scrape. The default is
  `100`; use a smaller number for test runs.

The scraper writes raw outputs to:

- `data/raw/apartements.jsonl` for listing metadata.
- `data/raw/images/{object_id}/` for downloaded listing images, with at most 20
  images per listing.

After scraping, deduplicate the raw listings:

```bash
uv run python preprocess_pipeline/dedpup_scraped_listings.py
```

This creates `data/cleaned/cleaned_apartements.jsonl`, which can then be used by
the preprocessing pipeline to produce the app-ready data artifacts.

## Environment variables

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Then set:

```bash
GEMINI_API_KEY=your_api_key_here
```

`GEMINI_API_KEY` is required whenever a session uses the `gemini` recommender
strategy. The backend loads `.env` automatically from the repository root.

Optional backend variables:

```bash
CORS_ORIGINS=http://localhost:3000
```

The frontend proxies `/api/*` and `/data/images/*` to the backend. For local
development it defaults to `http://localhost:8000` through `frontend/next.config.ts`.

## Run with Docker Compose

This is the simplest way to run the full app locally.

```bash
cp .env.example .env
# edit .env and add GEMINI_API_KEY

docker compose -f docker-compose.dev.yml up --build
```

Open:

- Frontend: http://localhost:3000
- Backend health check: http://localhost:8000/api/health
- Analytics: http://localhost:3000/analytics

Stop the services with `Ctrl+C`, then clean up containers with:

```bash
docker compose -f docker-compose.dev.yml down
```

Note: `docker-compose.yml` is production-style and only exposes service ports
inside the Docker network. Use `docker-compose.dev.yml` for local browser access.

## Run locally without Docker

Start the backend from the `src` directory so the app's relative data paths
resolve correctly.

```bash
cp .env.example .env
# edit .env and add GEMINI_API_KEY

uv sync
cd src
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

In a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Application flow

1. `/hardfacts`: user selects location, minimum rooms, and maximum rent.
2. `/onboarding`: backend returns diverse onboarding apartments; user likes or
   dislikes image cards.
3. `/feed`: frontend requests recommendations, displays ranked listings, and
   collects ratings.
4. `/analytics`: reads submitted feedback and compares recommender strategies.

Sessions start at a random appartment and the rest of the onboarding is created through farthest point sampling, then they are assigned to the least-used recommendation strategy based on
`data/feedback.jsonl`. Strategies currently include `gemini`, `single_vector`,
`k_nearest`, `fuzzy_cluster`, and `random_baseline`.

## Main API endpoints

- `GET /api/health` - backend health check.
- `GET /api/session` - assigns a recommender strategy for the current session.
- `GET /api/recommendations/onboarding` - returns onboarding image cards.
- `POST /api/recommendations/search` - returns ranked recommendations.
- `POST /api/feedback` - stores recommendation ratings.
- `GET /api/analytics` - returns aggregate strategy metrics.
- `GET /api/feedback/download` - downloads feedback as JSONL.

## Development commands

Python formatting and linting:

```bash
uv run ruff format .
uv run ruff check .
```

Frontend linting:

```bash
cd frontend
npm run lint
```

## Data and embedding scripts

The app consumes generated artifacts from `data/` and `embedding/`. Supporting
scripts live in:

- `preprocess_pipeline/` for cleaning listing data and selecting images.
- `embedding/` for creating Gemini embeddings, filtering embeddings, clustering,
  and adding cluster memberships.
- `populate_selected_images.py` for preparing the selected onboarding image
  folders.

These scripts are not required for a normal app run when the generated artifacts
already exist.
