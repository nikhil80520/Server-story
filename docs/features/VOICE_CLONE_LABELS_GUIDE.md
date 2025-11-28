# Voice Clone Labels & Background Noise Removal Guide

## 🎯 Overview

The voice clone endpoints now support **ElevenLabs labels** (age, language, accent) and **background noise removal** for improved voice quality and categorization.

---

## 🏷️ Labels Format

Labels help categorize and optimize voice clones. The format is a dictionary with these fields:

```json
{
  "age": "child",        // Voice age category
  "language": "english", // Voice language (defaults to "english")
  "accent": "british"    // Voice accent (important for quality)
}
```

### Age Options
- `"child"` - For children's voices
- `"young"` - For young adult voices
- `"middle_aged"` - For middle-aged voices
- `"old"` - For senior voices

### Language Options
The language field defaults to `"english"` if not specified. Other options include:
- `"english"`
- `"spanish"`
- `"french"`
- `"german"`
- `"italian"`
- `"portuguese"`
- `"chinese"`
- `"japanese"`
- `"korean"`
- And more...

### Accent Options (Most Important!)
Accent is the most critical field for voice quality. Available accents:

**English Variants:**
- `"american"` - Standard American English
- `"british"` - British English
- `"australian"` - Australian English
- `"canadian"` - Canadian English
- `"irish"` - Irish English
- `"scottish"` - Scottish English
- `"welsh"` - Welsh English
- `"south_african"` - South African English
- `"new_zealand"` - New Zealand English
- `"indian"` - Indian English
- `"caribbean"` - Caribbean English

**Other Accents:**
- `"spanish"` - Spanish accent
- `"french"` - French accent
- `"german"` - German accent
- `"italian"` - Italian accent
- `"russian"` - Russian accent
- `"chinese"` - Chinese accent
- `"japanese"` - Japanese accent
- `"african"` - African accent
- `"european"` - General European accent
- `"middle_eastern"` - Middle Eastern accent
- `"other"` - Other/unspecified accent

---

## 🔇 Background Noise Removal

**Default:** `true` (enabled by default for better quality)

ElevenLabs will automatically remove background noise from voice samples using their audio isolation model. 

⚠️ **Note:** If your samples don't include background noise, this can potentially make the quality worse. Only disable if you have studio-quality recordings.

---

## 📡 API Endpoints

### 1. Create Voice Clone - Multipart (Recommended)

**Endpoint:** `POST /users/voice-clone/create-multipart`

**Content-Type:** `multipart/form-data`

**Parameters:**
- `firebase_token` (required): Firebase authentication token
- `voice_name` (required): Name for the voice clone
- `description` (optional): Description of the voice clone
- `audio_file` (required): Audio file (WAV, MP3, FLAC, M4A, OGG)
- `labels` (optional): JSON string with labels
- `remove_background_noise` (optional): "true" or "false" (default: "true")

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/users/voice-clone/create-multipart" \
  -F "firebase_token=your_firebase_token" \
  -F "voice_name=Millie's Voice" \
  -F "description=Child voice for personalized storytelling" \
  -F "audio_file=@millie_voice.wav;type=audio/wav" \
  -F 'labels={"age": "child", "language": "english", "accent": "british"}' \
  -F "remove_background_noise=true"
```

**iOS/Swift Example:**
```swift
let url = URL(string: "https://your-api/users/voice-clone/create-multipart")!
var request = URLRequest(url: url)
request.httpMethod = "POST"

let boundary = "Boundary-\(UUID().uuidString)"
request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

var data = Data()

// Add firebase_token
data.append("--\(boundary)\r\n".data(using: .utf8)!)
data.append("Content-Disposition: form-data; name=\"firebase_token\"\r\n\r\n".data(using: .utf8)!)
data.append("\(firebaseToken)\r\n".data(using: .utf8)!)

// Add voice_name
data.append("--\(boundary)\r\n".data(using: .utf8)!)
data.append("Content-Disposition: form-data; name=\"voice_name\"\r\n\r\n".data(using: .utf8)!)
data.append("Millie's Voice\r\n".data(using: .utf8)!)

// Add description
data.append("--\(boundary)\r\n".data(using: .utf8)!)
data.append("Content-Disposition: form-data; name=\"description\"\r\n\r\n".data(using: .utf8)!)
data.append("Child voice for storytelling\r\n".data(using: .utf8)!)

// Add labels (JSON string)
let labels = ["age": "child", "language": "english", "accent": "british"]
let labelsJSON = try JSONEncoder().encode(labels)
let labelsString = String(data: labelsJSON, encoding: .utf8)!
data.append("--\(boundary)\r\n".data(using: .utf8)!)
data.append("Content-Disposition: form-data; name=\"labels\"\r\n\r\n".data(using: .utf8)!)
data.append("\(labelsString)\r\n".data(using: .utf8)!)

// Add remove_background_noise
data.append("--\(boundary)\r\n".data(using: .utf8)!)
data.append("Content-Disposition: form-data; name=\"remove_background_noise\"\r\n\r\n".data(using: .utf8)!)
data.append("true\r\n".data(using: .utf8)!)

// Add audio file
data.append("--\(boundary)\r\n".data(using: .utf8)!)
data.append("Content-Disposition: form-data; name=\"audio_file\"; filename=\"audio.wav\"\r\n".data(using: .utf8)!)
data.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
data.append(audioData)
data.append("\r\n".data(using: .utf8)!)

// Close boundary
data.append("--\(boundary)--\r\n".data(using: .utf8)!)

request.httpBody = data
```

---

### 2. Update Voice Clone - Multipart (Recommended)

**Endpoint:** `PUT /users/voice-clone/update-multipart`

**Same parameters as create-multipart**

---

### 3. Create Voice Clone - Simple JSON

**Endpoint:** `POST /users/voice-clone/create-simple`

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "firebase_token": "your_firebase_token",
  "voice_name": "Millie's Voice",
  "description": "Child voice for personalized storytelling",
  "audio_base64": "base64_encoded_audio_data...",
  "audio_format": "wav",
  "labels": {
    "age": "child",
    "language": "english",
    "accent": "british"
  },
  "remove_background_noise": true
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/users/voice-clone/create-simple" \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "your_token",
    "voice_name": "Millie'\''s Voice",
    "description": "Child voice for storytelling",
    "audio_base64": "UklGRiQAAABXQVZFZm10...",
    "audio_format": "wav",
    "labels": {
      "age": "child",
      "language": "english",
      "accent": "british"
    },
    "remove_background_noise": true
  }'
```

**iOS/Swift Example:**
```swift
struct VoiceCloneRequest: Codable {
    let firebase_token: String
    let voice_name: String
    let description: String
    let audio_base64: String
    let audio_format: String
    let labels: [String: String]?
    let remove_background_noise: Bool?
}

let audioBase64 = audioData.base64EncodedString()

let request = VoiceCloneRequest(
    firebase_token: firebaseToken,
    voice_name: "Millie's Voice",
    description: "Child voice for storytelling",
    audio_base64: audioBase64,
    audio_format: "wav",
    labels: [
        "age": "child",
        "language": "english",
        "accent": "british"
    ],
    remove_background_noise: true
)

let jsonData = try JSONEncoder().encode(request)

var urlRequest = URLRequest(url: url)
urlRequest.httpMethod = "POST"
urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
urlRequest.httpBody = jsonData
```

---

### 4. Update Voice Clone - Simple JSON

**Endpoint:** `PUT /users/voice-clone/update-simple`

**Same request body format as create-simple**

---

## 🎯 Best Practices

### For Children's Voices
```json
{
  "age": "child",
  "language": "english",
  "accent": "american"  // or "british", "australian", etc.
}
```

### For Adult Voices
```json
{
  "age": "middle_aged",
  "language": "english",
  "accent": "american"
}
```

### For Specific Accents
Always specify the accent that best matches the voice sample for optimal results:
```json
{
  "age": "young",
  "language": "english",
  "accent": "british"  // Use the exact accent from the recording
}
```

---

## 🔍 Response Format

All endpoints return:
```json
{
  "success": true,
  "message": "Voice clone created successfully",
  "voice_clone_id": "elevenlabs_voice_id",
  "voice_name": "Millie's Voice",
  "user_id": "firebase_user_id",
  "audio_format": "wav",
  "audio_size_bytes": 1234567
}
```

---

## ⚠️ Important Notes

1. **Labels are optional** - If not provided, ElevenLabs will use default settings
2. **Language defaults to "english"** - Automatically set if not specified
3. **Accent is most important** - Has the biggest impact on voice quality
4. **Background noise removal is enabled by default** - Only disable for studio recordings
5. **All fields are case-sensitive** - Use lowercase for accents (e.g., "british" not "British")

---

## 🚀 Migration from Old Endpoints

**Old endpoints (without labels):**
```bash
# Still works - labels and noise removal use defaults
curl -F "firebase_token=..." -F "voice_name=..." -F "audio_file=@audio.wav"
```

**New endpoints (with labels):**
```bash
# Enhanced with labels and noise control
curl -F "firebase_token=..." -F "voice_name=..." -F "audio_file=@audio.wav" \
     -F 'labels={"age":"child","accent":"british"}' \
     -F "remove_background_noise=true"
```

**All old code continues to work!** Labels and noise removal are optional enhancements.

---

## 📞 Support

For questions about:
- **Accent options**: Use the list above, or `"other"` for unlisted accents
- **Audio quality**: Enable `remove_background_noise` for noisy recordings
- **Language support**: Default to "english", or specify target language
- **Age categories**: Choose the closest match from the age options

The labels help ElevenLabs optimize the voice clone for your specific use case!
