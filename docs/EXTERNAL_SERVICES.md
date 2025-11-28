# External Services & APIs Documentation

This document provides a comprehensive overview of all external tools, APIs, and services integrated into the STServer backend.

## Table of Contents

1. [AI & Machine Learning Services](#ai--machine-learning-services)
2. [Database & Storage](#database--storage)
3. [Communication Services](#communication-services)
4. [Conversational AI Framework](#conversational-ai-framework)
5. [Infrastructure & Monitoring](#infrastructure--monitoring)
6. [Authentication & Security](#authentication--security)
7. [Cost Overview](#cost-overview)

---

## AI & Machine Learning Services

### 1. OpenAI

**Purpose:** Text generation, story creation, lullaby lyrics generation

**API Endpoint:** `https://api.openai.com/v1/`

**Models Used:**
- `gpt-4o` - Advanced story generation with image understanding
- `gpt-4o-mini` - Fast, cost-effective story generation (default)
- `gpt-3.5-turbo` - Legacy support

**Use Cases:**
```python
# Story Generation
story_service.py:
- Generate story scenes with character consistency
- Create structured narratives with [Beginning], [Middle], [End] tags
- Character description and scene descriptions

# Lullaby Lyrics Generation
lullaby_service.py:
- Generate lyrics in [Verse], [Chorus], [Bridge], [Outro] format
- 450 character target, 500 character strict maximum
- Temperature: 0.7, max_tokens: 300
```

**Configuration:**
```python
# Environment Variables
OPENAI_API_KEY=sk-...

# Usage
from openai import OpenAI
client = OpenAI(api_key=settings.openai_api_key)
```

**Cost:** 
- GPT-4o: ~$0.005 per story scene
- GPT-4o-mini: ~$0.001 per story scene
- Lullaby lyrics: ~$0.002 per generation

**Rate Limits:**
- Tier 1: 500 requests/day
- Tier 2: 3,500 requests/day

**Documentation:** https://platform.openai.com/docs

---

### 2. Replicate

**Purpose:** Image generation (Flux models), Music generation (MiniMax Music-1.5)

**API Endpoint:** `https://api.replicate.com/v1/`

**Models Used:**

#### Image Generation:
- `black-forest-labs/flux-1.1-pro` - High-quality story images (768x768 → upscaled to 1290x2796)
- `black-forest-labs/flux-dev` - Development/testing
- `adirik/flux-cinestill` - Cinematic style images

#### Music Generation:
- `minimax/music-01` (MiniMax Music-1.5) - AI music from lyrics
  - Output: MP3, 44.1kHz, 256kbps
  - Duration: ~1-2 minutes
  - Typical size: 2-4 MB

**Use Cases:**
```python
# Image Generation (media_service.py)
output = replicate.run(
    "black-forest-labs/flux-1.1-pro",
    input={
        "prompt": prompt,
        "aspect_ratio": "1:1",
        "output_format": "png",
        "output_quality": 100
    }
)

# Music Generation (lullaby_service.py)
output = replicate.run(
    "minimax/music-01",
    input={
        "prompt": "soft, loving, lullaby, sleep music, gentle piano, calm",
        "lyrics": lyrics_text
    }
)
```

**Configuration:**
```python
# Environment Variables
REPLICATE_API_TOKEN=r8_...

# Usage
import replicate
replicate.Client(api_token=settings.replicate_api_token)
```

**Cost:**
- Flux-1.1-pro: ~$0.04 per image
- Flux-dev: ~$0.01 per image
- MiniMax Music-1.5: ~$0.10-0.20 per generation

**Timeout:** 300 seconds (5 minutes) for music generation

**Documentation:** https://replicate.com/docs

---

### 3. Cartesia AI (Primary TTS Service)

**Purpose:** Text-to-Speech (TTS), Voice Cloning, Conversational AI

**API Endpoint:** `https://api.cartesia.ai`

**API Version:** `2024-06-10`

**Models:**
- `sonic-3-2025-10-27` - Latest model with best quality (multilingual)

**Features:**
- Ultra-low latency TTS (ideal for real-time conversations)
- Voice cloning from audio samples
- Multilingual support (English, Spanish, French, German, Italian, Russian, Arabic)
- Emotion control (neutral, happy, sad, angry, surprised)
- Speed control (slowest, slow, normal, fast, fastest)
- Volume control (0.5-2.0x gain)

**Default Voice:**
- ID: `79a125e8-cd45-4c13-8a67-188112f4dd22`
- Description: "British Lady" - Professional female narrator

**Use Cases:**
```python
# Story Narration (cartesia_service.py)
audio_bytes = await cartesia_service.generate_speech_cartesia(
    text="Once upon a time...",
    voice_id=user_voice_id,
    language="en",
    emotion="neutral",
    volume_gain=3.0  # Clamped to 2.0 max
)

# Voice Cloning
voice_id = await cartesia_service.clone_voice_from_audio(
    audio_data=audio_bytes,
    user_id=user_id,
    voice_name="Mom's Voice",
    language="en"
)

# Batch Generation
audio_files = await cartesia_service.generate_speech_batch_cartesia(
    scenes=[{"text": "Scene 1..."}, {"text": "Scene 2..."}],
    user_id=user_id,
    language="en"
)
```

**Configuration:**
```python
# Environment Variables
CARTESIA_API_KEY=sk-...

# Usage
from app.services.ai.cartesia_service import CartesiaService
service = CartesiaService()
```

**Audio Output:**
- Format: MP3
- Sample Rate: 44.1kHz
- Encoding: MP3 128kbps

**Cost:**
- TTS: ~$0.015 per 1,000 characters
- Voice cloning: ~$1.00 per voice clone

**Rate Limits:**
- 100 requests/minute
- Retry logic: 3 attempts with exponential backoff (2s, 4s, 8s)

**Voice Clone Management:**
```python
# Store in Firestore: users/{user_id}/voice_clones/{clone_id}
{
    "voice_id": "uuid-here",
    "provider": "cartesia",
    "voice_name": "Mom's Voice",
    "created_at": timestamp,
    "is_active": true
}
```

**Documentation:** https://docs.cartesia.ai

---

### 4. Deepgram

**Purpose:** Speech-to-Text (STT) for conversational AI

**API Endpoint:** `https://api.deepgram.com/v1/`

**Use Cases:**
```python
# Real-time Speech Recognition (conversation.py)
from pipecat.services.deepgram import DeepgramSTTService

stt = DeepgramSTTService(api_key=settings.deepgram_api_key)
```

**Configuration:**
```python
# Environment Variables
DEEPGRAM_API_KEY=...
```

**Cost:** ~$0.0043 per minute of audio

**Documentation:** https://developers.deepgram.com

---

### 5. Groq

**Purpose:** Fast LLM inference (alternative to OpenAI for conversations)

**API Endpoint:** `https://api.groq.com/openai/v1/`

**Models:** Llama 3, Mixtral, etc.

**Configuration:**
```python
# Environment Variables
GROQ_API_KEY=gsk_...
```

**Cost:** Free tier available, very competitive pricing

**Documentation:** https://console.groq.com/docs

---

### 6. Freesound

**Purpose:** Ambient sound effects for stories

**API Endpoint:** `https://freesound.org/apiv2/`

**Use Cases:**
```python
# Ambient Audio Mixing (media_service.py)
ambient_keywords = ["rain", "forest", "night"]
# Service searches Freesound API for matching effects
```

**Configuration:**
```python
# Environment Variables
FREESOUND_API_KEY=...
```

**Cost:** Free (requires attribution)

**Documentation:** https://freesound.org/docs/api/

---

## Database & Storage

### 1. Firebase (Google Cloud)

**Services Used:**
- Firebase Authentication
- Cloud Firestore (NoSQL database)
- Firebase Storage (file storage)

**Purpose:** User authentication, data persistence, file storage

#### Firebase Authentication

**Use Cases:**
- User registration and login
- ID token verification
- Custom token generation (for IoT devices)

```python
# Verify Firebase ID Token
from firebase_admin import auth

decoded_token = auth.verify_id_token(token)
user_id = decoded_token['uid']
```

#### Cloud Firestore

**Collections:**
```
users/
  {user_id}/
    - email, name, account_status, created_at
    - voice_clones/
        {clone_id}: voice_id, provider, created_at
    - child_profiles/
        {profile_id}: name, age, avatar_url
    
stories/
  {story_id}/
    - title, scenes, user_id, created_at
    
lullabies/
  {lullaby_id}/
    - description, lyrics, audio_url, user_id, created_at
    
devices/
  {device_id}/
    - owner_id, status, firmware_version
    
push_tokens/
  {token}/
    - user_id, device_token, platform
    
notifications/
  {notification_id}/
    - user_id, title, body, sent_at, read
```

**Query Patterns:**
```python
# Get user stories (newest first)
stories = db.collection('stories')\
    .where('user_id', '==', user_id)\
    .order_by('created_at', direction='DESCENDING')\
    .limit(20)\
    .stream()

# Get active voice clone
voice_doc = db.collection('users')\
    .document(user_id)\
    .collection('voice_clones')\
    .where('is_active', '==', True)\
    .limit(1)\
    .stream()
```

#### Firebase Storage

**Bucket Structure:**
```
storyteller-7ece7.firebasestorage.app/
  stories/
    {user_id}/
      {story_id}/
        scene_1_image.jpg
        scene_1_audio.ogg
        scene_2_image.jpg
        scene_2_audio.ogg
  
  lullabies/
    {user_id}/
      {lullaby_id}.mp3
  
  avatars/
    {user_id}/
      profile.jpg
  
  voice_samples/
    {user_id}/
      sample.wav
```

**Usage:**
```python
from firebase_admin import storage

bucket = storage.bucket()
blob = bucket.blob(f"lullabies/{user_id}/{lullaby_id}.mp3")
blob.upload_from_string(audio_data, content_type='audio/mpeg')
blob.make_public()
url = blob.public_url
```

**Configuration:**
```python
# firebase-credentials.json
{
  "type": "service_account",
  "project_id": "storyteller-7ece7",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "...",
  "storage_bucket": "storyteller-7ece7.firebasestorage.app"
}

# Environment Variables
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
FIREBASE_STORAGE_BUCKET=storyteller-7ece7.firebasestorage.app
FIREBASE_WEB_API_KEY=...
```

**Cost:**
- Firestore: $0.18/GB stored, $0.06 per 100k reads
- Storage: $0.026/GB/month, $0.10/GB egress
- Authentication: Free for most use cases

**Documentation:** 
- https://firebase.google.com/docs/auth
- https://firebase.google.com/docs/firestore
- https://firebase.google.com/docs/storage

---

### 2. MinIO (Self-Hosted S3-Compatible Storage)

**Purpose:** Alternative storage backend (legacy/optional)

**Endpoint:** `http://34.42.234.149:9000`

**Configuration:**
```python
# Environment Variables
MINIO_ENDPOINT=http://34.42.234.149:9000
MINIO_ROOT_USER=YOURACCESS
MINIO_ROOT_PASSWORD=YOURSECRET
MINIO_BUCKET=media
```

**Status:** Currently not actively used (Firebase Storage is primary)

**Documentation:** https://min.io/docs

---

## Communication Services

### 1. Expo Push Notifications

**Purpose:** Push notifications to mobile devices (iOS/Android)

**API Endpoint:** `https://exp.host/--/api/v2/push/send`

**Use Cases:**
```python
# Send Push Notification (notification_service.py)
async def send_push_notification(
    self,
    user_id: str,
    title: str,
    body: str,
    data: dict = None
):
    # Get user's push tokens
    tokens = await self.get_user_tokens(user_id)
    
    # Send via Expo Push API
    for token in tokens:
        payload = {
            "to": token,
            "title": title,
            "body": body,
            "data": data,
            "sound": "default",
            "priority": "high"
        }
```

**Token Format:** `ExponentPushToken[...]`

**Features:**
- iOS and Android support
- Badge counts
- Custom sound
- Data payload
- Deep linking

**Cost:** Free

**Documentation:** https://docs.expo.dev/push-notifications/overview/

---

### 2. SMTP Email Service

**Purpose:** Email notifications (verification, password reset)

**Default Provider:** Gmail SMTP

**Configuration:**
```python
# Environment Variables
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
```

**Use Cases:**
```python
# Send Verification Email (email_service.py)
await email_service.send_email(
    to_email=user_email,
    subject="Verify Your Email",
    body="Click here to verify..."
)
```

**Library Used:** `aiosmtplib` (async SMTP)

**Cost:** Free (Gmail), $0.10/email (SendGrid/SES)

**Documentation:** 
- Gmail: https://support.google.com/mail/answer/7126229
- SendGrid: https://docs.sendgrid.com
- AWS SES: https://docs.aws.amazon.com/ses/

---

### 3. MQTT Broker (IoT Device Communication)

**Purpose:** Real-time messaging with IoT devices

**Default Broker:** `localhost:1883`

**Configuration:**
```python
# Environment Variables
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=
MQTT_ENABLED=True
```

**Use Cases:**
```python
# Device Communication (iot_connection.py)
# Topics:
# - device/{device_id}/commands
# - device/{device_id}/status
# - device/{device_id}/queue
```

**Library Used:** `paho-mqtt`

**Protocol:** MQTT 3.1.1

**Cost:** Free (self-hosted), $0.08/million messages (AWS IoT Core)

**Documentation:** https://mqtt.org/

---

## Conversational AI Framework

### Pipecat AI

**Purpose:** Real-time conversational AI with WebRTC

**GitHub:** https://github.com/pipecat-ai/pipecat

**Components Used:**
- WebRTC transport (`aiortc`)
- Deepgram STT integration
- Cartesia TTS integration
- OpenAI LLM integration
- VAD (Voice Activity Detection) with Silero

**Use Cases:**
```python
# Real-time Conversation (conversation.py)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.services.cartesia.tts import CartesiaHttpTTSService
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.openai import OpenAILLMService

# Build pipeline: Audio → STT → LLM → TTS → Audio
```

**Dependencies:**
```
pipecat-ai
aiortc          # WebRTC
av              # Audio/video processing
pyaudio         # Audio I/O
numpy           # Audio processing
scipy           # Signal processing
torch           # Silero VAD
torchaudio      # Audio processing
```

**Features:**
- Sub-second latency
- Voice Activity Detection (VAD)
- Real-time streaming audio
- Context management
- Function calling

**Documentation:** https://docs.pipecat.ai

---

## Infrastructure & Monitoring

### 1. Sentry

**Purpose:** Error tracking and performance monitoring

**Configuration:**
```python
# Environment Variables
SENTRY_DSN=https://...@sentry.io/...

# Usage
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    integrations=[FastApiIntegration()]
)
```

**Features:**
- Error tracking
- Performance monitoring
- Release tracking
- User feedback
- Breadcrumbs

**Cost:** Free tier (5k events/month), Paid plans start at $26/month

**Documentation:** https://docs.sentry.io

---

### 2. FastAPI (Web Framework)

**Purpose:** Modern, high-performance Python web framework

**Features:**
- Automatic OpenAPI documentation
- Pydantic validation
- Async/await support
- WebSocket support
- Dependency injection

**Documentation:** https://fastapi.tiangolo.com

---

## Authentication & Security

### 1. JWT (JSON Web Tokens)

**Purpose:** Secure authentication for IoT devices and apps

**Libraries:**
- `pyjwt[crypto]` - JWT encoding/decoding
- `cryptography` - RSA key pair generation

**Key Types:**
- App JWT (RSA 2048-bit) - App-to-server auth
- Device JWT (RSA 2048-bit) - Device-to-server auth

**Token Storage:**
```
keys/
  app-jwt.pem        # App private key
  app-jwt.pub        # App public key
  device-jwt.pem     # Device private key
  device-jwt.pub     # Device public key
```

**Configuration:**
```python
# Environment Variables
JWT_PRIVATE_KEY_PATH=./keys/app-jwt.pem
JWT_PUBLIC_KEY_PATH=./keys/app-jwt.pub
DEVICE_JWT_TTL_SECONDS=14400  # 4 hours
```

**Documentation:** https://jwt.io

---

### 2. Argon2

**Purpose:** Password hashing (more secure than bcrypt)

**Library:** `argon2-cffi`

**Use Cases:**
```python
from argon2 import PasswordHasher
ph = PasswordHasher()

# Hash password
hashed = ph.hash(password)

# Verify password
ph.verify(hashed, password)
```

**Documentation:** https://argon2-cffi.readthedocs.io

---

### 3. HMAC Signature Verification

**Purpose:** IoT device request authentication

**Configuration:**
```python
# Environment Variables
HMAC_TOLERANCE_SECONDS=300  # 5 minutes
DEVICE_SECRET_KEY=change-this-secret-key-in-production
```

**Use Cases:**
```python
# Verify HMAC signature on device requests
# Prevents replay attacks with timestamp validation
```

---

## Cost Overview

### Monthly Cost Estimates (per 1,000 users)

**AI Services:**
- OpenAI (stories): ~$50-100/month
- Replicate (images): ~$200-400/month
- Replicate (music): ~$50-150/month
- Cartesia (TTS): ~$100-200/month
- Deepgram (STT): ~$50-100/month

**Database & Storage:**
- Firebase Firestore: ~$20-50/month
- Firebase Storage: ~$30-60/month
- Firebase Auth: Free

**Communication:**
- Expo Push: Free
- Email (SMTP): Free (Gmail) or ~$10/month (SendGrid)

**Infrastructure:**
- Sentry: Free or $26/month
- Hosting: Variable (Cloud Run, EC2, etc.)

**Total Estimated Cost:** $500-1,200/month for 1,000 active users

### Cost Optimization Strategies

1. **Caching:** Cache generated stories/lullabies to avoid regeneration
2. **Batch Processing:** Generate multiple scenes in parallel
3. **Model Selection:** Use gpt-4o-mini instead of gpt-4o when possible
4. **Rate Limiting:** Limit generations per user per day
5. **Content Reuse:** Encourage users to reuse existing content

---

## Environment Variables Summary

```bash
# AI Services
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
REPLICATE_API_TOKEN=r8_...
CARTESIA_API_KEY=sk-...
DEEPGRAM_API_KEY=...
FREESOUND_API_KEY=...

# Firebase
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
FIREBASE_STORAGE_BUCKET=storyteller-7ece7.firebasestorage.app
FIREBASE_WEB_API_KEY=...

# MinIO (Optional)
MINIO_ENDPOINT=http://34.42.234.149:9000
MINIO_ROOT_USER=YOURACCESS
MINIO_ROOT_PASSWORD=YOURSECRET
MINIO_BUCKET=media

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com

# MQTT
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=
MQTT_ENABLED=True

# JWT & Security
JWT_PRIVATE_KEY_PATH=./keys/app-jwt.pem
JWT_PUBLIC_KEY_PATH=./keys/app-jwt.pub
DEVICE_PRIVATE_KEY_PATH=./keys/device-jwt.pem
DEVICE_PUBLIC_KEY_PATH=./keys/device-jwt.pub
DEVICE_SECRET_KEY=change-this-secret-key-in-production
HMAC_TOLERANCE_SECONDS=300

# Monitoring
SENTRY_DSN=https://...@sentry.io/...

# Story Configuration
STORY_MAX_SCENES=5
STORY_AUDIO_FORMAT=ogg
STORY_IMAGE_SIZE=1290x2796
STORY_LLM_MODEL=gpt-4o-mini
```

---

## Service Health Checks

### Test Connectivity

```python
# OpenAI
from openai import OpenAI
client = OpenAI(api_key=settings.openai_api_key)
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "test"}]
)

# Replicate
import replicate
replicate.run("black-forest-labs/flux-dev", input={"prompt": "test"})

# Cartesia
from app.services.ai.cartesia_service import CartesiaService
service = CartesiaService()
audio = await service.generate_speech_cartesia("test")

# Firebase
from firebase_admin import auth, firestore, storage
db = firestore.client()
bucket = storage.bucket()
user = auth.get_user("test_user_id")

# Expo Push
import httpx
response = await httpx.post(
    "https://exp.host/--/api/v2/push/send",
    json={"to": "ExponentPushToken[test]", "title": "test"}
)
```

---

## Migration Guide

### Moving from ElevenLabs to Cartesia

**Why:** Lower latency, better quality, cost-effective

**Steps:**

1. Update voice IDs in Firestore:
```python
# Old ElevenLabs format: "pNInz6obpgDQGcFmaJgB" (20-24 chars, no dashes)
# New Cartesia format: "79a125e8-cd45-4c13-8a67-188112f4dd22" (UUID with dashes)
```

2. Create new voice clones:
```python
voice_id = await cartesia_service.clone_voice_from_audio(
    audio_data=audio_bytes,
    user_id=user_id,
    voice_name="User's Voice"
)
```

3. Update voice_clones collection:
```python
db.collection('users').document(user_id).collection('voice_clones').add({
    "voice_id": voice_id,
    "provider": "cartesia",  # Changed from "elevenlabs"
    "created_at": firestore.SERVER_TIMESTAMP
})
```

**Automatic Detection:** The system automatically detects ElevenLabs voice IDs and logs warnings, falling back to the default Cartesia voice.

---

## Support & Resources

### API Keys Management
- Store in `.env` file (never commit)
- Use separate keys for dev/staging/production
- Rotate keys quarterly

### Rate Limit Handling
- Implement exponential backoff
- Queue requests during high traffic
- Monitor usage dashboards

### Error Handling
- Log all API errors to Sentry
- Implement fallback strategies
- Provide user-friendly error messages

### Documentation Links
- [OpenAI Platform](https://platform.openai.com)
- [Replicate Docs](https://replicate.com/docs)
- [Cartesia API](https://docs.cartesia.ai)
- [Firebase Console](https://console.firebase.google.com)
- [Expo Docs](https://docs.expo.dev)
- [Pipecat AI](https://docs.pipecat.ai)

---

## Changelog

**Last Updated:** November 27, 2025

**Recent Changes:**
- Added MiniMax Music-1.5 for lullaby generation
- Migrated from ElevenLabs to Cartesia for TTS
- Implemented Pipecat AI for conversational features
- Added Deepgram for speech-to-text
- Updated Firebase Storage structure

---

For questions or issues, please refer to the main project documentation or contact the development team.
