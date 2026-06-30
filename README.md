# Selectable Chatbot

A full-stack chatbot application with a FastAPI backend and a React frontend. 6 possible personalities. Conversations can be saved, analyzed, and continued later.

## Project structure

- Backend/ - FastAPI API server
- Frontend/ - React + TypeScript client
- conversations/ - Stored conversation exports and conversation data used by the backend
- logs/ - Backend application logs

## Requirements

- Python 3.10+
- Node.js 18+
- uv (recommended for Python dependency management)
- An OpenAI API key

## Backend setup

1. Install uv (if not already available):

   ```powershell
   pip install uv
   ```

2. Go to the backend folder:

   ```powershell
   cd Backend
   ```

3. Sync dependencies with uv:

   ```powershell
   uv sync
   ```

4. Create a `.env` file in the Backend folder with your OpenAI API key:

   ```env
   OPENAI_API_KEY=your_openai_key_here
   ```

5. Start the backend:

   ```powershell
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

   The API will be available at:

   ```text
   http://localhost:8000
   ```

   The API documentation will also be available at:

   ```text
   http://localhost:8000/docs
   ```

## Frontend setup

1. Go to the frontend folder:

   ```powershell
   cd Frontend
   ```

2. Install frontend dependencies:

   ```powershell
   npm install
   ```

3. Start the development server:

   ```powershell
   npm start
   ```

   The frontend will be available at:

   ```text
   http://localhost:3000
   ```

## Important frontend note

Before starting the frontend, make sure the following dependencies are installed in the Frontend folder:

```powershell
npm install
```

This installs the React app dependencies, including `react`, `react-dom`, `react-router-dom`, and `react-scripts`.

## Notes

- The frontend is configured to connect to the backend at `http://localhost:8000`.
- The backend uses the `OPENAI_API_KEY` environment variable for AI functionality.
- Conversation files are stored in the backend-side conversations folder.
- Backend logs are written to the backend logs folder.

## Useful commands

### Backend

```powershell
cd Backend
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```powershell
cd Frontend
npm install
npm start
```

### Troubleshooting

- If the backend cannot start, verify that `OPENAI_API_KEY` is present in [Backend/.env](Backend/.env).
- If the frontend cannot connect, ensure the backend is running on `http://localhost:8000`.
- If dependency installation fails, remove `node_modules` and run `npm install` again.

## TODO

- Improve conversation analysis so the backend passes the full conversation object to the analysis flow instead of only message data. This is referenced in [Backend/app/main.py](Backend/app/main.py#L212).

## Development process

This project was developed with AI-assisted coding. I used AI tools to speed up implementation, but reviewed, tested, modified, and debugged the code myself.