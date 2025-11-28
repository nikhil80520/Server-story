# Code Architecture & Style Guide

## Overview
This document defines the coding standards, architecture patterns, and best practices for the Storyteller API.

---

## 1. Project Structure

```
STServer/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration and settings
│   ├── dependencies.py         # Dependency injection setup
│   ├── models/                 # Pydantic data models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── story.py
│   │   └── auth.py
│   ├── routers/                # API endpoint routers
│   │   ├── __init__.py
│   │   ├── stories.py
│   │   ├── children.py
│   │   └── users.py
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── story_service.py
│   │   ├── child_service.py
│   │   └── storage_service.py
│   ├── middleware/             # Custom middleware
│   │   └── __init__.py
│   ├── utils/                  # Utility functions
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   └── telemetry.py
│   └── database/               # Database connections
│       └── __init__.py
├── tests/                      # Test files
│   ├── __init__.py
│   ├── test_stories.py
│   └── test_children.py
├── docs/                       # Documentation
├── requirements.txt
└── README.md
```

---

## 2. Naming Conventions

### Files and Modules
- **Python files**: `snake_case.py`
  - ✅ `story_service.py`
  - ❌ `StoryService.py`, `story-service.py`

### Classes
- **Classes**: `PascalCase`
  - ✅ `StoryService`, `ChildService`, `StorageService`
  - ❌ `story_service`, `Story_Service`

### Functions and Methods
- **Functions/Methods**: `snake_case`
  - ✅ `generate_story()`, `create_child()`
  - ❌ `generateStory()`, `CreateChild()`

### Variables
- **Variables**: `snake_case`
  - ✅ `user_id`, `story_count`, `child_name`
  - ❌ `userId`, `StoryCount`

### Constants
- **Constants**: `UPPER_SNAKE_CASE` (class-level or module-level)
  - ✅ `MAX_STORY_LENGTH`, `DEFAULT_TIMEOUT`, `CHUNK_SIZE`
  - ❌ `maxStoryLength`, `default_timeout`

---

## 3. Service Layer Architecture

### Dependency Injection Pattern

**❌ BAD - Instantiating dependencies inside:**
```python
class StoryService:
    def __init__(self):
        self.storage = StorageService()  # Creates tight coupling
        self.media = MediaService()
```

**✅ GOOD - Dependencies injected:**
```python
class StoryService:
    """
    Service for story generation and management.
    
    This service handles story creation, scene generation, and metadata management.
    Dependencies are injected to enable testing and flexibility.
    
    Args:
        storage_service: Service for data persistence
        media_service: Service for media generation
        openai_client: OpenAI client for LLM operations
    """
    
    # Class constants
    DEFAULT_SCENE_COUNT = 7
    MAX_STORY_LENGTH = 5000
    GENERATION_TIMEOUT = 300  # seconds
    
    def __init__(
        self,
        storage_service: StorageService,
        media_service: MediaService,
        openai_client: OpenAI
    ):
        """Initialize the story service with required dependencies."""
        self.storage = storage_service
        self.media = media_service
        self.openai_client = openai_client
        self.logger = get_logger(__name__)
```

### Service Constants

Extract magic numbers to class-level constants with descriptive names:

**❌ BAD:**
```python
if len(story) > 500:
    chunk_size = 100

timeout = 30
```

**✅ GOOD:**
```python
class StoryService:
    # Processing constants
    MAX_STORY_LENGTH_FOR_CHUNKING = 500
    CHUNK_SIZE = 100
    API_TIMEOUT_SECONDS = 30
    MAX_RETRIES = 3
    
    def process_story(self, story: str):
        if len(story) > self.MAX_STORY_LENGTH_FOR_CHUNKING:
            chunk_size = self.CHUNK_SIZE
```

---

## 4. Logging

### Replace Print Statements

**❌ BAD:**
```python
print(f"Processing story: {story_id}")
print(f"Error: {e}")
```

**✅ GOOD:**
```python
from app.utils.logger import get_logger

logger = get_logger(__name__)

logger.info(f"Processing story: {story_id}", extra={"story_id": story_id})
logger.error(f"Story processing failed: {e}", exc_info=True, extra={"story_id": story_id})
```

### Log Levels

- `logger.debug()`: Detailed diagnostic information
- `logger.info()`: General informational messages
- `logger.warning()`: Warning messages for unexpected but handled situations
- `logger.error()`: Error messages for failures
- `logger.critical()`: Critical failures requiring immediate attention

### Structured Logging

Use the `extra` parameter for machine-readable context:

```python
logger.info(
    "Story generated successfully",
    extra={
        "story_id": story_id,
        "user_id": user_id,
        "scene_count": len(scenes),
        "duration_seconds": duration
    }
)
```

---

## 5. Error Handling

### Try-Except Blocks

All risky operations should be wrapped in try-except blocks:

**❌ BAD:**
```python
def generate_story(prompt: str):
    response = openai_client.chat.completions.create(...)
    story_data = json.loads(response)
    return story_data
```

**✅ GOOD:**
```python
def generate_story(self, prompt: str) -> Dict[str, Any]:
    """
    Generate a story using OpenAI.
    
    Args:
        prompt: Story generation prompt
        
    Returns:
        Generated story data
        
    Raises:
        HTTPException: If story generation fails
    """
    try:
        self.logger.debug(f"Generating story with prompt: {prompt[:100]}...")
        
        response = self.openai_client.chat.completions.create(
            model=self.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            timeout=self.API_TIMEOUT_SECONDS
        )
        
        story_data = json.loads(response.choices[0].message.content)
        
        self.logger.info(
            "Story generated successfully",
            extra={"scene_count": len(story_data.get("scenes", []))}
        )
        
        return story_data
        
    except json.JSONDecodeError as e:
        self.logger.error(f"Failed to parse story JSON: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to parse story response from AI"
        )
    
    except openai.APITimeoutError as e:
        self.logger.error(f"OpenAI API timeout: {e}", exc_info=True)
        raise HTTPException(
            status_code=504,
            detail=f"Story generation timed out after {self.API_TIMEOUT_SECONDS}s"
        )
    
    except openai.APIError as e:
        self.logger.error(f"OpenAI API error: {e}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="AI service error occurred"
        )
    
    except Exception as e:
        self.logger.error(f"Unexpected error in story generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during story generation"
        )
```

### Specific Exception Types

Always catch specific exceptions before general ones:

```python
try:
    # Risky operation
    pass
except ValueError as e:
    # Handle value errors
    pass
except KeyError as e:
    # Handle missing keys
    pass
except Exception as e:
    # Handle all other exceptions
    pass
```

---

## 6. Documentation

### Module Docstrings

Every module should have a docstring explaining its purpose:

```python
"""
Story service module for story generation and management.

This module provides the StoryService class which handles:
- Story scene generation using OpenAI
- Media generation (images and audio)
- Story metadata persistence
- Child-specific story personalization

Example:
    >>> story_service = StoryService(storage, media, openai_client)
    >>> scenes = await story_service.generate_story_scenes(
    ...     prompt="A story about friendship",
    ...     user_id="user_123"
    ... )
"""
```

### Class Docstrings

Use Google-style docstrings for classes:

```python
class StoryService:
    """
    Service for story generation and management.
    
    This service orchestrates the story generation process including:
    - Scene generation via OpenAI
    - Media creation (images and audio)
    - Metadata persistence
    - Child profile integration
    
    Attributes:
        storage: StorageService instance for data persistence
        media: MediaService instance for media generation
        openai_client: OpenAI client for LLM operations
        logger: Logger instance for this service
        
    Constants:
        DEFAULT_SCENE_COUNT: Default number of scenes per story
        MAX_STORY_LENGTH: Maximum allowed story length in characters
        GENERATION_TIMEOUT: Timeout for story generation in seconds
    """
```

### Method Docstrings

Document all public methods:

```python
async def generate_story_scenes(
    self,
    user_prompt: str,
    user_id: str,
    target_scenes: int = 7,
    child_id: Optional[str] = None
) -> Tuple[List[StoryScene], str, str, str]:
    """
    Generate story scenes using OpenAI GPT with child personalization.
    
    This method:
    1. Fetches user/child profile from storage
    2. Builds personalized prompt with child context
    3. Calls OpenAI to generate scenes
    4. Parses and validates the response
    5. Returns scenes with metadata
    
    Args:
        user_prompt: User's story request/prompt
        user_id: Firebase user ID
        target_scenes: Number of scenes to generate (default: 7)
        child_id: Optional child ID for personalization
        
    Returns:
        Tuple containing:
            - List of StoryScene objects
            - Story title (str)
            - Thumbnail prompt (str)
            - Child ID used (str or None)
            
    Raises:
        HTTPException: If story generation fails
        ValueError: If parameters are invalid
        
    Example:
        >>> scenes, title, thumb, child_id = await service.generate_story_scenes(
        ...     user_prompt="A story about courage",
        ...     user_id="user_123",
        ...     target_scenes=5
        ... )
    """
```

---

## 7. Type Hints

Use type hints for all function signatures:

```python
from typing import List, Dict, Optional, Tuple, Any

async def create_child(
    self,
    user_id: str,
    child_data: ChildCreate,
    image_data: Optional[bytes] = None
) -> Child:
    """Create a new child profile."""
    pass
```

---

## 8. Async/Await

Use async/await consistently:

**✅ GOOD:**
```python
async def generate_story(self, prompt: str) -> Story:
    """Generate story asynchronously."""
    scenes = await self.generate_scenes(prompt)
    media = await self.generate_media(scenes)
    return Story(scenes=scenes, media=media)
```

---

## 9. OpenTelemetry Tracing

Use tracing for performance monitoring:

```python
from app.utils.telemetry import create_span, trace_operation

class StoryService:
    @trace_operation("generate_story", service="story_service")
    async def generate_story(self, prompt: str) -> Story:
        """Generate a story with distributed tracing."""
        
        with create_span("fetch_user_profile", {"user_id": self.user_id}):
            profile = await self.storage.get_user_profile(self.user_id)
        
        with create_span("call_openai_api"):
            response = await self.openai_client.chat.completions.create(...)
        
        return story
```

---

## 10. Configuration

Use environment variables and settings:

**❌ BAD:**
```python
API_KEY = "sk-1234567890"  # Hardcoded
TIMEOUT = 30
```

**✅ GOOD:**
```python
from app.config import settings

class StoryService:
    API_TIMEOUT = settings.openai_timeout
    MODEL_NAME = settings.llm_model
```

---

## 11. Testing

Write tests for all services:

```python
import pytest
from app.services.story_service import StoryService

@pytest.mark.asyncio
async def test_generate_story_success():
    """Test successful story generation."""
    # Arrange
    storage_mock = Mock(spec=StorageService)
    media_mock = Mock(spec=MediaService)
    openai_mock = Mock(spec=OpenAI)
    
    service = StoryService(storage_mock, media_mock, openai_mock)
    
    # Act
    result = await service.generate_story("test prompt")
    
    # Assert
    assert result is not None
    assert len(result.scenes) > 0
```

---

## 12. Code Review Checklist

Before committing code, ensure:

- [ ] No hardcoded values (use constants or config)
- [ ] No `print()` statements (use logger)
- [ ] All risky operations in try-except blocks
- [ ] Proper type hints on all functions
- [ ] Docstrings on all classes and public methods
- [ ] Dependencies injected, not instantiated
- [ ] Structured logging with extra context
- [ ] Tests written for new functionality
- [ ] OpenTelemetry tracing for critical paths
- [ ] Error messages are user-friendly
- [ ] No security vulnerabilities (no secrets in code)

---

## Summary

Following these guidelines ensures:
- **Maintainability**: Code is easy to understand and modify
- **Testability**: Dependencies can be mocked, functions can be tested
- **Observability**: Logs and traces provide insight into system behavior
- **Reliability**: Proper error handling prevents crashes
- **Performance**: Tracing identifies bottlenecks
