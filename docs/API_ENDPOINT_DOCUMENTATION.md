# API Endpoint Documentation

## Overview
Comprehensive documentation for all API endpoints in the Storyteller API.

**Base URL**: `https://api.storyteller.app`  
**API Version**: 3.0.0  
**Authentication**: Firebase JWT Token  
**Backward Compatibility**: ✅ FULLY COMPATIBLE with v2.x

> **Important:** All legacy request formats continue to work unchanged. The `child_id` parameter and children endpoints are new optional features. Existing clients require **zero changes** to continue working.

---

## Table of Contents
1. [Authentication](#1-authentication)
2. [Children Management](#2-children-management)
3. [Story Generation](#3-story-generation)
4. [Story Management](#4-story-management)
5. [User Profile](#5-user-profile)
6. [Voice Clones](#6-voice-clones)
7. [Reference Images](#7-reference-images)
8. [Health & System](#8-health--system)

---

## Common Patterns

### Authentication
All endpoints (except health checks) require a Firebase JWT token:

**Header:**
```
Authorization: Bearer <firebase_jwt_token>
```

**OR Query Parameter (legacy):**
```
?firebase_token=<firebase_jwt_token>
```

### Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `201`: Created
- `400`: Bad Request (invalid input)
- `401`: Unauthorized (invalid/missing token)
- `402`: Payment Required (trial expired, subscription needed)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `500`: Internal Server Error
- `502`: Bad Gateway (external service error)
- `504`: Gateway Timeout

---

## 1. Authentication

### 1.1 Register User

**Endpoint:** `POST /auth/register`

**Description:** Create a new user account with parent profile and first child.

**Request Body:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "parent": {
    "name": "John Doe",
    "email": "john@example.com"
  },
  "child": {
    "name": "Emma",
    "age": 7,
    "gender": "female",
    "interests": ["reading", "adventure", "animals"]
  },
  "system_prompt": "Optional custom system prompt for story generation"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "User profile created successfully",
  "user_id": "user_abc123",
  "default_child_id": "child_xyz789",
  "profile": {
    "parent_name": "John Doe",
    "parent_email": "john@example.com",
    "children_count": 1,
    "story_count": 0,
    "created_at": "2025-11-07T12:00:00Z"
  }
}
```

**Error Cases:**
- `400`: Missing required fields
- `401`: Invalid Firebase token
- `409`: User already exists

**Client Handling:**
```typescript
async function registerUser(firebaseToken: string, parentData, childData) {
  try {
    const response = await fetch('/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        firebase_token: firebaseToken,
        parent: parentData,
        child: childData
      })
    });
    
    if (!response.ok) {
      if (response.status === 409) {
        // User already exists - redirect to login
        return redirectToLogin();
      }
      throw new Error('Registration failed');
    }
    
    const data = await response.json();
    // Save user_id and default_child_id for future requests
    saveToLocalStorage('user_id', data.user_id);
    saveToLocalStorage('default_child_id', data.default_child_id);
    
    return data;
  } catch (error) {
    console.error('Registration error:', error);
    throw error;
  }
}
```

---

## 2. Children Management

### 2.1 Create Child

**Endpoint:** `POST /children`

**Description:** Add a new child profile to the parent's account.

**Headers:**
```
Authorization: Bearer <firebase_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "name": "Oliver",
  "age": 5,
  "gender": "male",
  "interests": ["space", "dinosaurs", "building"]
}
```

**Response:** `201 Created`
```json
{
  "child_id": "child_def456",
  "name": "Oliver",
  "age": 5,
  "gender": "male",
  "interests": ["space", "dinosaurs", "building"],
  "image_url": null,
  "voice_clone_id": null,
  "created_at": "2025-11-07T12:30:00Z",
  "is_default": false
}
```

**Client Handling:**
```typescript
async function createChild(childData: ChildCreate) {
  const token = await getFirebaseToken();
  
  const response = await fetch('/children', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      firebase_token: token,
      ...childData
    })
  });
  
  if (!response.ok) {
    throw new Error('Failed to create child');
  }
  
  const child = await response.json();
  
  // Update local children list
  updateChildrenList(child);
  
  return child;
}
```

---

### 2.2 List Children

**Endpoint:** `GET /children`

**Description:** Get all children for the authenticated parent.

**Headers:**
```
Authorization: Bearer <firebase_token>
```

**Response:** `200 OK`
```json
{
  "children": [
    {
      "child_id": "child_xyz789",
      "name": "Emma",
      "age": 7,
      "gender": "female",
      "interests": ["reading", "adventure", "animals"],
      "image_url": "https://storage.googleapis.com/...",
      "voice_clone_id": "voice_123",
      "created_at": "2025-11-01T10:00:00Z",
      "is_default": true,
      "story_count": 5
    },
    {
      "child_id": "child_def456",
      "name": "Oliver",
      "age": 5,
      "gender": "male",
      "interests": ["space", "dinosaurs", "building"],
      "image_url": null,
      "voice_clone_id": null,
      "created_at": "2025-11-07T12:30:00Z",
      "is_default": false,
      "story_count": 0
    }
  ],
  "total_count": 2,
  "default_child_id": "child_xyz789"
}
```

**Client Handling:**
```typescript
async function loadChildren() {
  const token = await getFirebaseToken();
  
  const response = await fetch('/children', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  
  // Display children in UI
  renderChildrenList(data.children);
  
  // Highlight default child
  highlightDefaultChild(data.default_child_id);
  
  return data;
}
```

---

### 2.3 Get Child Details

**Endpoint:** `GET /children/{child_id}`

**Description:** Get detailed information about a specific child.

**Response:** `200 OK`
```json
{
  "child_id": "child_xyz789",
  "name": "Emma",
  "age": 7,
  "gender": "female",
  "interests": ["reading", "adventure", "animals"],
  "image_url": "https://storage.googleapis.com/...",
  "voice_clone_id": "voice_123",
  "system_prompt": "Custom story generation prompt for this child",
  "created_at": "2025-11-01T10:00:00Z",
  "updated_at": "2025-11-05T15:30:00Z",
  "is_default": true,
  "stats": {
    "total_stories": 5,
    "total_scenes": 35,
    "last_story_created": "2025-11-05T15:30:00Z"
  }
}
```

---

### 2.4 Update Child

**Endpoint:** `PUT /children/{child_id}`

**Description:** Update a child's profile information.

**Request Body:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "name": "Emma Rose",
  "age": 8,
  "interests": ["reading", "adventure", "animals", "science"]
}
```

**Response:** `200 OK`
```json
{
  "child_id": "child_xyz789",
  "name": "Emma Rose",
  "age": 8,
  "interests": ["reading", "adventure", "animals", "science"],
  "updated_at": "2025-11-07T13:00:00Z"
}
```

---

### 2.5 Delete Child

**Endpoint:** `DELETE /children/{child_id}`

**Description:** Soft delete a child profile (marks as inactive).

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Child profile deleted successfully",
  "child_id": "child_def456"
}
```

**Client Handling:**
```typescript
async function deleteChild(childId: string) {
  // Show confirmation dialog
  const confirmed = await showConfirmDialog(
    'Delete Child Profile',
    'Are you sure? This cannot be undone.'
  );
  
  if (!confirmed) return;
  
  const token = await getFirebaseToken();
  
  const response = await fetch(`/children/${childId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      firebase_token: token
    })
  });
  
  if (!response.ok) {
    showError('Failed to delete child');
    return;
  }
  
  // Refresh children list
  await loadChildren();
  
  showSuccess('Child profile deleted');
}
```

---

### 2.6 Set Default Child

**Endpoint:** `POST /children/{child_id}/select`

**Description:** Set a child as the default for story generation.

**Request Body:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Default child updated",
  "default_child_id": "child_xyz789"
}
```

---

### 2.7 Get Child's Stories

**Endpoint:** `GET /children/{child_id}/stories`

**Description:** Get all stories created for a specific child.

**Query Parameters:**
- `limit` (optional): Number of stories to return (default: 20)
- `offset` (optional): Pagination offset (default: 0)

**Response:** `200 OK`
```json
{
  "stories": [
    {
      "story_id": "story_123",
      "title": "Emma's Adventure in the Magic Forest",
      "created_at": "2025-11-05T15:30:00Z",
      "total_scenes": 7,
      "total_duration": 420,
      "thumbnail_url": "https://storage.googleapis.com/..."
    }
  ],
  "total_count": 5,
  "has_more": false
}
```

---

### 2.8 Get Default Child

**Endpoint:** `GET /children/default`

**Description:** Return the currently selected default child for story generation.

**Response:** `200 OK`
```json
{
  "default_child_id": "child_xyz789",
  "child": {
    "child_id": "child_xyz789",
    "name": "Emma",
    "age": 7,
    "gender": "female",
    "interests": ["reading", "adventure"],
    "image_url": null,
    "voice_clone_id": null,
    "system_prompt": "...",
    "is_default": true
  }
}
```

---

### 2.9 Update Child System Prompt

**Endpoint:** `PATCH /children/{child_id}/system-prompt`

**Description:** Set or update a child's system prompt which overrides the parent-level prompt during generation.

**Request Body:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "system_prompt": "Custom prompt for this child"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "child_id": "child_xyz789",
  "system_prompt": "Custom prompt for this child",
  "updated_at": "2025-11-08T12:00:00Z"
}
```

---

### 2.10 Select Child Voice Clone

**Endpoint:** `POST /children/{child_id}/voice-clone/select`

**Description:** Assign an existing voice clone to a child; used by default during story generation.

**Request Body:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "voice_clone_id": "voice_123"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "child_id": "child_xyz789",
  "voice_clone_id": "voice_123"
}
```

---

### 2.11 Link Child Reference Image

**Endpoint:** `POST /children/{child_id}/reference-images/link`

**Description:** Link a previously uploaded reference image to the child.

**Request Body:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "reference_image_id": "ref_abc123"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "child_id": "child_xyz789",
  "linked_reference_image_id": "ref_abc123"
}
```

---

### 2.12 Children Stats (Aggregate)

**Endpoint:** `GET /children/stats`

**Description:** Aggregate counts across all children (stories, voice clones, reference images).

**Response:** `200 OK`
```json
{
  "totals": {
    "children": 2,
    "stories": 5,
    "voice_clones": 1,
    "reference_images": 3
  },
  "by_child": [
    { "child_id": "child_xyz789", "stories": 5, "voice_clones": 1, "reference_images": 2 },
    { "child_id": "child_def456", "stories": 0, "voice_clones": 0, "reference_images": 1 }
  ]
}
```

## 3. Story Generation

### 3.1 Generate Story (Async)

**Endpoint:** `POST /stories/generate`

**Description:** Start asynchronous story generation. Returns immediately with story_id to track progress.

**Backward Compatible:** ✅ All legacy formats supported

#### Request Format A: New Format (Recommended)

```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "child_id": "child_xyz789",
  "prompt": "A story about a brave girl who discovers a magical library",
  "morals": ["courage", "curiosity", "friendship"],
  "story_length": "medium",
  "art_style": "watercolor",
  "language": "english"
}
```

#### Request Format B: Legacy Format (Still Works ✅)

```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "prompt": "A story about a brave girl who discovers a magical library",
  "child_name": "Emma",
  "child_age": 7,
  "story_length": "medium",
  "art_style": "watercolor"
}
```

> **Note:** If you don't provide `child_id`, the system will use your default child or the legacy single-child profile. Both formats work identically.

#### Child settings precedence

When `child_id` is provided, that child's settings are auto-applied to generation:

- System prompt: child's `system_prompt` overrides parent profile
- Voice: child's `voice_clone_id` is used by default (request `voice_clone_id` takes precedence if provided)
- Name/Age/Interests: inherited from child profile unless explicitly overridden by request fields (`child_name`, `child_age`)
- Reference image: child's `image_url` is used to keep visual consistency when the child appears in scenes

**Required Fields:**
- `firebase_token`: Your Firebase authentication token

**Optional Fields:**
- `child_id`: Specific child profile to use (NEW in v3.0)
- `child_name`: Override child's name from profile
- `child_age`: Override child's age from profile
- `prompt`: Story request
- `morals`: List of moral values
- `story_length`: "short", "medium", "long" (default: "medium")
- `art_style`: Image generation style (default: "magical")
- `language`: Story language (default: "english")
- `scene_count`: Custom scene count (overrides story_length)
- `voice_clone_id`: Specific voice to use
- `reference_image_ids`: Array of reference image IDs for character appearance

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Story generation started! Connect via WebSocket to receive real-time updates.",
  "story_id": "story_9dd2fdf0",
  "job_id": "job_abc123",
  "status": "processing",
  "estimated_completion_time": "30-60 seconds",
  "websocket_endpoint": "/ws/stories/{firebase_token}",
  "tracking_method": "background_service_with_websocket_notifications"
}
```

**Client Handling:**
```typescript
async function generateStory(storyRequest: StoryRequest) {
  const token = await getFirebaseToken();
  
  // NEW FORMAT (recommended for multi-child support)
  const newFormatRequest = {
    firebase_token: token,
    child_id: selectedChildId,  // Optional - uses default if not provided
    prompt: storyRequest.prompt,
    story_length: "medium"
  };
  
  // LEGACY FORMAT (still works perfectly!)
  const legacyFormatRequest = {
    firebase_token: token,
    prompt: storyRequest.prompt,
    child_name: "Emma",
    child_age: 7,
    story_length: "medium"
  };
  
  // Both formats work - choose what fits your app
  const requestBody = useLegacyFormat ? legacyFormatRequest : newFormatRequest;
  
  // Start story generation
  const response = await fetch('/stories/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(requestBody)
  });
  
  if (!response.ok) {
    if (response.status === 402) {
      // Trial expired - show subscription prompt
      showSubscriptionPrompt();
      return;
    }
    throw new Error('Story generation failed');
  }
  
  const data = await response.json();
  
  // Connect to WebSocket for real-time updates
  const ws = new WebSocket(`wss://api.storyteller.app/ws/stories/${token}`);
  
  ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    
    if (update.story_id === data.story_id) {
      switch (update.event) {
        case 'story_progress':
          // Update progress bar
          updateProgress(update.progress, update.message);
          break;
          
        case 'story_completed':
          // Story ready - fetch full details
          fetchStoryDetails(update.story_id);
          ws.close();
          break;
          
        case 'story_failed':
          // Show error
          showError(update.message);
          ws.close();
          break;
      }
    }
  };
  
  return data;
}
```

---

### 3.2 Check Story Status

**Endpoint:** `GET /stories/{story_id}`

**Description:** Check the status of a story (for polling if WebSocket not used).

**Response:** `200 OK` (Processing)
```json
{
  "status": "generating_media",
  "message": "Story status: generating_media"
}
```

**Response:** `200 OK` (Completed)
```json
{
  "status": "completed",
  "message": "Story 'Emma's Adventure in the Magic Forest' completed successfully!",
  "manifest": {
    "story_id": "story_9dd2fdf0",
    "title": "Emma's Adventure in the Magic Forest",
    "total_scenes": 7,
    "total_duration": 420,
    "scenes": [...]
  }
}
```

**Response:** `404 Not Found` (After deletion)
```json
{ "detail": "story_not_found" }
```

---

## 4. Story Management

### 4.1 List User Stories

**Endpoint:** `GET /stories/user/stories`

**Description:** Get all stories for the authenticated user with optional filtering.

**Headers:**
```
Authorization: Bearer <firebase_token>
```

**Query Parameters:**
- `limit`: Number of stories (default: 20, max: 100)
- `offset`: Pagination offset (default: 0)
- `filter`: Filter type - `owned`, `shared`, `copied`, `all` (default: `owned`)

**Response:** `200 OK`
```json
{
  "success": true,
  "user_id": "user_abc123",
  "filter": "owned",
  "stories": [
    {
      "story_id": "story_123",
      "title": "Emma's Adventure in the Magic Forest",
      "user_prompt": "A story about a brave girl who discovers a magical library",
      "created_at": "2025-11-05T15:30:00Z",
      "total_scenes": 7,
      "total_duration": 420,
      "status": "completed",
      "thumbnail_url": "https://storage.googleapis.com/...",
      "child_id": "child_xyz789",
      "child_name": "Emma",
      "days_ago": 2
    }
  ],
  "total_count": 5,
  "has_more": false,
  "pagination": {
    "current_page": 1,
    "total_pages": 1,
    "page_size": 20,
    "offset": 0
  }
}
```

**Client Handling:**
```typescript
async function loadStories(page = 1, filter = 'owned') {
  const token = await getFirebaseToken();
  const limit = 20;
  const offset = (page - 1) * limit;
  
  const response = await fetch(
    `/stories/user/stories?limit=${limit}&offset=${offset}&filter=${filter}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  const data = await response.json();
  
  // Render stories in UI
  renderStories(data.stories);
  
  // Setup pagination
  if (data.has_more) {
    showLoadMoreButton();
  }
  
  return data;
}
```

---

### 4.2 Get Story Details

**Endpoint:** `GET /stories/details/{story_id}`

**Description:** Get complete story details including all scenes.

**Response:** `200 OK`
```json
{
  "success": true,
  "story": {
    "story_id": "story_123",
    "title": "Emma's Adventure in the Magic Forest",
    "user_prompt": "A story about a brave girl who discovers a magical library",
    "child_id": "child_xyz789",
    "child_snapshot": {
      "name": "Emma",
      "age": 7,
      "interests": ["reading", "adventure"]
    },
    "created_at": "2025-11-05T15:30:00Z",
    "total_scenes": 7,
    "total_duration": 420,
    "thumbnail_url": "https://storage.googleapis.com/...",
    "scenes": [
      {
        "scene_number": 1,
        "text": "Once upon a time, in a quiet village...",
        "audio_url": "https://storage.googleapis.com/...",
        "image_url": "https://storage.googleapis.com/...",
        "start_time": 0,
        "duration": 60
      }
    ]
  }
}
```

---

### 4.3 Delete Story

**Endpoint:** `DELETE /stories/delete/{story_id}`

**Description:** Permanently delete a story.

**Request Body:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Story 'Emma's Adventure in the Magic Forest' has been deleted",
  "story_id": "story_123",
  "deleted_at": "2025-11-07T14:00:00Z"
}
```

---

## 5. User Profile

### 5.1 Get Profile

**Endpoint:** `GET /users/profile`

**Description:** Returns the authenticated user's profile and defaults.

**Headers:**
```
Authorization: Bearer <firebase_token>
```

**Response:** `200 OK`
```json
{
  "user_id": "user_abc123",
  "parent": { "name": "John Doe", "email": "john@example.com" },
  "children_count": 2,
  "default_child_id": "child_xyz789"
}
```

### 5.2 Update Profile

**Endpoint:** `PUT /users/profile`

**Description:** Update parent profile fields.

**Request Body:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "parent": { "name": "John X. Doe" }
}
```

**Response:** `200 OK`
```json
{ "success": true }
```

### 5.3 Delete Profile

**Endpoint:** `DELETE /users/profile`

**Description:** Delete user profile (dangerous, irreversible). May be restricted.

**Response:** `200 OK`
```json
{ "success": true }
```

---

## 6. Voice Clones

Endpoints to manage user's voice clones used for TTS:

- `POST /users/voice-clones/create` — Create a new clone
- `PUT /users/voice-clones/{voice_clone_id}/update` — Update metadata
- `POST /users/voice-clones/set-active` — Set active clone
- `POST /users/voice-clones/delete` — Delete a clone
- `POST /users/voice-clones/preview` — Generate a short preview using the clone

All require Authorization header and accept JSON bodies; responses are JSON with `success` and entity data.

---

## 7. Reference Images

### 7.1 Upload Reference Image (Multipart)

**Endpoint:** `POST /reference-images/upload`

**Description:** Upload an image file and register as a reference image for the user.

**Headers:**
```
Authorization: Bearer <firebase_token>
Content-Type: multipart/form-data
```

**Form Fields:**
- `file`: binary image file
- `label` (optional): label for this image

**Response:** `201 Created`
```json
{
  "reference_image_id": "ref_abc123",
  "image_url": "https://storage.googleapis.com/...",
  "label": "portrait"
}
```

### 7.2 Create (JSON)

**Endpoint:** `POST /reference-images/create`

**Description:** Register an already-uploaded URL as a reference image.

**Request Body:**
```json
{ "firebase_token": "...", "image_url": "https://...", "label": "optional" }
```

**Response:** `201 Created`
```json
{ "reference_image_id": "ref_abc123", "image_url": "https://..." }
```

### 7.3 List

**Endpoint:** `GET /reference-images/list`

**Description:** List user's reference images.

**Response:** `200 OK`
```json
{ "images": [{ "reference_image_id": "ref_abc123", "image_url": "https://...", "label": "portrait" }] }
```

### 7.4 Get by ID

**Endpoint:** `GET /reference-images/{reference_image_id}`

**Response:** `200 OK`
```json
{ "reference_image_id": "ref_abc123", "image_url": "https://...", "label": "portrait" }
```

### 7.5 Update

**Endpoint:** `PUT /reference-images/{reference_image_id}`

**Request Body:**
```json
{ "label": "new label" }
```

**Response:** `200 OK`
```json
{ "success": true }
```

### 7.6 Delete

**Endpoint:** `DELETE /reference-images/{reference_image_id}`

**Response:** `200 OK`
```json
{ "success": true }
```

---

## 8. Health & System

### 8.1 Health

**Endpoint:** `GET /health`

**Response:** `200 OK`
```json
{ "status": "healthy", "services": { "firebase": "connected", "openai": "configured" } }
```

### 8.2 Analytics (examples)

- `GET /analytics/summary` — summary KPI metrics
- `GET /analytics/metrics/users` — user metrics

### 8.3 Admin (examples)

- `GET /admin/status` — service status
- `GET /admin/users` — list users (restricted)

### 8.4 WebSockets

- `GET /ws/stories/{user_token}` — story progress updates (connect with Firebase token)

---

For additional endpoints and exact field-level schemas, see the OpenAPI at `/docs`.

---

## Client Integration Examples

### React Example

```tsx
import { useState, useEffect } from 'react';

function StoryGenerator() {
  const [children, setChildren] = useState([]);
  const [selectedChild, setSelectedChild] = useState(null);
  const [generating, setGenerating] = useState(false);
  
  useEffect(() => {
    loadChildren();
  }, []);
  
  async function loadChildren() {
    const token = await getFirebaseToken();
    const response = await fetch('/children', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();
    setChildren(data.children);
    setSelectedChild(data.default_child_id);
  }
  
  async function generateStory(prompt) {
    setGenerating(true);
    
    try {
      const token = await getFirebaseToken();
      const response = await fetch('/stories/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          firebase_token: token,
          child_id: selectedChild,
          prompt,
          story_length: 'medium',
          art_style: 'magical'
        })
      });
      
      const data = await response.json();
      
      // Connect WebSocket for updates
      connectWebSocket(token, data.story_id);
    } catch (error) {
      console.error('Generation failed:', error);
    }
  }
  
  return (
    <div>
      <select onChange={(e) => setSelectedChild(e.target.value)}>
        {children.map(child => (
          <option key={child.child_id} value={child.child_id}>
            {child.name}
          </option>
        ))}
      </select>
      
      <button onClick={() => generateStory('A story about adventure')} disabled={generating}>
        {generating ? 'Generating...' : 'Generate Story'}
      </button>
    </div>
  );
}
```

---

## Summary

This documentation provides:
- Complete endpoint specifications
- Request/response examples
- Error handling patterns
- Client integration code
- WebSocket usage
- Pagination examples
- Authentication patterns

For more details on specific endpoints, refer to the OpenAPI schema at `/docs`.
