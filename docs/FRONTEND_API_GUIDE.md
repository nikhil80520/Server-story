# Frontend API Guide - ESP32 Storytelling Server

## Table of Contents
1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [User Management](#user-management)
4. [Story Management](#story-management)
5. [IoT Device Management](#iot-device-management)
6. [Conversational AI (WebRTC)](#conversational-ai-webrtc)
7. [WebSocket Real-Time Updates](#websocket-real-time-updates)
8. [Error Handling](#error-handling)
9. [Rate Limits & Best Practices](#rate-limits--best-practices)

---

## Getting Started

### Base URL
```
Production: https://your-domain.com
Development: http://localhost:8000
```

### API Documentation
Interactive API docs available at:
- Swagger UI: `{BASE_URL}/docs`
- ReDoc: `{BASE_URL}/redoc`

### Common Headers
```http
Content-Type: application/json
Authorization: Bearer {firebase_token}
```

---

## Authentication

### 1. Sign Up (Create New User)

**Endpoint**: `POST /auth/signup`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "display_name": "John Doe"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "User created successfully",
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "AOEOul...",
  "expires_in": 3600,
  "user_info": {
    "localId": "user_firebase_uid",
    "email": "user@example.com",
    "displayName": "John Doe",
    "idToken": "eyJhbGciOiJSUzI1NiIs...",
    "registered": true
  }
}
```

**Example (React Native)**:
```javascript
const signUp = async (email, password, displayName) => {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/signup`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ email, password, display_name: displayName })
    });
    
    const data = await response.json();
    
    if (data.success) {
      // Store tokens securely
      await AsyncStorage.setItem('firebase_token', data.firebase_token);
      await AsyncStorage.setItem('refresh_token', data.refresh_token);
      return data;
    }
  } catch (error) {
    console.error('Sign up error:', error);
    throw error;
  }
};
```

### 2. Sign In

**Endpoint**: `POST /auth/signin`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Sign in successful",
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "AOEOul...",
  "expires_in": 3600,
  "user_info": {
    "localId": "user_firebase_uid",
    "email": "user@example.com",
    "displayName": "John Doe",
    "profile": {
      "parent_profile": {...},
      "child_profiles": [...]
    }
  }
}
```

### 3. Refresh Token

**Endpoint**: `POST /auth/refresh-token`

**Description**: Refreshes an expired Firebase ID token using a refresh token. Firebase ID tokens expire after 1 hour, but refresh tokens remain valid for 30 days. This endpoint exchanges a valid refresh token for a new ID token and refresh token pair.

**Request Body**:
```json
{
  "refresh_token": "AOEOul4_your_refresh_token_here"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "firebase_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6Ijc1...",
  "refresh_token": "AOEOul4_new_refresh_token_here",
  "expires_in": 3600
}
```

**Error Responses**:

- **400 Bad Request** - Missing or invalid request body:
```json
{
  "detail": "Refresh token is required"
}
```

- **401 Unauthorized** - Token expired, revoked, or invalid:
```json
{
  "detail": "Token refresh failed: TOKEN_EXPIRED"
}
```

Common Firebase error messages:
- `TOKEN_EXPIRED`: Refresh token has expired (30 days)
- `INVALID_REFRESH_TOKEN`: Malformed or invalid token
- `USER_DISABLED`: User account has been disabled
- `USER_NOT_FOUND`: User has been deleted

**When to Refresh**:
- Firebase ID tokens expire after **1 hour**
- Refresh tokens expire after **30 days of inactivity**
- Refresh proactively 5 minutes before expiry
- On any API call that returns 401 with token expiration error

**Auto-Refresh Implementation**:
```javascript
// Automatically refresh token before expiry
let tokenExpiryTime = Date.now() + (3600 * 1000);

const refreshTokenIfNeeded = async () => {
  const now = Date.now();
  const timeUntilExpiry = tokenExpiryTime - now;
  
  // Refresh 5 minutes before expiry
  if (timeUntilExpiry < 5 * 60 * 1000) {
    try {
      const refreshToken = await AsyncStorage.getItem('refresh_token');
      const response = await fetch(`${API_BASE_URL}/auth/refresh-token`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ refresh_token: refreshToken })
      });
      
      if (!response.ok) {
        const error = await response.json();
        console.error('Token refresh failed:', error.detail);
        // If refresh fails, user needs to re-login
        await handleLogout();
        return false;
      }
      
      const data = await response.json();
      await AsyncStorage.setItem('firebase_token', data.firebase_token);
      await AsyncStorage.setItem('refresh_token', data.refresh_token);
      tokenExpiryTime = Date.now() + (data.expires_in * 1000);
      return true;
    } catch (error) {
      console.error('Token refresh error:', error);
      await handleLogout();
      return false;
    }
  }
  return true;
};

// Call before any authenticated API request
await refreshTokenIfNeeded();
```

**Error Handling Best Practices**:
```javascript
const makeAuthenticatedRequest = async (url, options = {}) => {
  // Try to refresh if needed
  const refreshed = await refreshTokenIfNeeded();
  if (!refreshed) {
    throw new Error('Session expired. Please login again.');
  }
  
  const token = await AsyncStorage.getItem('firebase_token');
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });
  
  // If 401, try refreshing once more
  if (response.status === 401) {
    const errorData = await response.json();
    if (errorData.detail?.includes('expired') || errorData.detail?.includes('invalid')) {
      // Force refresh and retry
      const refreshToken = await AsyncStorage.getItem('refresh_token');
      const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh-token`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ refresh_token: refreshToken })
      });
      
      if (refreshResponse.ok) {
        const data = await refreshResponse.json();
        await AsyncStorage.setItem('firebase_token', data.firebase_token);
        await AsyncStorage.setItem('refresh_token', data.refresh_token);
        tokenExpiryTime = Date.now() + (data.expires_in * 1000);
        
        // Retry original request with new token
        return fetch(url, {
          ...options,
          headers: {
            ...options.headers,
            'Authorization': `Bearer ${data.firebase_token}`
          }
        });
      } else {
        // Refresh failed, logout
        await handleLogout();
        throw new Error('Session expired. Please login again.');
      }
    }
  }
  
  return response;
};
```

**Important Notes**:
- Always store both `firebase_token` and `refresh_token` from the response
- The refresh token in the response is **new** - replace the old one
- If refresh fails with 401, the user must re-authenticate
- Implement automatic retry logic for network failures
- Never expose refresh tokens in logs or error messages

### 4. Verify Token

**Endpoint**: `POST /auth/verify-token`

**Request**:
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "user_id": "user_firebase_uid",
  "email": "user@example.com"
}
```

### 5. Password Reset

**Endpoint**: `POST /auth/password-reset`

**Request**:
```json
{
  "email": "user@example.com"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Password reset email sent to user@example.com"
}
```

### 6. Sign Out

**Endpoint**: `POST /auth/signout`

**Headers**:
```http
Authorization: Bearer {firebase_token}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Sign out successful"
}
```

---

## User Management

### 1. Register User Profile

**Endpoint**: `POST /users/register`

**Headers**:
```http
Authorization: Bearer {firebase_token}
Content-Type: application/json
```

**Request**:
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "parent_profile": {
    "name": "John Doe",
    "email": "john@example.com"
  },
  "child_profiles": [
    {
      "name": "Emma",
      "age": 7,
      "avatar": "bear",
      "gender": "female"
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "User profile created successfully",
  "user_id": "user_firebase_uid",
  "profile": {
    "parent_profile": {...},
    "child_profiles": [...]
  }
}
```

### 2. Get User Profile

**Endpoint**: `GET /users/profile`

**Headers**:
```http
Authorization: Bearer {firebase_token}
```

**Query Parameters**:
- `firebase_token` (string, required): The user's Firebase token

**Response** (200 OK):
```json
{
  "user_id": "user_firebase_uid",
  "parent_profile": {
    "name": "John Doe",
    "email": "john@example.com",
    "avatar_url": "https://..."
  },
  "child_profiles": [
    {
      "id": "child_1",
      "name": "Emma",
      "age": 7,
      "avatar": "bear",
      "gender": "female",
      "avatar_url": "https://...",
      "voice_clone_id": "vc_123..."
    }
  ],
  "account_status": {
    "status": "active",
    "plan": "free",
    "stories_generated": 5,
    "stories_limit": 10
  }
}
```

### 3. Update User Profile

**Endpoint**: `PUT /users/profile`

**Headers**:
```http
Authorization: Bearer {firebase_token}
Content-Type: application/json
```

**Request**:
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "parent_profile": {
    "name": "John Updated Doe"
  },
  "child_profiles": [
    {
      "id": "child_1",
      "name": "Emma Rose",
      "age": 8
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "profile": {...}
}
```

### 4. Upload Avatar

**Endpoint**: `POST /users/avatar`

**Headers**:
```http
Authorization: Bearer {firebase_token}
Content-Type: multipart/form-data
```

**Form Data**:
- `firebase_token` (string, required)
- `profile_type` (string, required): "parent" or "child"
- `child_id` (string, optional): Required if profile_type is "child"
- `avatar` (file, required): Image file (PNG, JPG, max 5MB)

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Avatar uploaded successfully",
  "avatar_url": "https://firebasestorage.googleapis.com/..."
}
```

**Example (React Native)**:
```javascript
const uploadAvatar = async (imageUri, profileType, childId = null) => {
  const formData = new FormData();
  formData.append('firebase_token', await AsyncStorage.getItem('firebase_token'));
  formData.append('profile_type', profileType);
  if (childId) formData.append('child_id', childId);
  
  formData.append('avatar', {
    uri: imageUri,
    type: 'image/jpeg',
    name: 'avatar.jpg'
  });
  
  const response = await fetch(`${API_BASE_URL}/users/avatar`, {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
};
```

### 5. Create Voice Clone

**Endpoint**: `POST /users/voice-clone`

**Headers**:
```http
Authorization: Bearer {firebase_token}
Content-Type: multipart/form-data
```

**Form Data**:
- `firebase_token` (string, required)
- `child_id` (string, required)
- `voice_name` (string, required): Name for the voice
- `audio_files` (files, required): 1-5 audio files (WAV, MP3, max 10MB each)

**Response** (200 OK):
```json
{
  "success": true,
  "voice_clone_id": "vc_123...",
  "voice_name": "Emma's Voice"
}
```

---

## Child Management

### 1. Create Child Profile

**Endpoint**: `POST /children`

**Request**:
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "name": "Emma",
  "age": 8,
  "gender": "girl",
  "interests": ["reading", "science", "animals"],
  "image_base64": "data:image/jpeg;base64,/9j/4AAQ...",
  "avatar_seed": "emma_custom_seed",
  "avatar_style": "avataaars",
  "system_prompt": "Custom AI prompt for Emma..."
}
```

**Field Descriptions**:
- `firebase_token` (string, required): User's Firebase authentication token
- `name` (string, required): Child's name
- `age` (number, required): Child's age
- `gender` (string, optional): **"boy"** or **"girl"** - **CRITICAL for consistent story images**
  - **Ensures the child appears as the same gender across all story scenes**
  - **Without this, the AI may render the child inconsistently (sometimes boy, sometimes girl)**
- `interests` (array, required): List of child's interests
- `image_base64` (string, optional): Base64-encoded profile image
- `avatar_seed` (string, optional): Custom seed for avatar generation
- `avatar_style` (string, optional): Avatar style (default: "avataaars")
- `system_prompt` (string, optional): Custom AI storytelling prompt

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Child profile created successfully",
  "child": {
    "child_id": "child_a1b2c3d4e5f6",
    "name": "Emma",
    "age": 8,
    "gender": "girl",
    "interests": ["reading", "science", "animals"],
    "image_url": "https://storage.googleapis.com/...",
    "avatar_seed": "emma_custom_seed",
    "avatar_style": "avataaars",
    "avatar_url": null,
    "system_prompt": "You are a creative children's storyteller...",
    "is_active": true,
    "story_count": 0,
    "voice_clones_count": 0,
    "reference_images_count": 0,
    "created_at": "2025-11-21T10:30:00Z",
    "updated_at": "2025-11-21T10:30:00Z"
  }
}
```

**Example (React Native)**:
```javascript
const createChild = async (childData) => {
  const token = await AsyncStorage.getItem('firebase_token');
  
  const response = await fetch(`${API_BASE_URL}/children`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      firebase_token: token,
      name: childData.name,
      age: childData.age,
      gender: childData.gender,  // "boy" or "girl"
      interests: childData.interests,
      image_base64: childData.imageBase64  // Optional
    })
  });
  
  const data = await response.json();
  if (data.success) {
    console.log('Child created:', data.child.child_id);
    return data.child;
  }
  throw new Error(data.message);
};

// Usage example
const newChild = await createChild({
  name: "Emma",
  age: 8,
  gender: "girl",  // IMPORTANT: Include for consistent story images
  interests: ["reading", "animals", "science"]
});
```

### 2. Get All Children

**Endpoint**: `GET /children`

**Query Parameters**:
- `firebase_token` (string, required)

**Response** (200 OK):
```json
{
  "success": true,
  "children": [
    {
      "child_id": "child_a1b2c3d4e5f6",
      "name": "Emma",
      "age": 8,
      "gender": "girl",
      "interests": ["reading", "science"],
      "story_count": 12,
      "is_active": true
    }
  ],
  "default_child_id": "child_a1b2c3d4e5f6"
}
```

### 3. Update Child Profile

**Endpoint**: `PUT /children/{child_id}`

**Request**:
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "name": "Emma Rose",
  "age": 9,
  "gender": "girl",
  "interests": ["reading", "art", "music"]
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Child profile updated successfully",
  "child": {
    "child_id": "child_a1b2c3d4e5f6",
    "name": "Emma Rose",
    "age": 9,
    "gender": "girl",
    "interests": ["reading", "art", "music"],
    "updated_at": "2025-11-21T15:45:00Z"
  }
}
```

### 4. Delete Child Profile

**Endpoint**: `DELETE /children/{child_id}`

**Query Parameters**:
- `firebase_token` (string, required)

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Child profile deleted successfully"
}
```

### 5. Set Default Child

**Endpoint**: `POST /children/{child_id}/select`

**Request**:
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Default child set successfully",
  "default_child_id": "child_a1b2c3d4e5f6"
}
```

---

## Story Management

### 1. Generate Story (Async)

**Endpoint**: `POST /stories/generate`

**Headers**:
```http
Authorization: Bearer {firebase_token}
Content-Type: application/json
```

**Request**:
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "user_prompt": "A magical adventure in an enchanted forest",
  "child_name": "Emma",
  "child_age": 7,
  "morals": ["kindness", "bravery"],
  "story_length": "medium",
  "art_style": "magical",
  "voice_option": "female",
  "voice_clone_id": "vc_123...",
  "language": "english",
  "reference_image_urls": ["https://..."],
  "target_scenes": 7
}
```

**Response** (202 Accepted):
```json
{
  "success": true,
  "job_id": "job_uuid",
  "story_id": "story_uuid",
  "status": "processing",
  "message": "Story generation started. Use job_id to track progress."
}
```

**WebSocket Progress Updates**:
```javascript
const ws = new WebSocket(`wss://your-domain.com/ws/${story_id}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'progress') {
    console.log(`Progress: ${data.progress}% - ${data.message}`);
  } else if (data.type === 'complete') {
    console.log('Story generation complete!', data.manifest);
  } else if (data.type === 'error') {
    console.error('Story generation failed:', data.error);
  }
};
```

### 2. Get Story Status

**Endpoint**: `GET /stories/{story_id}/status`

**Headers**:
```http
Authorization: Bearer {firebase_token}
```

**Response** (200 OK):
```json
{
  "story_id": "story_uuid",
  "status": "processing",
  "progress": 65,
  "message": "Generating audio for scene 4...",
  "estimated_completion": "2025-11-05T22:30:00Z"
}
```

### 3. Get Story Details

**Endpoint**: `GET /stories/{story_id}`

**Headers**:
```http
Authorization: Bearer {firebase_token}
```

**Response** (200 OK):
```json
{
  "story_id": "story_uuid",
  "title": "Emma's Enchanted Forest Adventure",
  "status": "completed",
  "created_at": "2025-11-05T22:00:00Z",
  "user_id": "user_firebase_uid",
  "child_name": "Emma",
  "manifest": {
    "title": "Emma's Enchanted Forest Adventure",
    "scenes": [
      {
        "scene_number": 1,
        "text": "Once upon a time...",
        "audio_url": "https://firebasestorage.googleapis.com/.../scene_1.wav",
        "image_url": "https://firebasestorage.googleapis.com/.../scene_1.png",
        "duration": 15.5,
        "ambient_keywords": ["forest", "peaceful"]
      }
    ],
    "total_duration": 180.5,
    "scene_count": 7,
    "performance_metrics": {
      "total_time": 45.2,
      "audio_generation_time": 20.1,
      "image_generation_time": 15.3
    }
  }
}
```

### 4. List User Stories

**Endpoint**: `GET /stories`

**Headers**:
```http
Authorization: Bearer {firebase_token}
```

**Query Parameters**:
- `firebase_token` (string, required)
- `limit` (int, optional, default: 20): Number of stories to return
- `offset` (int, optional, default: 0): Pagination offset

**Response** (200 OK):
```json
{
  "stories": [
    {
      "story_id": "story_uuid_1",
      "title": "Emma's Enchanted Forest Adventure",
      "status": "completed",
      "created_at": "2025-11-05T22:00:00Z",
      "thumbnail_url": "https://...",
      "duration": 180.5
    },
    {
      "story_id": "story_uuid_2",
      "title": "The Magical Castle",
      "status": "processing",
      "created_at": "2025-11-05T21:00:00Z",
      "progress": 45
    }
  ],
  "total": 2,
  "limit": 20,
  "offset": 0
}
```

### 5. Delete Story

**Endpoint**: `DELETE /stories/{story_id}`

**Headers**:
```http
Authorization: Bearer {firebase_token}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Story deleted successfully"
}
```

### 6. Share Story

**Endpoint**: `POST /stories/{story_id}/share`

**Headers**:
```http
Authorization: Bearer {firebase_token}
Content-Type: application/json
```

**Request**:
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "share_code": "ABC123XYZ",
  "share_url": "https://your-app.com/story/ABC123XYZ",
  "expires_at": "2025-12-05T22:00:00Z"
}
```

### 7. Get Shared Story

**Endpoint**: `GET /sharing/{share_code}`

**No authentication required**

**Response** (200 OK):
```json
{
  "story_id": "story_uuid",
  "title": "Emma's Enchanted Forest Adventure",
  "manifest": {...},
  "shared_by": "John Doe",
  "created_at": "2025-11-05T22:00:00Z"
}
```

---

## IoT Device Management

### 1. Create Device (Admin Only)

**Endpoint**: `POST /iot/devices/create`

**Headers**:
```http
Content-Type: application/json
Authorization: Bearer {admin_token}
```

**Request**:
```json
{
  "device_name": "Family Room Storyteller",
  "mac_address": "AA:BB:CC:DD:EE:FF"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "device_id": "device_uuid",
  "device_secret": "secret_key",
  "qr_code_data": "STDEV:device_uuid:secret_key"
}
```

### 2. Get Claim Token

**Endpoint**: `POST /iot/devices/claim-token`

**Headers**:
```http
Content-Type: application/json
Authorization: Bearer {firebase_token}
```

**Request**:
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**Response** (200 OK):
```json
{
  "claim_token": "claim_token_jwt",
  "expires_at": "2025-11-05T22:10:00Z"
}
```

### 3. Claim Device

**Endpoint**: `POST /iot/devices/claim`

**Headers**:
```http
Content-Type: application/json
```

**Request**:
```json
{
  "device_id": "device_uuid",
  "device_secret": "secret_key",
  "claim_token": "claim_token_jwt"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Device claimed successfully",
  "device_info": {
    "device_id": "device_uuid",
    "device_name": "Family Room Storyteller",
    "claimed_by": "user_firebase_uid",
    "claimed_at": "2025-11-05T22:00:00Z"
  }
}
```

### 4. List User Devices

**Endpoint**: `GET /iot/devices`

**Headers**:
```http
Authorization: Bearer {firebase_token}
```

**Query Parameters**:
- `firebase_token` (string, required)

**Response** (200 OK):
```json
{
  "devices": [
    {
      "device_id": "device_uuid_1",
      "device_name": "Family Room Storyteller",
      "status": "online",
      "last_seen": "2025-11-05T22:00:00Z",
      "firmware_version": "1.0.0"
    },
    {
      "device_id": "device_uuid_2",
      "device_name": "Bedroom Storyteller",
      "status": "offline",
      "last_seen": "2025-11-04T18:00:00Z",
      "firmware_version": "1.0.0"
    }
  ],
  "total": 2
}
```

### 5. Get Device Intro Audio

**Endpoint**: `POST /iot/intro-audio`

**Headers**:
```http
Content-Type: application/json
```

**Request**:
```json
{
  "device_id": "device_uuid",
  "device_secret": "secret_key",
  "child_name": "Emma"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "audio_url": "https://firebasestorage.googleapis.com/.../intro.wav",
  "text": "Hi Emma! I'm June the storytelling owl...",
  "duration": 8.5
}
```

### 6. Get Available Stories for Device

**Endpoint**: `POST /iot/stories`

**Headers**:
```http
Content-Type: application/json
```

**Request**:
```json
{
  "device_id": "device_uuid",
  "device_secret": "secret_key"
}
```

**Response** (200 OK):
```json
{
  "stories": [
    {
      "story_id": "story_uuid",
      "title": "Emma's Enchanted Forest Adventure",
      "duration": 180.5,
      "thumbnail_url": "https://...",
      "created_at": "2025-11-05T22:00:00Z"
    }
  ],
  "total": 1
}
```

---

## Conversational AI (WebRTC)

### 1. Start Conversation Session

**Endpoint**: `POST /conversation/start`

**Headers**:
```http
Authorization: Bearer {firebase_token}
Content-Type: application/json
```

**Request**:
```json
{
  "user_id": "user_firebase_uid",
  "child_name": "Emma",
  "session_config": {
    "voice_id": "female",
    "language": "en-US"
  }
}
```

**Response** (200 OK):
```json
{
  "session_id": "session_uuid",
  "ice_servers": [
    {
      "urls": ["stun:stun.l.google.com:19302"]
    }
  ],
  "expires_at": "2025-11-05T23:00:00Z"
}
```

### 2. WebRTC Signaling (Offer)

**Endpoint**: `POST /conversation/{session_id}/offer`

**Headers**:
```http
Content-Type: application/json
```

**Request**:
```json
{
  "sdp": "v=0\r\no=- 123456789 2 IN IP4 127.0.0.1...",
  "type": "offer"
}
```

**Response** (200 OK):
```json
{
  "sdp": "v=0\r\no=- 987654321 2 IN IP4 127.0.0.1...",
  "type": "answer"
}
```

### 3. Add ICE Candidate

**Endpoint**: `PATCH /conversation/{session_id}/candidate`

**Headers**:
```http
Content-Type: application/json
```

**Request**:
```json
{
  "candidate": "candidate:1 1 UDP 2130706431 192.168.1.1 54321 typ host",
  "sdpMid": "0",
  "sdpMLineIndex": 0
}
```

**Response** (200 OK):
```json
{
  "success": true
}
```

### 4. End Conversation

**Endpoint**: `DELETE /conversation/{session_id}`

**Headers**:
```http
Authorization: Bearer {firebase_token}
```

**Response** (200 OK):
```json
{
  "success": true,
  "duration": 180,
  "transcript": "User: Tell me a story...\nAI: Once upon a time..."
}
```

**Full WebRTC Integration Example (React Native)**:
```javascript
import { RTCPeerConnection, RTCSessionDescription, mediaDevices } from 'react-native-webrtc';

const startConversation = async () => {
  // 1. Start session
  const sessionResponse = await fetch(`${API_BASE_URL}/conversation/start`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      user_id: userId,
      child_name: 'Emma'
    })
  });
  
  const { session_id, ice_servers } = await sessionResponse.json();
  
  // 2. Create peer connection
  const pc = new RTCPeerConnection({ iceServers: ice_servers });
  
  // 3. Get local audio stream
  const stream = await mediaDevices.getUserMedia({ audio: true, video: false });
  stream.getTracks().forEach(track => pc.addTrack(track, stream));
  
  // 4. Handle ICE candidates
  pc.onicecandidate = async (event) => {
    if (event.candidate) {
      await fetch(`${API_BASE_URL}/conversation/${session_id}/candidate`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          candidate: event.candidate.candidate,
          sdpMid: event.candidate.sdpMid,
          sdpMLineIndex: event.candidate.sdpMLineIndex
        })
      });
    }
  };
  
  // 5. Handle remote stream
  pc.ontrack = (event) => {
    console.log('Receiving audio from AI...');
    // Play remote audio stream
  };
  
  // 6. Create and send offer
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  
  const offerResponse = await fetch(`${API_BASE_URL}/conversation/${session_id}/offer`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      sdp: offer.sdp,
      type: offer.type
    })
  });
  
  const { sdp: answerSdp, type: answerType } = await offerResponse.json();
  await pc.setRemoteDescription(new RTCSessionDescription({
    sdp: answerSdp,
    type: answerType
  }));
  
  return { sessionId: session_id, peerConnection: pc };
};
```

---

## WebSocket Real-Time Updates

### Story Generation Progress

**WebSocket URL**: `ws(s)://your-domain.com/ws/{story_id}`

**Connection**: 
```javascript
const ws = new WebSocket(`wss://your-domain.com/ws/${story_id}`);
```

**Message Types**:

1. **Progress Update**
```json
{
  "type": "progress",
  "story_id": "story_uuid",
  "progress": 45,
  "message": "Generating images for scene 3...",
  "current_scene": 3,
  "total_scenes": 7
}
```

2. **Completion**
```json
{
  "type": "complete",
  "story_id": "story_uuid",
  "manifest": {...},
  "message": "Story generation completed successfully!"
}
```

3. **Error**
```json
{
  "type": "error",
  "story_id": "story_uuid",
  "error": "Failed to generate audio",
  "message": "Story generation failed"
}
```

**Complete WebSocket Implementation**:
```javascript
const connectToStoryProgress = (storyId, callbacks) => {
  const ws = new WebSocket(`wss://your-domain.com/ws/${storyId}`);
  
  ws.onopen = () => {
    console.log('WebSocket connected');
    callbacks.onOpen?.();
  };
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
      case 'progress':
        callbacks.onProgress?.(data.progress, data.message);
        break;
      case 'complete':
        callbacks.onComplete?.(data.manifest);
        ws.close();
        break;
      case 'error':
        callbacks.onError?.(data.error);
        ws.close();
        break;
    }
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    callbacks.onError?.(error);
  };
  
  ws.onclose = () => {
    console.log('WebSocket closed');
    callbacks.onClose?.();
  };
  
  return ws;
};

// Usage
const ws = connectToStoryProgress(storyId, {
  onProgress: (progress, message) => {
    setProgress(progress);
    setStatusMessage(message);
  },
  onComplete: (manifest) => {
    setStory(manifest);
    setProgress(100);
  },
  onError: (error) => {
    alert(`Story generation failed: ${error}`);
  }
});
```

---

## Error Handling

### Standard Error Response Format

```json
{
  "detail": "Error message here",
  "status_code": 400,
  "error_type": "validation_error"
}
```

### Common HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Request completed successfully |
| 201 | Created | Resource created successfully |
| 202 | Accepted | Async operation started |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Service temporarily down |

### Error Handling Best Practices

```javascript
const handleApiError = (error, response) => {
  if (response.status === 401) {
    // Token expired - refresh or redirect to login
    return refreshTokenAndRetry();
  } else if (response.status === 429) {
    // Rate limited - show user-friendly message
    Alert.alert('Too Many Requests', 'Please wait a moment and try again.');
  } else if (response.status === 503) {
    // Service down - retry with exponential backoff
    return retryWithBackoff(() => makeRequest());
  } else if (response.status >= 500) {
    // Server error - log and show generic message
    logError(error);
    Alert.alert('Server Error', 'Something went wrong. Please try again later.');
  } else {
    // Client error - show specific error message
    const errorData = await response.json();
    Alert.alert('Error', errorData.detail || 'An error occurred');
  }
};

// Usage
try {
  const response = await fetch(url, options);
  if (!response.ok) {
    await handleApiError(new Error('API Error'), response);
  }
  return await response.json();
} catch (error) {
  console.error('Network error:', error);
  Alert.alert('Network Error', 'Please check your internet connection');
}
```

---

## Rate Limits & Best Practices

### Rate Limits

| Endpoint Category | Rate Limit | Window |
|-------------------|------------|--------|
| Authentication | 10 requests | per minute |
| Story Generation | 3 requests | per minute |
| Story Retrieval | 60 requests | per minute |
| IoT Device | 30 requests | per minute |
| WebSocket | 5 connections | concurrent |

### Best Practices

#### 1. Token Management
```javascript
// Always refresh tokens proactively
const REFRESH_BUFFER = 5 * 60 * 1000; // 5 minutes

const getValidToken = async () => {
  const token = await AsyncStorage.getItem('firebase_token');
  const expiryTime = await AsyncStorage.getItem('token_expiry');
  
  if (Date.now() + REFRESH_BUFFER > parseInt(expiryTime)) {
    return await refreshToken();
  }
  
  return token;
};
```

#### 2. Request Retry Logic
```javascript
const fetchWithRetry = async (url, options, maxRetries = 3) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return response;
      
      if (response.status === 429) {
        // Rate limited - wait before retry
        await new Promise(resolve => setTimeout(resolve, (i + 1) * 1000));
        continue;
      }
      
      throw new Error(`HTTP ${response.status}`);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, (i + 1) * 1000));
    }
  }
};
```

#### 3. Caching
```javascript
// Cache story list to reduce API calls
const cachedStories = useRef(null);
const lastFetch = useRef(0);
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

const getStories = async (forceRefresh = false) => {
  const now = Date.now();
  
  if (!forceRefresh && 
      cachedStories.current && 
      now - lastFetch.current < CACHE_DURATION) {
    return cachedStories.current;
  }
  
  const stories = await fetchStories();
  cachedStories.current = stories;
  lastFetch.current = now;
  
  return stories;
};
```

#### 4. Optimistic Updates
```javascript
// Update UI immediately, sync with server in background
const deleteStory = async (storyId) => {
  // 1. Optimistically update UI
  setStories(prev => prev.filter(s => s.id !== storyId));
  
  try {
    // 2. Sync with server
    await fetch(`${API_BASE_URL}/stories/${storyId}`, {
      method: 'DELETE',
      headers: {'Authorization': `Bearer ${token}`}
    });
  } catch (error) {
    // 3. Revert on error
    setStories(prev => [...prev, deletedStory]);
    Alert.alert('Error', 'Failed to delete story');
  }
};
```

#### 5. Connection State Management
```javascript
import NetInfo from '@react-native-community/netinfo';

// Monitor connection state
const [isOnline, setIsOnline] = useState(true);

useEffect(() => {
  const unsubscribe = NetInfo.addEventListener(state => {
    setIsOnline(state.isConnected);
  });
  
  return unsubscribe;
}, []);

// Queue offline requests
const offlineQueue = useRef([]);

const makeRequest = async (url, options) => {
  if (!isOnline) {
    offlineQueue.current.push({ url, options });
    Alert.alert('Offline', 'Request saved. Will sync when online.');
    return;
  }
  
  return await fetch(url, options);
};

// Process queue when back online
useEffect(() => {
  if (isOnline && offlineQueue.current.length > 0) {
    Promise.all(
      offlineQueue.current.map(req => fetch(req.url, req.options))
    ).then(() => {
      offlineQueue.current = [];
    });
  }
}, [isOnline]);
```

---

## Complete API Client Example

```javascript
// api-client.js
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE_URL = 'https://your-domain.com';

class APIClient {
  async getToken() {
    return await AsyncStorage.getItem('firebase_token');
  }
  
  async refreshToken() {
    const refreshToken = await AsyncStorage.getItem('refresh_token');
    const response = await fetch(`${API_BASE_URL}/auth/refresh-token`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ refresh_token: refreshToken })
    });
    
    const data = await response.json();
    await AsyncStorage.setItem('firebase_token', data.firebase_token);
    await AsyncStorage.setItem('refresh_token', data.refresh_token);
    
    return data.firebase_token;
  }
  
  async request(endpoint, options = {}) {
    let token = await this.getToken();
    
    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers
      }
    };
    
    let response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    
    // Auto-refresh token on 401
    if (response.status === 401) {
      token = await this.refreshToken();
      config.headers['Authorization'] = `Bearer ${token}`;
      response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    }
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Request failed');
    }
    
    return await response.json();
  }
  
  // Authentication
  async signUp(email, password, displayName) {
    return this.request('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName })
    });
  }
  
  async signIn(email, password) {
    return this.request('/auth/signin', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
  }
  
  // Stories
  async generateStory(params) {
    return this.request('/stories/generate', {
      method: 'POST',
      body: JSON.stringify(params)
    });
  }
  
  async getStory(storyId) {
    return this.request(`/stories/${storyId}`);
  }
  
  async listStories(limit = 20, offset = 0) {
    return this.request(`/stories?limit=${limit}&offset=${offset}`);
  }
  
  async deleteStory(storyId) {
    return this.request(`/stories/${storyId}`, { method: 'DELETE' });
  }
  
  // User Management
  async getProfile() {
    const token = await this.getToken();
    return this.request(`/users/profile?firebase_token=${token}`);
  }
  
  async updateProfile(profile) {
    return this.request('/users/profile', {
      method: 'PUT',
      body: JSON.stringify(profile)
    });
  }
}

export default new APIClient();
```

**Usage**:
```javascript
import API from './api-client';

// Sign in
const handleSignIn = async () => {
  try {
    const data = await API.signIn(email, password);
    await AsyncStorage.setItem('firebase_token', data.firebase_token);
    await AsyncStorage.setItem('refresh_token', data.refresh_token);
    navigation.navigate('Home');
  } catch (error) {
    Alert.alert('Error', error.message);
  }
};

// Generate story
const handleGenerateStory = async () => {
  try {
    const { story_id } = await API.generateStory({
      user_prompt: "A magical adventure",
      child_name: "Emma",
      child_age: 7
    });
    
    // Connect to WebSocket for progress
    const ws = new WebSocket(`wss://your-domain.com/ws/${story_id}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'progress') {
        setProgress(data.progress);
      } else if (data.type === 'complete') {
        setStory(data.manifest);
        ws.close();
      }
    };
  } catch (error) {
    Alert.alert('Error', error.message);
  }
};
```

---

## Additional Resources

- **OpenAPI Spec**: `{BASE_URL}/openapi.json`
- **Health Check**: `{BASE_URL}/health`
- **API Status**: `{BASE_URL}/admin/status` (admin only)

For more detailed implementation guides, see:
- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) - Backend development
- [IMPLEMENTATION_DETAILS.md](./IMPLEMENTATION_DETAILS.md) - Technical deep-dives
- [CONVERSATIONAL_AI_DOCS.md](./CONVERSATIONAL_AI_DOCS.md) - WebRTC AI details
