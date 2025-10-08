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
│   └── productivityapp/
│       ├── package.json
│       └── src/
│           ├── App.js
│           └── ... (components, pages, hooks)
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

1. Navigate to `frontend/productivityapp`.
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

## License

MIT License
Feel free to use, modify, and build upon it.