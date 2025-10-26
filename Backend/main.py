from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from pypdf import PdfReader
from io import BytesIO
import re
import os
import google.generativeai as genai
from elevenlabs.client import ElevenLabs
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import json

# ============================================================
# 1️⃣ Initialize FastAPI
# ============================================================
app = FastAPI(title="Podcast Generator API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 2️⃣ Initialize Firebase Admin with your service account
# ============================================================
try:
    # Use your service account JSON file directly
    service_account_info = {
        "type": "service_account",
        "project_id": "podcase-generator",
        "private_key_id": "b8b4e6402db1ee173852efb850407eaaeb2320ee",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDCq9l6lajlHdxN\nbMxWhZ2A3axyHOSG9SKikQZE9HQZFrm2vTzuHZVQv2XqeqF7F4vb6st9/EY2L3DU\n+5SHEXgoOA1b+StfY01ah4l0MS4xUb39qx0x5y+fBE7HeMMyla/uLGKWWuhzKP9w\n5Ba/9ha1ZWvbZaaRYEWTri17x351ONdBLeC5f522zBknIG+4gheOim6kTJmPAjCn\nO3IIXnmh/Oa9AK7je3bGymjdhrtbKF+HpJaSKrdVjizHTZlYUy2yq3yCNtMJcKhC\nXjNL0xmpaVYhTbvxClOnlXi6FcbYzzjz9neoRtVkAysmbw0jAA7+kmr/R3+fwsnV\n028YITdDAgMBAAECggEAAuplxJI/CDhWDJHszm/TNEwBMy/jJhwVWAww5PVFNvve\nmDHXmqpEinW6gpfc7mXqxan9ecuT62fWfeTLKOnUgxlAQtwpLCNz8HhHpoYTYJeA\nKEvKrbP+RCbFCCyr9t3D9B7OgWtRzptLssh7T6J8JCPQEC1fIJ3USWMPjnF7kWHb\n2RrPPqugTWn0m0gbhcZ6suMCjAFXjQSFvgAeLxuqPjTc/7wxqzMgu4jwzw67WZm9\n3Xt4QGnZ5rlUrGi7BLwTg/GrWNhNo1FQ+rASiIze6eV7WCWJAZgeY5NYwxBs6TDJ\nJ9QqntCMqovIZRwcgf2VrQ7pJlTzM5vDccDIEYMXQQKBgQDyBNOKnDsWbqhCaTfU\nZIDoGxUOLsYrO64s7KbaTRoRZlp7uBKM2DJAQmIzIlXqjQxlHZpqZsd0e6PzZwVz\n7QrYFxnkgak/YRuLOynVzIGlmMzoor+HQ45qXUcg3BBWKurhvoh7igXt6UgdKaVx\n7YmmKEnq7f81dfSYeAWNy1mi0wKBgQDN6s748BCxNDF0H2GlGHs8qCkFJHiUMbGI\nx5l4lALaJ1m22JIxgMprM7LxoZPCZx+Je5m+5DBKweOK0Rt+d0i7m7kwpSD0I/CJ\nd15bIe32rP6EQLeE1CNp+oJNJ2BERIuw00B8ljYHEg67dFao3D3BdfpgcjhMkVs4\nNzQMZufz0QKBgEPTpHGhTVIBGzjZgiMNM69Y/7Kk2zb8l9jRTgW6PAcKV2t67//3\nC0ZFFH5eLhP5CbNA86jEOzvi9tTdV4LguPxMpR4MVKGFlpGTuCrKEL+XLj44dlLz\nVPNsRuXnptBvYLp5ioiM6xJ9IY/CvzJJrx0ZB3ZG0xJph24/nNbbWbivAoGAJAER\nbV90W7eXiglOpnJQYfu5KGgHGUpTE2prADVJBmHpAtp9PWCahAIHIM6yqkQjtIND\nD6iQdRHPul7zoroyonMI/2NwDqAWF8MiYWbeV8pJulAihnwdMROXIuxmnakqj6Fw\nXhhZnAThRI+D84SG28PIIoL2KxUjUQH9/Mkld3ECgYAzbhDB8/h+0ijHduy+j2tO\ndvWzrsb482R6hi3PB/zf1uRzuc4MV7LTGATHSNhi+ZTGRKTwlFsdd5uifb7BR6tx\n8d5wwVjsdsmBBkr7TPkzWdNtQXkeH0Pwj6ya78KkZn/PZoXiwgfbUa2Q4QlilMHa\nQGrO9KEKvt5jvZzUYK1oSw==\n-----END PRIVATE KEY-----\n",
        "client_email": "firebase-adminsdk-fbsvc@podcase-generator.iam.gserviceaccount.com",
        "client_id": "117615707402004887836",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40podcase-generator.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase Admin initialized successfully!")
    
except Exception as e:
    print(f"❌ Firebase Admin initialization failed: {e}")
    db = None

# ============================================================
# 3️⃣ Load AI Models
# ============================================================
MODEL_NAME = "pszemraj/long-t5-tglobal-base-16384-book-summary"
print("Loading summarization model...")

try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    summarizer = pipeline("summarization", model=model, tokenizer=tokenizer)
    print("✅ AI models loaded successfully!")
except Exception as e:
    print(f"❌ Error loading AI models: {e}")
    summarizer = None

# Configure Gemini + ElevenLabs with direct API keys
GEMINI_API_KEY = "AIzaSyD70N1RH5dtQlmnInvAXYqUUHm0VCa67Uw"  # Replace with your actual Gemini API key
ELEVENLABS_API_KEY = "sk_592903a05e4f6665703df76298c2d787a70cc4f14a3bca13"  # Replace with your actual ElevenLabs API key

genai.configure(api_key=GEMINI_API_KEY)
tts_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

VOICE_MAP = {
    "ALEX": "90ipbRoKi4CpHXvKVtl0",
    "JORDAN": "s2wvuS7SwITYg8dqsJdn",
}

# ============================================================
# 4️⃣ Helper Functions
# ============================================================
def extract_content(file: UploadFile):
    if file.filename.endswith(".txt"):
        return file.file.read().decode("utf-8")

    elif file.filename.endswith(".pdf"):
        pdf_reader = PdfReader(file.file)
        text = ""
        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            text += f"--- PAGE {i+1} ---\n{page_text or ''}\n"
        return text

    else:
        raise ValueError("Unsupported file type. Only PDF or TXT allowed.")

def clean_text(raw_text: str):
    text = re.sub(r'--- PAGE \d+ ---', '', raw_text)
    text = re.sub(r'\n+', ' ', text).strip()
    return text

def summarize_text(cleaned_text: str):
    if not summarizer:
        raise HTTPException(status_code=500, detail="AI models not loaded")
    
    instruction = """
    Summarize the following text into a **concise, clear, and natural narrative** suitable for a speaker or podcast.

    Your goals:
    - Capture only the essential points in a flowing story.
    - Avoid repeating instructions or meta-comments from the text.
    - Keep the narrative easy to understand, like explaining to someone aloud.
    - Use smooth transitions between ideas.
    - Maintain factual accuracy and include key examples if they clarify the point.
    - Target a length of 150–200 words for short chapters or sections.

    Do not include bullet points, lists, stage directions, or any formatting. 
    Write as if you are narrating the content naturally to an audience.

    Now, summarize the following text:
    """
    prompt = instruction + "\n\nText:\n" + cleaned_text
    result = summarizer(prompt, max_length=360, min_length=200, do_sample=True, temperature=0.7)
    return result[0]["summary_text"]

def generate_podcast_script(summary_text: str):
    prompt = f"""
    You are a professional podcast scriptwriter for a popular tech show.

    Write a **3–4 minute** (approximately 400–500 words) **dynamic, natural conversation** between two hosts — **Alex** and **Jordan** — discussing the following summary:

    **Summary:**
    {summary_text}

    **Guidelines:**
    - Make the conversation **smooth, flowing, and easy to read aloud** for TTS.
    - Each speaker's line must start with their name exactly as: 
        - Alex: ...
        - Jordan: ...
    - Alternate naturally between Alex and Jordan.
    - Avoid **any stage directions, emotion tags, or bracketed instructions**.
    - Use **natural pauses, punctuation, and sentence rhythm** to guide TTS intonation.
    - Keep the tone **friendly, informative, and engaging**, like a real podcast discussion between two tech enthusiasts.
    - Cover the full narrative: origins → evolution → breakthroughs → ethical considerations → future vision.
    - Include a **hook at the start** and a **thought-provoking takeaway at the end**.
    - Do **not** use bullet points or any lists.
    - Make sure each line is **short enough to be clearly read by TTS**, ideally 1–2 sentences per line, so that it can be synthesized smoothly.

    **Format exactly like this:**
    Alex: ...
    Jordan: ...
    Alex: ...
    ...

    This script will be **directly fed to ElevenLabs TTS**, so clarity, line separation, and readability are critical.
    """
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text

def parse_script(script_text: str):
    pattern = re.compile(r"^\s*([A-Za-z]+):\s*(.*)$", re.MULTILINE)
    cue_pattern = re.compile(r"\[.*?\]|\(.*?\)")
    dialogue = []
    for match in pattern.finditer(script_text):
        speaker = match.group(1).upper()
        text = cue_pattern.sub('', match.group(2)).strip()
        if speaker in VOICE_MAP and text:
            dialogue.append((VOICE_MAP[speaker], text))
    return dialogue

def generate_tts_audio(script: str):
    dialogue = parse_script(script)
    combined_audio = BytesIO()
    for voice_id, text in dialogue:
        audio_stream = tts_client.text_to_speech.convert(
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            text=text
        )
        for chunk in audio_stream:
            if chunk:
                combined_audio.write(chunk)
    combined_audio.seek(0)
    
    # Create audio directory if it doesn't exist
    os.makedirs("audio_outputs", exist_ok=True)
    
    output_path = f"audio_outputs/podcast_{uuid.uuid4().hex[:8]}.mp3"
    with open(output_path, "wb") as f:
        f.write(combined_audio.read())
    return output_path

# ============================================================
# 5️⃣ Store in Firestore Function
# ============================================================
def store_in_firestore(podcast_data: dict):
    if db is None:
        print("⚠️ Firebase not initialized, skipping Firestore storage")
        return None
    
    try:
        podcast_id = str(uuid.uuid4())
        podcast_data["id"] = podcast_id
        podcast_data["createdAt"] = firestore.SERVER_TIMESTAMP
        
        doc_ref = db.collection("podcasts").document(podcast_id)
        doc_ref.set(podcast_data)
        
        print(f"✅ Podcast stored in Firestore with ID: {podcast_id}")
        return podcast_id
    except Exception as e:
        print(f"❌ Error storing in Firestore: {e}")
        return None

# ============================================================
# 6️⃣ Main Endpoint
# ============================================================
@app.post("/upload_file/")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Validate file type
        if not file.filename.endswith(('.pdf', '.txt')):
            raise HTTPException(status_code=400, detail="Only PDF and TXT files are allowed")

        # Step 1: Extract + clean
        raw_content = extract_content(file)
        cleaned_text = clean_text(raw_content)

        # Step 2: Summarize
        summary = summarize_text(cleaned_text)

        # Step 3: Generate podcast script
        podcast_script = generate_podcast_script(summary)

        # Step 4: Convert to speech
        audio_path = generate_tts_audio(podcast_script)

        # Step 5: Prepare data for Firestore
        podcast_data = {
            "fileName": file.filename,
            "fileType": file.content_type,
            "summary": summary,
            "podcastScript": podcast_script,
            "audioPath": audio_path,
            "status": "completed"
        }

        # Step 6: Store in Firestore
        podcast_id = store_in_firestore(podcast_data)

        response_data = {
            "id": podcast_id,
            "summary": summary,
            "podcast_script": podcast_script,
            "audio_path": audio_path,
            "message": "✅ Podcast generated successfully!"
        }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

# Health check endpoint
@app.get("/")
async def health_check():
    return {"status": "healthy", "message": "Podcast Generator API is running!"}

# Get all podcasts endpoint
@app.get("/podcasts/")
async def get_podcasts():
    if db is None:
        return {"podcasts": [], "message": "Firebase not configured"}
    
    try:
        podcasts_ref = db.collection("podcasts")
        docs = podcasts_ref.stream()
        
        podcasts = []
        for doc in docs:
            podcast_data = doc.to_dict()
            # Convert Firestore timestamp to ISO string
            if 'createdAt' in podcast_data:
                podcast_data['createdAt'] = podcast_data['createdAt'].isoformat()
            podcasts.append(podcast_data)
        
        return {"podcasts": podcasts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching podcasts: {str(e)}")

# Get single podcast by ID
@app.get("/podcasts/{podcast_id}")
async def get_podcast(podcast_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Firebase not configured")
    
    try:
        doc_ref = db.collection("podcasts").document(podcast_id)
        doc = doc_ref.get()
        
        if doc.exists:
            podcast_data = doc.to_dict()
            if 'createdAt' in podcast_data:
                podcast_data['createdAt'] = podcast_data['createdAt'].isoformat()
            return podcast_data
        else:
            raise HTTPException(status_code=404, detail="Podcast not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching podcast: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)