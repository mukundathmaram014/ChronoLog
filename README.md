<h1 align="center">
  <img src="assets/favicon.png" alt="Logo" width="32" style="vertical-align: middle; margin-right: 8px;">
  ChronoLog
</h1>


ChronoLog is a productivity tracking application with a Flask backend and a React frontend. It helps users manage habits, track time with stopwatches, and view statistics on these. It is currently hosted at [www.chronologtracker.com](https://chronologtracker.com/) where I use it daily, and also available for anyone else to use.



## 📘 Documentation

For in-depth explanations of the architecture, authentication, deployment, and design decisions, see the [**docs/**](./docs/) folder.


## Features

- User authentication (JWT-based)
- Habit tracking (CRUD operations)
- Time tracking with custom stopwatches
- Productivity statistics and analytics
- Responsive React frontend
- RESTful API backend

## Project Structure

```

ChronoLog/
├── assets/
│   └── favicon.png
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── instance/
│   │   └── ChronoLog.db
│   └── src/
│       ├── app.py
│       ├── db.py
│       ├── utils.py
│       └── routes/
│           ├── habits.py
│           ├── statistics.py
│           ├── stopwatch.py
│           └── users.py
├── docs/
│   ├── architecture.md
│   ├── authentication.md
│   ├── deployment.md
│   └── implementation_details.md
├── frontend/
│   ├── package.json
│   └── src/
│       ├── App.js
│       └── ... (components, pages, hooks)
└── docker-compose.yml

```

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Node.js & npm (for frontend development)
- Python 3.8+ (for backend development, if running locally)

### Running with Docker Compose

1. Build and start the services:
	```sh
	docker-compose up --build
	```
2. The backend will be available at `http://localhost:80` (mapped to Flask’s port 5000).

### Running Locally

#### Backend

1. Navigate to `backend/src`.
2. Install dependencies:
	```sh
	pip install -r ../requirements.txt
	```
3. Run the Flask app:
	```sh
	python app.py
	```

#### Frontend

1. Navigate to `frontend`.
2. Install dependencies:
	```sh
	npm install
	```
3. Start the React app:
	```sh
	npm start
	```
4. The frontend will be available at `http://localhost:3000`.

## Environment Variables

- Backend uses a `.env` file for configuration (see `backend/.env`). Add your JWT secret key to this file using the format:

JWT_SECRET_KEY = "your-secret-key"

## Technologies Used

- Backend: Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-CORS
- Frontend: React, React Router, DnD Kit
- Database: SQLite (default)
- Containerization: Docker, Docker Compose

## 🤖 AI-Assisted Development Workflow

ChronoLog is developed with [Claude Code](https://claude.com/claude-code) using a small set of
repo-specific slash commands (defined in [`.claude/commands/`](./.claude/commands/)) that take an idea
from rough note to reviewed PR. Project conventions and the working agreement live in
[`CLAUDE.md`](./CLAUDE.md); specs live in [`specs/`](./specs/) (see [`specs/README.md`](./specs/README.md)).

The loop:

| Command | What it does |
|---------|--------------|
| `/triage` | Reads my Obsidian notes doc (read-only), pulls every unchecked idea, and writes a reviewable accept/reject list of candidate specs to `specs/triage.md`. The pre-spec idea funnel. |
| `/spec <todo>` | Turns one accepted idea/bug into a structured, code-grounded implementation spec at `specs/NNNN-slug.md`. |
| `/build specs/NNNN-...` | Implements one approved spec on its own branch and opens a PR. |
| `/build-batch <specs \| all>` | Orchestrates building many specs: maps dependencies from each spec's "Affected files", builds in waves — independent specs in parallel (isolated git worktrees), coupled specs sequenced — and pauses after each wave for me to review/merge before the next. Never auto-merges. |
| `/deploy-backend <version>` | Builds, pushes, and redeploys the backend image to the production VM (frontend deploys automatically via Netlify on merge to `main`). |

Guiding principles: `main` is always the deployed/stable branch (never committed to directly); every
change lands through a reviewed PR; and changes stay as small as the goal allows — larger refactors are
fine when they deliver substantial value, but never opportunistically.

## License

MIT License
Feel free to use, modify, and build upon it.