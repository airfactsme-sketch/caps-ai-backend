# CAPS AI Backend (Firebase-ready)

This backend implements small FastAPI endpoints for your CAPS AI Tutor app.
It integrates with Firebase Admin SDK so you can manage student approvals from your Admin app.

## Files
- `main.py` - FastAPI application
- `requirements.txt` - Python dependencies
- `.env` - environment variables (place your keys here or set them in Render)

## Environment variables
- `OPENAI_API_KEY` - your OpenAI secret key (set this in Render Environment)
- `FIREBASE_CREDENTIALS_PATH` - path to service account JSON (optional for local use)
- `FIREBASE_CREDENTIALS_JSON` - raw service account JSON string (useful for Render)
- `ADMIN_ROLE_TOKEN` - optional admin token for quick admin requests (not recommended for production)

## Deploy to Render
1. Push repo to GitHub.
2. Create a new Web Service on Render, connect to the repo.
3. Start command: `uvicorn main:app --host 0.0.0.0 --port 10000`
4. Add environment variables in Render's dashboard (OPENAI_API_KEY and FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH).
5. Deploy and visit `/docs` to test.\n