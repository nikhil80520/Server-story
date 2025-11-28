# Voice Clone API Documentation

## Overview

The Voice Clone API allows users to create and update custom voice clones using the ElevenLabs AI voice synthesis platform. Users can upload audio samples (minimum 4.6 seconds) to create personalized voice models for text-to-speech generation.

## Authentication

All endpoints require Firebase authentication via the `firebase_token` parameter in the request body (NOT header-based auth).

## Audio Requirements

- **Minimum Duration**: 4.6 seconds (ElevenLabs requirement)
- **Recommended Duration**: 10+ seconds for best quality
- **Supported Formats**: WAV, MP3, M4A, FLAC, OGG
- **Maximum File Size**: 25MB
- **Recommended Settings**:
  - Sample Rate: 44.1kHz
  - Channels: Mono (1 channel)
  - Bit Depth: 16-bit
  - Format: WAV (best quality)

---

## Endpoint 1: Create Voice Clone

### Request Details
- **Method**: `POST`
- **Endpoint**: `/users/voice-clone/create`
- **Content-Type**: `application/json`

### Request Schema

**⚠️ IMPORTANT**: The API expects a complex `AudioData` object, NOT a simple base64 string.

```typescript
interface VoiceCloneCreateRequest {
  firebase_token: string;
  voice_name: string;
  description: string;
  audio_data: AudioData;  // Complex object, not simple base64!
}

interface AudioData {
  base64: string;              // Base64 encoded audio data
  format: string;              // Audio format: "wav", "mp3", "m4a", etc.
  mime_type: string;           // MIME type: "audio/wav", "audio/mpeg", etc.
  size_bytes: number;          // File size in bytes
  duration_ms?: number;        // Duration in milliseconds (optional)
  sample_rate?: number;        // Sample rate (default: 44100)
  channels?: number;           // Channel count (default: 1)
  platform?: string;          // Source platform (optional)
  corruption_check: CorruptionCheck;  // REQUIRED validation object
}

interface CorruptionCheck {
  null_bytes: number;          // Count of null bytes (should be 0)
  base64_length: number;       // Length of base64 string
  is_valid_base64: boolean;    // Base64 validation result
}
```

### ✅ Working Example Request

```javascript
// JavaScript/TypeScript Example
const createVoiceClone = async (audioFile, voiceName, description, firebaseToken) => {
  // Convert audio file to base64
  const arrayBuffer = await audioFile.arrayBuffer();
  const audioData = new Uint8Array(arrayBuffer);
  const base64Audio = btoa(String.fromCharCode(...audioData));
  
  const payload = {
    firebase_token: firebaseToken,
    voice_name: voiceName,
    description: description,
    audio_data: {  // Complex AudioData object
      base64: base64Audio,
      format: "wav",
      mime_type: "audio/wav", 
      size_bytes: audioFile.size,
      duration_ms: 10000, // 10 seconds
      sample_rate: 44100,
      channels: 1,
      platform: "web",
      corruption_check: {  // REQUIRED validation
        null_bytes: 0,
        base64_length: base64Audio.length,
        is_valid_base64: true
      }
    }
  };

  const response = await fetch('/users/voice-clone/create', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload)
  });

  return await response.json();
};
```

```python
# Python Example (WORKING - tested with real audio)
import base64
import requests

def create_voice_clone(audio_file_path, voice_name, description, firebase_token):
    # Read and encode audio file
    with open(audio_file_path, 'rb') as f:
        audio_data = f.read()
    
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    file_size = len(audio_data)
    
    payload = {
        "firebase_token": firebase_token,
        "voice_name": voice_name,
        "description": description,
        "audio_data": {  # Complex AudioData object
            "base64": audio_base64,
            "format": "wav",
            "mime_type": "audio/wav",
            "size_bytes": file_size,
            "duration_ms": 10000,
            "sample_rate": 44100,
            "channels": 1,
            "platform": "python",
            "corruption_check": {  # REQUIRED validation
                "null_bytes": 0,
                "base64_length": len(audio_base64),
                "is_valid_base64": True
            }
        }
    }
    
    response = requests.post(
        "http://localhost:8000/users/voice-clone/create",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    return response.json()
```

### Response Schema

```typescript
interface VoiceCloneCreateResponse {
  success: boolean;
  message: string;
  voice_clone_id: string;      // ElevenLabs voice ID
  voice_name: string;          // Name of the created voice
  user_id: string;             // Firebase user ID
  audio_format: string;        // Processed audio format
  audio_size_bytes: number;    // Size of audio data processed
}
```

### ✅ Example Success Response

```json
{
  "success": true,
  "message": "Voice clone created successfully",
  "voice_clone_id": "SiG8S5wPMv0gkqL7KhPf",
  "voice_name": "MyCustomVoice",
  "user_id": "CnHUiHOSe0RGDPPev6fAeY4YfXj1",
  "audio_format": "wav",
  "audio_size_bytes": 882078
}

#### Error Responses

**400 Bad Request - Missing Fields**
```json
{
    "detail": "Missing required field: <field_name>"
}
```

**400 Bad Request - Invalid Format**
```json
{
    "detail": "Invalid audio format. Supported formats: wav, mp3, m4a"
}
```

**400 Bad Request - Audio Too Short**
```json
{
    "detail": "Failed to create voice clone: Voice clone creation failed: ElevenLabs API error 400: {\"detail\":{\"status\":\"voice_sample_too_short\",\"message\":\"All voice samples must be at least 4.6 seconds long when removing background noise.\"}}"
}
```

**409 Conflict - Voice Already Exists**
```json
{
    "detail": "User already has a voice clone"
}
```

**401 Unauthorized**
```json
{
    "detail": "Authentication required"
}
```

**500 Internal Server Error**
```json
{
    "detail": "Failed to create voice clone: <error_message>"
}
```

---

## Endpoint 2: Update Voice Clone

### Request Details
- **Method**: `PUT` ⚠️ (NOT POST!)
- **Endpoint**: `/users/voice-clone/update`
- **Content-Type**: `application/json`

### Request Schema

**The request schema is identical to the create endpoint** - same complex `AudioData` object required.

```typescript
interface VoiceCloneUpdateRequest {
  firebase_token: string;
  voice_name: string;
  description: string;
  audio_data: AudioData;  // Same complex AudioData object as create
}
```

### ✅ Working Example Request

```javascript
// JavaScript/TypeScript Example
const updateVoiceClone = async (audioFile, newVoiceName, newDescription, firebaseToken) => {
  // Convert audio file to base64 (same process as create)
  const arrayBuffer = await audioFile.arrayBuffer();
  const audioData = new Uint8Array(arrayBuffer);
  const base64Audio = btoa(String.fromCharCode(...audioData));
  
  const payload = {
    firebase_token: firebaseToken,
    voice_name: newVoiceName,
    description: newDescription,
    audio_data: {  // Same complex AudioData object
      base64: base64Audio,
      format: "wav",
      mime_type: "audio/wav",
      size_bytes: audioFile.size,
      duration_ms: 10000,
      sample_rate: 44100,
      channels: 1,
      platform: "web",
      corruption_check: {
        null_bytes: 0,
        base64_length: base64Audio.length,
        is_valid_base64: true
      }
    }
  };

  const response = await fetch('/users/voice-clone/update', {
    method: 'PUT',  // ⚠️ PUT method for update!
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload)
  });

  return await response.json();
};
```

```python
# Python Example (WORKING - tested with real audio)
def update_voice_clone(audio_file_path, new_voice_name, new_description, firebase_token):
    # Same audio processing as create
    with open(audio_file_path, 'rb') as f:
        audio_data = f.read()
    
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    file_size = len(audio_data)
    
    payload = {
        "firebase_token": firebase_token,
        "voice_name": new_voice_name,
        "description": new_description,
        "audio_data": {  # Same complex AudioData object
            "base64": audio_base64,
            "format": "wav",
            "mime_type": "audio/wav",
            "size_bytes": file_size,
            "duration_ms": 10000,
            "sample_rate": 44100,
            "channels": 1,
            "platform": "python",
            "corruption_check": {
                "null_bytes": 0,
                "base64_length": len(audio_base64),
                "is_valid_base64": True
            }
        }
    }
    
    response = requests.put(  # ⚠️ PUT method for update!
        "http://localhost:8000/users/voice-clone/update",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    return response.json()
```

### Response Schema

```typescript
interface VoiceCloneUpdateResponse {
  success: boolean;
  message: string;
  old_voice_clone_id: string;  // Previous voice ID (deleted)
  new_voice_clone_id: string;  // New voice ID (created) 
  voice_name: string;          // Updated voice name
  user_id: string;             // Firebase user ID
  audio_format: string;        // Processed audio format
  audio_size_bytes: number;    // Size of audio data processed
  operation: string;           // Always "replace"
}
```

### ✅ Example Success Response

```json
{
  "success": true,
  "message": "Voice clone updated successfully",
  "old_voice_clone_id": "SiG8S5wPMv0gkqL7KhPf",
  "new_voice_clone_id": "VqHKzbeuP7abCswzez28",
  "voice_name": "MyUpdatedVoice",
  "user_id": "CnHUiHOSe0RGDPPev6fAeY4YfXj1",
  "audio_format": "wav", 
  "audio_size_bytes": 882078,
  "operation": "replace"
}

---

## Error Handling

### Common Error Codes

- **400 Bad Request**: Invalid audio data, unsupported format, or corrupted file
- **401 Unauthorized**: Invalid or expired Firebase token
- **409 Conflict**: User profile not found or voice clone already exists
- **413 Payload Too Large**: Audio file exceeds 25MB limit
- **422 Unprocessable Entity**: Invalid request format or missing required fields
- **500 Internal Server Error**: Server-side processing error

### Error Response Format

```typescript
interface ErrorResponse {
  detail: string;  // Error description
}
```

### Example Error Responses

```json
// Audio too short (most common error)
{
  "detail": "Audio duration too short. Minimum 4.6 seconds required for voice cloning."
}

// Invalid audio format
{
  "detail": "Unsupported audio format: mp4. Allowed: ['m4a', 'wav', 'mp3']"
}

// File too large
{
  "detail": "Audio file too large (max 25MB)"
}

// Corrupted audio data
{
  "detail": "Corrupted audio data detected: 150 null bytes found"
}

// Missing AudioData structure (common integration error)
{
  "detail": "Invalid audio_data format. Expected AudioData object with base64, format, mime_type, size_bytes, and corruption_check fields."
}

// User already has voice clone (create endpoint)
{
  "detail": "User already has a voice clone"
}

// User doesn't have voice clone (update endpoint)  
{
  "detail": "User does not have an existing voice clone to update"
}
```

---

## Best Practices

### Audio Quality Tips

1. **Use WAV format** for best quality and compatibility
2. **Record in quiet environment** to minimize background noise
3. **Speak clearly and naturally** with consistent volume
4. **Use 44.1kHz sample rate** for optimal processing
5. **Keep recordings between 10-30 seconds** for best results
6. **Use mono audio** to reduce file size

### Integration Tips

1. **Validate audio duration** client-side before uploading
2. **Use the complex AudioData structure** - NOT simple base64 string
3. **Include corruption_check validation** in every request
4. **Handle errors gracefully** with user-friendly messages
5. **Use PUT method for updates** - NOT POST
6. **Implement progress indicators** for large file uploads

### Security Considerations

1. **Always use HTTPS** in production
2. **Validate Firebase tokens** server-side
3. **Implement rate limiting** to prevent abuse
4. **Sanitize file uploads** to prevent malicious content
5. **Log operations** for audit trails

---

## Testing & Examples

### ✅ Tested and Working Examples

Our API has been thoroughly tested with real audio files. The following test files demonstrate working implementations:

1. **`test_voice_real_audio_fixed.py`** - Complete create endpoint test
2. **`test_update_endpoint.py`** - Complete update endpoint test  
3. **`test_voice_clone_curl.sh`** - cURL script examples

### Audio Conversion for Testing

Convert your audio files to the proper format using FFmpeg:

```bash
# Convert OPUS to WAV (10 seconds, 44.1kHz, mono)
ffmpeg -i example.opus -t 10 -ar 44100 -ac 1 test_output.wav

# Check file details
ffmpeg -i test_output.wav 2>&1 | grep Duration
```

### Test Results (Real Audio)

✅ **Successful Tests Performed:**
- **File**: `test_output.wav` (882,078 bytes, 10 seconds)
- **Create Endpoint**: Status 200, Voice ID: `SiG8S5wPMv0gkqL7KhPf`
- **Update Endpoint**: Status 200, New Voice ID: `VqHKzbeuP7abCswzez28`
- **Base64 Size**: 1,176,104 characters
- **Format Detection**: WAV successfully detected and processed

---

## Rate Limits & Quotas

- **ElevenLabs Free Tier**: Limited monthly character generation
- **File Size Limit**: 25MB per audio file
- **Concurrent Requests**: Recommended max 2-3 simultaneous uploads
- **Minimum Duration**: 4.6 seconds (ElevenLabs requirement)
- **Maximum Duration**: No hard limit, but 30+ seconds may impact performance

---

## Common Integration Issues

### ❌ Wrong API Format (Will Fail)

```json
// DON'T DO THIS - Simple string format (old/incorrect)
{
  "firebase_token": "...",
  "voice_name": "Test",
  "description": "Test voice",
  "audio": "base64_string_here",  // ❌ Wrong!
  "format": "wav"
}
```

### ✅ Correct API Format (Will Work)

```json
// DO THIS - Complex AudioData object (correct)
{
  "firebase_token": "...",
  "voice_name": "Test", 
  "description": "Test voice",
  "audio_data": {  // ✅ Correct complex object!
    "base64": "base64_string_here",
    "format": "wav",
    "mime_type": "audio/wav", 
    "size_bytes": 882078,
    "corruption_check": {
      "null_bytes": 0,
      "base64_length": 1176104,
      "is_valid_base64": true
    }
  }
}
```

### Method Confusion

- **Create**: `POST /users/voice-clone/create` ✅
- **Update**: `PUT /users/voice-clone/update` ✅ (NOT POST!)

---

## Support & Troubleshooting

### Debug Information

The server logs detailed information about:
- Audio format detection results
- File size and duration validation
- ElevenLabs API responses
- User authentication status
- Error stack traces for debugging

### Contact & Issues

- Check server logs for detailed error information
- Verify audio file meets minimum 4.6-second requirement
- Ensure proper `AudioData` object structure
- Test with provided working examples first

---

*Last updated: December 2024*  
*API Version: 1.0*  
*Status: ✅ Fully tested with real audio*  
*ElevenLabs Integration: Active*