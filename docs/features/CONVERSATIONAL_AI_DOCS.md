# Conversational AI WebRTC Endpoint

## Overview
Real-time conversational AI storytelling using WebRTC for voice interaction.

## Endpoint
```
POST /conversation/api/offer          # Web mode (browsers)
POST /conversation/api/offer/esp32    # ESP32 mode (embedded devices)
PATCH /conversation/api/offer         # ICE candidates (web)
PATCH /conversation/api/offer/esp32   # ICE candidates (ESP32)
GET /conversation/health              # Health check
```

## Features
- ✅ Firebase authentication via session token
- ✅ Optional story-specific mode (narrate a particular story)
- ✅ Free-form storytelling mode (create stories on the fly)
- ✅ Real-time voice interaction via WebRTC
- ✅ Child-personalized responses (uses child name and age)
- ✅ Low-latency audio processing
- ✅ Automatic session cleanup

## API Usage

### 1. Start Conversation

#### Web Mode (Browsers)

```http
POST /conversation/api/offer
Content-Type: application/json

{
  "session_token": "firebase_id_token_here",
  "story_id": "optional_story_id_here",
  "sdp": "webrtc_sdp_offer",
  "type": "offer",
  "pc_id": "unique_connection_id"
}
```

**Parameters:**
- `session_token` (required): Firebase ID token for authentication
- `story_id` (optional): If provided, AI will narrate only this story
- `sdp` (required): WebRTC SDP offer
- `type` (required): Always "offer"
- `pc_id` (optional): Unique peer connection identifier

**Response:**
```json
{
  "type": "answer",
  "sdp": "webrtc_sdp_answer"
}
```

#### ESP32 Mode (Embedded Devices)

```http
POST /conversation/api/offer/esp32
Content-Type: application/json

{
  "session_token": "firebase_id_token_or_iot_session_token",
  "story_id": "optional_story_id_here",
  "sdp": "webrtc_sdp_offer",
  "type": "offer",
  "pc_id": "unique_connection_id"
}
```

**Parameters:** Same as web mode, but optimized for ESP32

**Response:**
```json
{
  "type": "answer",
  "sdp": "esp32_optimized_sdp_answer"
}
```

**Key Differences:**
- Uses ESP32-specific SDP munging
- Optimized audio codec settings
- Lower bandwidth requirements
- Compatible with ESP32 WebRTC libraries

### 2. ICE Candidate Update

#### Web Mode
```http
PATCH /conversation/api/offer
Content-Type: application/json

{
  "pc_id": "connection_id",
  "candidates": [
    {
      "candidate": "ice_candidate_string",
      "sdp_mid": "0",
      "sdp_mline_index": 0
    }
  ]
}
```

#### ESP32 Mode
```http
PATCH /conversation/api/offer/esp32
Content-Type: application/json

{
  "pc_id": "connection_id",
  "candidates": [
    {
      "candidate": "ice_candidate_string",
      "sdp_mid": "0",
      "sdp_mline_index": 0
    }
  ]
}
```

### 3. Health Check

```http
GET /conversation/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "conversational-ai",
  "active_sessions": 2
}
```

## Modes

### Connection Modes

#### Web Mode (Default)
**Endpoint:** `POST /conversation/api/offer`

Standard WebRTC mode for web browsers:
- Uses standard WebRTC SDP format
- Compatible with browsers (Chrome, Firefox, Safari, etc.)
- Full duplex audio communication
- Standard ICE candidate negotiation

#### ESP32 Mode
**Endpoint:** `POST /conversation/api/offer/esp32`

Optimized for ESP32 devices:
- Uses ESP32-specific SDP munging
- Optimized for embedded devices
- Lower bandwidth requirements
- Compatible with ESP32 WebRTC implementations
- Supports IoT session tokens

**When to use ESP32 endpoint:**
- Building ESP32-based storytelling devices
- Embedded audio applications
- IoT devices with voice interaction
- Resource-constrained devices

### Story Modes

### Free-Form Storytelling (No story_id)
When no `story_id` is provided:
- AI acts as a creative storyteller
- Can tell stories about any topic
- Interactive - asks child what they want to hear
- Uses child's name and age for personalization

**System Prompt:**
```
You are a creative storyteller for children. The child's name is [Name] and they are [Age] years old.

Your role is to create and tell engaging, age-appropriate stories for children...
```

### Story-Specific Mode (With story_id)
When `story_id` is provided:
- AI narrates ONLY the specified story
- Retrieves story from Firebase
- No deviation or improvisation
- Redirects off-topic questions back to the story

**System Prompt:**
```
You are an expert storyteller for children. The child's name is [Name]...

Your ONLY task is to narrate the following story...
[Story content loaded from Firebase]
```

## Testing

### Web Test Page
Open: http://localhost:8000/test-conversation

1. Enter your Firebase session token
2. (Optional) Enter a story ID
3. Click "Start Conversation"
4. Grant microphone permission
5. Start talking!

### JavaScript Client Example

```javascript
// Create WebRTC connection
const peerConnection = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
});

// Add microphone stream
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
stream.getTracks().forEach(track => {
    peerConnection.addTrack(track, stream);
});

// Handle incoming audio
peerConnection.ontrack = (event) => {
    const audio = new Audio();
    audio.srcObject = event.streams[0];
    audio.play();
};

// Create and send offer
const offer = await peerConnection.createOffer();
await peerConnection.setLocalDescription(offer);

const response = await fetch('http://localhost:8000/conversation/api/offer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        session_token: 'your_firebase_token',
        story_id: null, // or 'story_abc123'
        sdp: offer.sdp,
        type: offer.type,
        pc_id: Math.random().toString(36).substring(7),
        mode: 'web'  // Use 'web' for browsers, 'esp32' for ESP32 devices
    })
});

const answer = await response.json();
await peerConnection.setRemoteDescription(answer);
```

### ESP32 Client Example

```cpp
// ESP32 Arduino code
#include <WebRTC.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

WebRTC webrtc;

void setup() {
  Serial.begin(115200);
  
  // Connect to WiFi
  WiFi.begin("YOUR_SSID", "YOUR_PASSWORD");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  
  // Create WebRTC offer
  String sdpOffer = webrtc.createOffer();
  
  // Send to ESP32 endpoint
  HTTPClient http;
  http.begin("http://your-server:8000/conversation/api/offer/esp32");
  http.addHeader("Content-Type", "application/json");
  
  // Build JSON payload
  StaticJsonDocument<4096> doc;
  doc["session_token"] = "your_iot_session_token_or_firebase_token";
  doc["sdp"] = sdpOffer;
  doc["type"] = "offer";
  doc["pc_id"] = "esp32_" + String(random(10000, 99999));
  // Note: No need to specify "mode" - ESP32 endpoint always uses ESP32 mode
  
  String payload;
  serializeJson(doc, payload);
  
  int httpCode = http.POST(payload);
  
  if (httpCode == 200) {
    String response = http.getString();
    
    // Parse response
    StaticJsonDocument<4096> responseDoc;
    deserializeJson(responseDoc, response);
    String sdpAnswer = responseDoc["sdp"];
    
    // Set remote description
    webrtc.setRemoteDescription(sdpAnswer);
    
    Serial.println("WebRTC connection established!");
  } else {
    Serial.printf("HTTP Error: %d\n", httpCode);
  }
  
  http.end();
}

void loop() {
  // Handle WebRTC audio streaming
  webrtc.loop();
  delay(10);
}
```

**Important Notes for ESP32:**
- Use the `/api/offer/esp32` endpoint (not `/api/offer`)
- Use the `/api/offer/esp32` endpoint for ICE candidates too
- IoT session tokens are supported alongside Firebase tokens
- Audio is optimized for ESP32's limited bandwidth
        type: offer.type,
        pc_id: Math.random().toString(36).substring(7)
    })
});

const answer = await response.json();
await peerConnection.setRemoteDescription(answer);
```

## Architecture

### Services Used
1. **Deepgram STT**: Speech-to-text (voice input)
2. **OpenAI LLM**: Language understanding and story generation
3. **Cartesia TTS**: Text-to-speech (voice output)
4. **Pipecat**: Real-time pipeline orchestration
5. **SmallWebRTC**: WebRTC transport layer

### Pipeline Flow
```
User Speech → Deepgram STT → User Context → OpenAI LLM → 
Cartesia TTS → WebRTC Output → User Hears Response
```

### Authentication Flow
1. Client sends Firebase ID token in `session_token`
2. Server verifies token with Firebase
3. Extracts user ID and fetches profile (child name, age)
4. If `story_id` provided, fetches story from Firestore
5. Builds personalized system prompt
6. Starts WebRTC conversation session

## Error Handling

### 401 Unauthorized
```json
{
  "detail": "Authentication failed: Invalid token"
}
```
**Cause:** Invalid or expired Firebase token

### 404 Not Found
```json
{
  "detail": "Story not found: story_id does not exist"
}
```
**Cause:** Provided story_id doesn't exist or user doesn't have access

### 500 Internal Server Error
```json
{
  "detail": "WebRTC connection failed: ..."
}
```
**Cause:** WebRTC setup failure, network issues, or service unavailable

## Configuration

Required environment variables in `.env`:
```bash
DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key
OPENAI_API_KEY=your_openai_key
```

## Limitations
- 5-minute idle timeout per session
- One WebRTC connection per peer connection ID
- Requires microphone permission in browser
- HTTPS required for production (WebRTC constraint)

## Quick Reference

### Choosing the Right Endpoint

| Use Case | Endpoint | Authentication |
|----------|----------|----------------|
| Web browser client | `/api/offer` | Firebase ID token |
| ESP32 device | `/api/offer/esp32` | Firebase ID token or IoT session token |
| Mobile app (WebView) | `/api/offer` | Firebase ID token |
| Custom embedded device | `/api/offer/esp32` | IoT session token |

### ESP32 vs Web Mode Comparison

| Feature | Web Mode | ESP32 Mode |
|---------|----------|------------|
| **Endpoint** | `/api/offer` | `/api/offer/esp32` |
| **SDP Format** | Standard WebRTC | ESP32-optimized |
| **Audio Codec** | Opus (48kHz) | Opus (16kHz) |
| **Bandwidth** | High quality | Optimized for low bandwidth |
| **ICE Candidates** | Full negotiation | Simplified for ESP32 |
| **Authentication** | Firebase only | Firebase + IoT tokens |
| **Use Case** | Browsers, apps | Embedded devices |

### Example cURL Commands

**Web Mode:**
```bash
curl -X POST http://localhost:8000/conversation/api/offer \
  -H "Content-Type: application/json" \
  -d '{
    "session_token": "your_firebase_token",
    "sdp": "v=0\r\no=...",
    "type": "offer",
    "pc_id": "web_12345"
  }'
```

**ESP32 Mode:**
```bash
curl -X POST http://localhost:8000/conversation/api/offer/esp32 \
  -H "Content-Type: application/json" \
  -d '{
    "session_token": "your_iot_or_firebase_token",
    "sdp": "v=0\r\no=...",
    "type": "offer",
    "pc_id": "esp32_67890"
  }'
```

## Future Enhancements
- [ ] Multi-language support
- [ ] Voice customization (different storyteller voices)
- [ ] Session recording and playback
- [ ] Real-time emotion detection
- [ ] Story branching based on child's responses
