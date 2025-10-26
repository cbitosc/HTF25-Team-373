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
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 1️⃣ Initialize FastAPI
# ============================================================
app = FastAPI(title="Podcast Generator API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 2️⃣ Initialize Firebase Admin
# ============================================================
try:
    # Method 1: Try to load from service account file first
    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    if service_account_path and os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        print("✅ Firebase initialized from service account file")
    else:
        # Method 2: Load from environment variables
        service_account_info = {
            "type": "service_account",
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL"),
            "universe_domain": "googleapis.com"
        }
        
        if service_account_info["private_key"]:
            cred = credentials.Certificate(service_account_info)
            print("✅ Firebase initialized from environment variables")
        else:
            raise Exception("Firebase credentials not found")
    
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

# Configure Gemini + ElevenLabs
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY environment variable is required")
if not ELEVENLABS_API_KEY:
    raise Exception("ELEVENLABS_API_KEY environment variable is required")

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
    
    os.makedirs("audio_outputs", exist_ok=True)
    output_path = f"audio_outputs/podcast_{uuid.uuid4().hex[:8]}.mp3"
    
    with open(output_path, "wb") as f:
        f.write(combined_audio.read())
    return output_path

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
# 5️⃣ Main Endpoint
# ============================================================
@app.post("/upload_file/")
async def upload_file(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith(('.pdf', '.txt')):
            raise HTTPException(status_code=400, detail="Only PDF and TXT files are allowed")

        raw_content = extract_content(file)
        cleaned_text = clean_text(raw_content)
        summary = summarize_text(cleaned_text)
        podcast_script = generate_podcast_script(summary)
        audio_path = generate_tts_audio(podcast_script)

        podcast_data = {
            "fileName": file.filename,
            "fileType": file.content_type,
            "summary": summary,
            "podcastScript": podcast_script,
            "audioPath": audio_path,
            "status": "completed"
        }

        podcast_id = store_in_firestore(podcast_data)

        return {
            "id": podcast_id,
            "summary": summary,
            "podcast_script": podcast_script,
            "audio_path": audio_path,
            "message": "✅ Podcast generated successfully!"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@app.get("/")
async def health_check():
    return {"status": "healthy", "message": "Podcast Generator API is running!"}

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
            if 'createdAt' in podcast_data:
                podcast_data['createdAt'] = podcast_data['createdAt'].isoformat()
            podcasts.append(podcast_data)
        
        return {"podcasts": podcasts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching podcasts: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)