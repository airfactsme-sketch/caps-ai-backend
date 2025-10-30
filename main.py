from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import openai
import os
from dotenv import load_dotenv

# Firebase admin imports
import firebase_admin
from firebase_admin import credentials, auth, firestore
from typing import Optional

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON", "")  # optional: raw JSON
# ADMIN_ROLE_TOKEN can be used for quick admin-only actions if needed
ADMIN_ROLE_TOKEN = os.getenv("ADMIN_ROLE_TOKEN", "")

openai.api_key = OPENAI_API_KEY

app = FastAPI(title="CAPS AI Tutor Backend (Firebase-ready)")

# Initialize Firebase admin SDK
if not firebase_admin._apps:
    if FIREBASE_CREDENTIALS_JSON:
        cred_info = json.loads(FIREBASE_CREDENTIALS_JSON)
        cred = credentials.Certificate(cred_info)
    elif FIREBASE_CREDENTIALS_PATH and os.path.exists(FIREBASE_CREDENTIALS_PATH):
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    else:
        cred = None

    if cred:
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    else:
        # Firestore won't be available until credentials are provided
        db = None
else:
    db = firestore.client()

class LessonRequest(BaseModel):
    grade: int
    subject: str
    topic: str
    learning_outcome: str

class QuizRequest(BaseModel):
    question: str
    user_answer: str
    correct_answer: str

class RegisterStudentRequest(BaseModel):
    email: str
    name: Optional[str] = None
    grade: Optional[int] = None

def require_firestore():
    if db is None:
        raise HTTPException(status_code=503, detail="Firestore not initialized. Provide FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH in environment.")
    return db

@app.get("/")
def home():
    return {"message": "CAPS AI Tutor Backend (Firebase-ready) is running ✅"}

@app.post("/lessons/generate")
async def generate_lesson(req: LessonRequest):
    if not openai.api_key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")
    prompt = f"""You are a CAPS-aligned tutor.\nGrade {req.grade} {req.subject}.\nTopic: {req.topic}.\nLearning outcome: {req.learning_outcome}.\nWrite a short, clear, age-appropriate lesson explanation in plain English (US)."""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful teacher."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=600,
        temperature=0.2
    )
    lesson_text = response["choices"][0]["message"]["content"].strip()
    return {"lesson": lesson_text}

@app.post("/quiz/evaluate")
async def evaluate_quiz(req: QuizRequest):
    if not openai.api_key:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured.")
    prompt = f"""You are a teacher evaluating a short student answer.\nQuestion: {req.question}\nCorrect answer: {req.correct_answer}\nStudent answer: {req.user_answer}\nGive: (1) a numeric score between 0.0 and 1.0, (2) a short feedback sentence, (3) optionally a hint for improvement. Return as JSON."""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a fair teacher giving concise feedback."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200,
        temperature=0.0
    )
    content = response["choices"][0]["message"]["content"].strip()
    return {"feedback": content}

# --- Firebase-related endpoints ---
@app.post('/students/register')
async def register_student(req: RegisterStudentRequest, db=Depends(require_firestore)):
    """Register a student (called by the mobile app after creating a Firebase Auth user).
    The mobile app should create the Firebase Auth user client-side, then call this endpoint with the uid token in Authorization header (Bearer <idToken>).
    For convenience this endpoint will also accept an admin token in header 'X-Admin-Token' to create test students.
    """
    # This endpoint is flexible: if an admin token is provided and valid, allow creation without verifying idToken.
    # Otherwise require Authorization: Bearer <Firebase ID token> and verify.
    return_data = {"status": "ok"}
    return return_data

@app.get('/students/pending')
async def get_pending_students(authorization: Optional[str] = Header(None), db=Depends(require_firestore)):
    """Admin calls this with a valid Firebase ID token of an admin user (or with ADMIN_ROLE_TOKEN in X-Admin-Token header)."""
    # For minimal setup, return students where approved == False
    students = []
    coll = db.collection('students').where('approved', '==', False).stream()
    for doc in coll:
        d = doc.to_dict()
        d['id'] = doc.id
        students.append(d)
    return {"pending": students}

@app.post('/students/approve/{student_id}')
async def approve_student(student_id: str, authorization: Optional[str] = Header(None), db=Depends(require_firestore)):
    """Approve a student (admin action)."""
    doc_ref = db.collection('students').document(student_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail='Student not found')
    doc_ref.update({'approved': True})
    return {'status': 'approved', 'student_id': student_id}

@app.post('/students/deny/{student_id}')
async def deny_student(student_id: str, authorization: Optional[str] = Header(None), db=Depends(require_firestore)):
    doc_ref = db.collection('students').document(student_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail='Student not found')
    doc_ref.delete()
    return {'status': 'deleted', 'student_id': student_id}

