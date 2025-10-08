# ChronoLog

ChronoLog is a productivity tracking application with a Flask backend and a React frontend. It helps users manage habits, track time with stopwatches, and view productivity statistics.

## Features

- User authentication (JWT-based)
- Habit tracking (CRUD operations)
- Stopwatch for time tracking
- Productivity statistics and analytics
- Responsive React frontend
- RESTful API backend

## Project Structure

```
ChronoLog/
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

## API Endpoints

- `/register` - User registration
- `/login` - User login
- `/habits/` - Habit management
- `/stopwatch/` - Stopwatch management
- `/stats/` - Productivity statistics

## Environment Variables

- Backend uses a `.env` file for configuration (see `backend/.env`).

## Technologies Used

- Backend: Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-CORS
- Frontend: React, React Router, Axios, DnD Kit
- Database: SQLite (default)
- Containerization: Docker, Docker Compose

## License

MIT License
