# Developer Guide - ESP32 Storytelling Server

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Setup & Installation](#setup--installation)
5. [Development Workflow](#development-workflow)
6. [Key Technologies](#key-technologies)
7. [Testing](#testing)
8. [Deployment](#deployment)
9. [Common Tasks](#common-tasks)

---

## Project Overview

The ESP32 Storytelling Server is a production-grade FastAPI backend that powers an AI-driven storytelling platform. It handles story generation, IoT device management, conversational AI, user authentication, and real-time communication.

### Core Features
- **AI Story Generation**: Creates personalized children's stories with audio and images
- **IoT Device Management**: Manages ESP32-based storytelling devices
- **Conversational AI**: Real-time WebRTC-based voice conversations
- **User Management**: Firebase authentication with multi-profile support
- **Queue Management**: Robust background task processing with failover
- **Admin Dashboard**: System monitoring and user management

---

## Architecture

### High-Level Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Mobile App     │────▶│  FastAPI Server  │◀────│  IoT Devices    │
│  (React Native) │     │                  │     │  (ESP32)        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ├──▶ Firebase (Auth & Storage)
                               ├──▶ OpenAI (Story Generation)
                               ├──▶ Cartesia (Text-to-Speech)
                               ├──▶ SeeDream (Image Generation)
                               └──▶ Deepgram (Speech-to-Text)
```

### Service Layer Architecture

```
app/
├── routers/          # API endpoints (Controllers)
├── services/         # Business logic
├── models/           # Data models (Pydantic)
├── utils/            # Helpers
├── middleware/       # Request interceptors
└── database/         # Database connections
```

### Request Flow

```
1. Client Request → 2. Router → 3. Middleware (Auth) 
   → 4. Service Layer → 5. External APIs/DB → 6. Response
```

---

## Project Structure

```
STServer/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Configuration & environment variables
│   ├── dependencies.py            # Shared dependencies (auth, services)
│   │
│   ├── routers/                   # API endpoints
│   │   ├── auth.py               # Authentication (signup/signin)
│   │   ├── stories.py            # Story generation & management
│   │   ├── users.py              # User profile management
│   │   ├── iot.py                # IoT device management
│   │   ├── conversation.py       # WebRTC conversational AI
│   │   ├── admin.py              # Admin dashboard & management
│   │   ├── analytics.py          # Analytics & metrics
│   │   ├── sharing.py            # Story sharing features
│   │   ├── reference_images.py   # Character image uploads
│   │   ├── health.py             # Health checks
│   │   ├── ntp.py                # Time synchronization
│   │   └── websocket.py          # WebSocket connections
│   │
│   ├── services/                  # Business logic layer
│   │   ├── auth_service.py       # Authentication business logic
│   │   ├── user_service.py       # User management
│   │   ├── story_service.py      # Story generation orchestration
│   │   ├── parallel_story_service.py  # Concurrent story generation
│   │   ├── enhanced_background_service.py  # Queue management
│   │   ├── media_service.py      # Audio/image generation
│   │   ├── storage_service.py    # Firebase storage operations
│   │   ├── cartesia_service.py   # Text-to-speech (Cartesia)
│   │   ├── elevenlabs_service.py # Text-to-speech (ElevenLabs)
│   │   ├── iot_device_service_firestore.py  # IoT device management
│   │   ├── account_status_service.py  # Subscription management
│   │   ├── analytics_service.py  # Analytics & metrics
│   │   └── email_service.py      # Email notifications
│   │
│   ├── models/                    # Pydantic data models
│   │   ├── auth.py               # Authentication models
│   │   ├── user.py               # User & profile models
│   │   ├── story.py              # Story models
│   │   ├── iot_api_models.py     # IoT device models
│   │   └── analytics.py          # Analytics models
│   │
│   ├── utils/                     # Utility functions
│   │   ├── firebase_init.py      # Firebase initialization
│   │   └── helpers.py            # Common helper functions
│   │
│   ├── middleware/                # Request interceptors
│   │   └── iot_auth.py           # IoT device authentication
│   │
│   └── database/                  # Database connections
│       └── iot_connection.py     # Database connection pool
│
├── tests/                         # Test suites
│   ├── test_queue_management.py
│   └── test_queue_edge_cases.py
│
├── docs/                          # Documentation
│   ├── DEVELOPER_GUIDE.md        # This file
│   ├── FRONTEND_API_GUIDE.md     # API documentation for frontend
│   ├── PROJECT_OVERVIEW.md       # High-level overview
│   ├── IMPLEMENTATION_DETAILS.md # Deep-dive technical docs
│   ├── QUEUE_MANAGEMENT.md       # Queue system docs
│   ├── CONVERSATIONAL_AI_DOCS.md # WebRTC AI docs
│   └── MOBILE_WEBRTC_GUIDE.md    # Mobile WebRTC integration
│
├── scripts/                       # Utility scripts
├── static/                        # Static files
├── pipecat/                       # Pipecat library (WebRTC AI)
├── keys/                          # API keys & certificates
├── firebase-credentials.json      # Firebase service account
├── .env                          # Environment variables
├── requirements.txt              # Python dependencies
└── README.md                     # Project README
```

---

## Setup & Installation

### Prerequisites
- **Python 3.11+**
- **Firebase Project** (with Firestore & Storage enabled)
- **API Keys**: OpenAI, Cartesia, SeeDream, Deepgram, Freesound

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd STServer
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup Firebase**
   - Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
   - Enable Firestore Database
   - Enable Firebase Storage
   - Enable Authentication (Email/Password)
   - Download service account JSON and save as `firebase-credentials.json`

5. **Configure Environment Variables**
   Create a `.env` file:
   ```bash
   # Firebase
   FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
   FIREBASE_STORAGE_BUCKET=your-project.appspot.com
   
   # API Keys
   OPENAI_API_KEY=sk-...
   CARTESIA_API_KEY=...
   SEEDREAM_API_KEY=...
   DEEPGRAM_API_KEY=...
   FREESOUND_API_KEY=...
   
   # Firebase Web API Key (for authentication)
   FIREBASE_WEB_API_KEY=...
   
   # Server Configuration
   DEBUG=true
   VERBOSE_LOGGING=true
   PORT=8000
   CORS_ORIGINS=http://localhost:3000,http://localhost:19006
   
   # Admin Credentials
   ADMIN_USERNAME=root
   ADMIN_PASSWORD=root
   ```

6. **Run the Server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Verify Installation**
   - Open http://localhost:8000/docs for API documentation
   - Check http://localhost:8000/health for health status

---

## Development Workflow

### Starting Development Server

```bash
# Activate virtual environment
source .venv/bin/activate

# Run with auto-reload
uvicorn app.main:app --reload --port 8000
```

### Code Organization Principles

1. **Separation of Concerns**
   - Routers: Handle HTTP requests/responses only
   - Services: Contain business logic
   - Models: Define data structures
   - Utils: Reusable helper functions

2. **Dependency Injection**
   ```python
   # Good: Use FastAPI dependency injection
   @router.get("/stories")
   async def get_stories(
       storage_service: StorageService = Depends(get_storage_service)
   ):
       return await storage_service.get_user_stories(user_id)
   
   # Bad: Don't instantiate services in routes
   @router.get("/stories")
   async def get_stories():
       storage_service = StorageService()  # ❌ Don't do this
       return await storage_service.get_user_stories(user_id)
   ```

3. **Error Handling**
   ```python
   try:
       result = await some_operation()
       return {"success": True, "data": result}
   except ValueError as e:
       raise HTTPException(status_code=400, detail=str(e))
   except Exception as e:
       logger.error(f"Unexpected error: {e}")
       raise HTTPException(status_code=500, detail="Internal server error")
   ```

### Adding New Features

#### 1. Adding a New Endpoint

**Step 1**: Create/update the model in `app/models/`
```python
# app/models/story.py
class NewFeatureRequest(BaseModel):
    user_id: str
    feature_data: str
```

**Step 2**: Add business logic in `app/services/`
```python
# app/services/feature_service.py
class FeatureService:
    async def process_feature(self, request: NewFeatureRequest):
        # Business logic here
        return result
```

**Step 3**: Create the endpoint in `app/routers/`
```python
# app/routers/features.py
from fastapi import APIRouter, Depends
from app.models.story import NewFeatureRequest
from app.services.feature_service import FeatureService

router = APIRouter(prefix="/features", tags=["features"])

@router.post("/process")
async def process_feature(
    request: NewFeatureRequest,
    feature_service: FeatureService = Depends(get_feature_service)
):
    return await feature_service.process_feature(request)
```

**Step 4**: Register the router in `app/main.py`
```python
from app.routers import features
app.include_router(features.router)
```

#### 2. Adding a New Service

```python
# app/services/my_service.py
from app.utils.firebase_init import get_firestore_client
from app.config import settings

class MyService:
    def __init__(self):
        self.db = get_firestore_client()
        self.api_key = settings.my_api_key
    
    async def do_something(self, param: str):
        # Implementation
        pass
```

---

## Key Technologies

### FastAPI
- **Version**: 0.115+
- **Purpose**: Web framework for building APIs
- **Key Features**:
  - Automatic API documentation (Swagger/OpenAPI)
  - Type hints and validation with Pydantic
  - Async/await support
  - Dependency injection

### Firebase
- **Firestore**: NoSQL document database for user data, stories, and devices
- **Firebase Storage**: File storage for audio, images
- **Firebase Authentication**: User authentication and authorization

### AI Services
- **OpenAI GPT-4**: Story generation and narrative creation
- **Cartesia (Sonic)**: Text-to-speech with voice cloning
- **SeeDream**: AI image generation for story scenes
- **Deepgram**: Speech-to-text for conversational AI
- **Freesound**: Ambient sound effects library

### WebRTC (Pipecat)
- **Pipecat**: Framework for building real-time conversational AI
- **SmallWebRTC**: Lightweight WebRTC transport
- **Daily**: Alternative WebRTC transport (supported but not primary)

### Queue Management
- **AsyncIO**: Python's async library for concurrent operations
- **Priority Queue**: For job scheduling and failover
- **Background Tasks**: Worker-based task processing

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_queue_management.py

# Run with coverage
pytest --cov=app tests/

# Run edge case tests
python tests/test_queue_edge_cases.py
```

### Test Structure

```python
# tests/test_feature.py
import pytest
from app.services.feature_service import FeatureService

@pytest.mark.asyncio
async def test_feature_functionality():
    service = FeatureService()
    result = await service.do_something("test")
    assert result is not None
```

### Manual API Testing

1. **Using Swagger UI**
   - Navigate to http://localhost:8000/docs
   - Try out endpoints interactively

2. **Using cURL**
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Test authentication
   curl -X POST http://localhost:8000/auth/signup \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"password123"}'
   ```

3. **Using Postman**
   - Import the OpenAPI spec from `/docs`
   - Set up environment variables for tokens

---

## Deployment

### Production Checklist

- [ ] Set `DEBUG=false` in `.env`
- [ ] Set `VERBOSE_LOGGING=false`
- [ ] Configure proper CORS origins
- [ ] Use environment secrets management
- [ ] Enable HTTPS/SSL
- [ ] Set up monitoring and logging
- [ ] Configure database backups
- [ ] Set up error tracking (Sentry)

### Deployment Options

#### 1. Google Cloud Run (Recommended)
```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT_ID/stserver

# Deploy
gcloud run deploy stserver \
  --image gcr.io/PROJECT_ID/stserver \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### 2. Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 3. Traditional Server
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv nginx

# Setup and run with gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## Common Tasks

### Adding a New API Key

1. Add to `.env`:
   ```bash
   NEW_API_KEY=your_key_here
   ```

2. Add to `app/config.py`:
   ```python
   class Settings(BaseSettings):
       new_api_key: str = Field(..., env="NEW_API_KEY")
   ```

3. Use in service:
   ```python
   from app.config import settings
   api_key = settings.new_api_key
   ```

### Debugging Issues

1. **Enable Verbose Logging**
   ```bash
   # In .env
   VERBOSE_LOGGING=true
   DEBUG=true
   ```

2. **Check Logs**
   ```bash
   # View real-time logs
   tail -f logs/server.log
   
   # In production (Cloud Run)
   gcloud logging read "resource.type=cloud_run_revision"
   ```

3. **Test Individual Services**
   ```python
   # In Python REPL
   from app.services.story_service import StoryService
   service = StoryService()
   result = await service.generate_story(...)
   ```

### Database Migrations

Since we use Firestore (NoSQL), there are no traditional migrations. However, for data structure changes:

1. **Add New Fields**: Firestore allows dynamic fields
2. **Rename Fields**: Use a migration script:
   ```python
   # scripts/migrate_field.py
   from app.utils.firebase_init import get_firestore_client
   
   db = get_firestore_client()
   users = db.collection('users').stream()
   
   for user in users:
       user_ref = db.collection('users').document(user.id)
       user_ref.update({'new_field': user.get('old_field')})
   ```

### Performance Optimization

1. **Use Background Tasks**
   ```python
   from fastapi import BackgroundTasks
   
   @router.post("/generate-story")
   async def generate_story(
       request: StoryRequest,
       background_tasks: BackgroundTasks
   ):
       job_id = await submit_story_job(request)
       return {"job_id": job_id, "status": "processing"}
   ```

2. **Caching**
   - Use Firebase caching for frequently accessed data
   - Implement in-memory caching with `functools.lru_cache`

3. **Async Operations**
   ```python
   # Good: Run operations concurrently
   async with asyncio.TaskGroup() as tg:
       audio_task = tg.create_task(generate_audio(text))
       image_task = tg.create_task(generate_image(prompt))
   
   # Bad: Sequential operations
   audio = await generate_audio(text)
   image = await generate_image(prompt)
   ```

---

## Getting Help

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Project Issues**: Check GitHub issues
- **Stack Overflow**: Tag questions with `fastapi` and `firebase`

---

## Next Steps

- Read [FRONTEND_API_GUIDE.md](./FRONTEND_API_GUIDE.md) for API integration
- Read [IMPLEMENTATION_DETAILS.md](./IMPLEMENTATION_DETAILS.md) for deep dives
- Check [QUEUE_MANAGEMENT.md](./QUEUE_MANAGEMENT.md) for background job system
- Review [CONVERSATIONAL_AI_DOCS.md](./CONVERSATIONAL_AI_DOCS.md) for WebRTC features
