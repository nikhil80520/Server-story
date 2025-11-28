# Conversational AI API Documentation

## Overview
Real-time conversational AI storytelling endpoint using WebRTC for voice interaction. The AI can tell stories interactively with voice input/output.

## Base URL
```
http://localhost:8000
```

## Authentication
All conversation endpoints require Firebase authentication via ID token in the Authorization header.

## Endpoints

### 1. Create/Update Conversation Session
**POST** `/conversation/api/offer`

Creates a new WebRTC conversation session or updates an existing one.

#### Headers
```
Authorization: Bearer <firebase_id_token>
Content-Type: application/json
```

#### Request Body
```json
{
  "sdp": "v=0\r\no=- ... (WebRTC SDP offer)",
  "story_id": "optional-story-id-to-tell-specific-story"
}
```

#### Parameters
- `sdp` (required): WebRTC SDP offer string from client
- `story_id` (optional): If provided, AI will tell this specific story from Firebase. If not provided, AI will create a new interactive story.

#### Response (200 OK)
```json
{
  "sdp": "v=0\r\na=... (WebRTC SDP answer)",
  "session_id": "unique-session-id",
  "user_id": "firebase-user-id",
  "story_mode": "specific_story",  // or "interactive"
  "story_title": "The Adventures of...",  // if story_id provided
  "message": "WebRTC session established"
}
```

#### Response (400 Bad Request)
```json
{
  "detail": "SDP offer is required"
}
```

#### Response (401 Unauthorized)
```json
{
  "detail": "Invalid or expired token"
}
```

#### Response (404 Not Found)
```json
{
  "detail": "Story not found"
}
```

---

### 2. Update Existing Session
**PATCH** `/conversation/api/offer`

Updates an existing WebRTC session (for ICE candidates, etc.)

#### Headers
```
Authorization: Bearer <firebase_id_token>
Content-Type: application/json
```

#### Request Body
```json
{
  "sdp": "v=0\r\no=- ... (updated SDP)",
  "session_id": "existing-session-id"
}
```

#### Response (200 OK)
```json
{
  "sdp": "v=0\r\na=... (updated SDP answer)",
  "session_id": "session-id",
  "message": "Session updated"
}
```

---

### 3. Health Check
**GET** `/conversation/health`

Check if the conversation service is running.

#### Response (200 OK)
```json
{
  "status": "healthy",
  "service": "conversational_ai",
  "active_sessions": 5,
  "timestamp": "2025-11-01T18:00:00Z"
}
```

---

## How It Works

### Without Story ID (Interactive Mode)
```mermaid
sequenceDiagram
    Client->>API: POST /conversation/api/offer (no story_id)
    API->>Firebase: Verify user token
    API->>OpenAI: Create conversation with "tell me a story" prompt
    API->>Client: Return WebRTC SDP answer
    Client<-->API: WebRTC voice connection established
    User->>Client: "Tell me a story about dragons"
    Client->>API: Voice data via WebRTC
    API->>OpenAI: Process voice, generate story
    API->>Deepgram: Speech-to-text
    OpenAI->>API: Story response
    API->>Cartesia: Text-to-speech
    API->>Client: Voice response via WebRTC
```

### With Story ID (Specific Story Mode)
```mermaid
sequenceDiagram
    Client->>API: POST /conversation/api/offer (story_id provided)
    API->>Firebase: Verify user token
    API->>Firebase: Fetch story by story_id
    API->>OpenAI: Create conversation with story context
    Note over API,OpenAI: System prompt: "Tell ONLY this story..."
    API->>Client: Return WebRTC SDP answer
    Client<-->API: WebRTC voice connection established
    User->>Client: "Start the story"
    Client->>API: Voice data via WebRTC
    API->>OpenAI: Process with story context
    OpenAI->>API: Story narration
    API->>Cartesia: Text-to-speech
    API->>Client: Voice response via WebRTC
```

---

## System Prompts

### Interactive Mode (No Story ID)
```
You are a friendly AI storyteller. Create engaging, interactive stories for children.
Ask questions and respond to the child's input to make the story personalized and fun.
```

### Specific Story Mode (With Story ID)
```
You are narrating a specific story. Tell ONLY the story provided below.
Do not deviate from the story content. Narrate it engagingly but stay true to the story.

Story Title: [title]
Story Summary: [summary from Firebase]

Full Story: [scenes and content]
```

---

## Testing

### Test Page
Open the test client in your browser:
```
http://localhost:8000/test-conversation
```

The test page allows you to:
1. Enter your Firebase ID token
2. Optionally enter a story ID
3. Connect via WebRTC
4. Talk to the AI using your microphone
5. Hear AI responses through your speakers

### Manual Testing with cURL

#### 1. Get Firebase ID Token
```bash
# From your React Native app or Firebase Auth
FIREBASE_TOKEN="your-firebase-id-token-here"
```

#### 2. Test Without Story (Interactive)
```bash
curl -X POST http://localhost:8000/conversation/api/offer \
  -H "Authorization: Bearer $FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sdp": "v=0\r\no=- 123456 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n..."
  }'
```

#### 3. Test With Specific Story
```bash
STORY_ID="your-story-id-from-firebase"

curl -X POST http://localhost:8000/conversation/api/offer \
  -H "Authorization: Bearer $FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"sdp\": \"v=0\\r\\no=- 123456 2 IN IP4 127.0.0.1\\r\\ns=-\\r\\nt=0 0\\r\\n...\",
    \"story_id\": \"$STORY_ID\"
  }"
```

#### 4. Health Check
```bash
curl http://localhost:8000/conversation/health
```

---

## Client Integration

### React Native Example
```javascript
import { RTCPeerConnection, RTCSessionDescription } from 'react-native-webrtc';
import auth from '@react-native-firebase/auth';

async function startConversation(storyId = null) {
  // Get Firebase token
  const token = await auth().currentUser.getIdToken();
  
  // Create WebRTC peer connection
  const pc = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
  });
  
  // Add audio track
  const stream = await getUserMedia({ audio: true });
  stream.getTracks().forEach(track => pc.addTrack(track, stream));
  
  // Create offer
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  
  // Send to server
  const response = await fetch('http://localhost:8000/conversation/api/offer', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      sdp: offer.sdp,
      story_id: storyId  // Optional
    })
  });
  
  const { sdp } = await response.json();
  
  // Set remote description
  await pc.setRemoteDescription(new RTCSessionDescription({
    type: 'answer',
    sdp: sdp
  }));
  
  // Listen for remote audio
  pc.ontrack = (event) => {
    const remoteStream = event.streams[0];
    // Play remote audio stream
  };
}

// Interactive storytelling
startConversation();

// Tell specific story
startConversation('story-id-123');
```

### Swift Example
```swift
import WebRTC
import FirebaseAuth

func startConversation(storyId: String? = nil) async throws {
    // Get Firebase token
    guard let token = try? await Auth.auth().currentUser?.getIDToken() else {
        throw ConversationError.notAuthenticated
    }
    
    // Create peer connection
    let config = RTCConfiguration()
    config.iceServers = [RTCIceServer(urlStrings: ["stun:stun.l.google.com:19302"])]
    let pc = peerConnectionFactory.peerConnection(with: config, constraints: constraints, delegate: self)
    
    // Add audio track
    let audioTrack = createAudioTrack()
    pc.add(audioTrack, streamIds: ["local"])
    
    // Create offer
    pc.offer(for: constraints) { sdp, error in
        guard let sdp = sdp else { return }
        pc.setLocalDescription(sdp) { error in }
        
        // Send to server
        var request = URLRequest(url: URL(string: "http://localhost:8000/conversation/api/offer")!)
        request.httpMethod = "POST"
        request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "sdp": sdp.sdp,
            "story_id": storyId as Any
        ]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let remoteSdp = json["sdp"] as? String else { return }
            
            let answer = RTCSessionDescription(type: .answer, sdp: remoteSdp)
            pc.setRemoteDescription(answer) { error in }
        }.resume()
    }
}

// Interactive mode
Task { try await startConversation() }

// Specific story mode
Task { try await startConversation(storyId: "story-123") }
```

---

## API Configuration

### Required API Keys in .env
```bash
OPENAI_API_KEY=sk-...           # For LLM conversation
DEEPGRAM_API_KEY=...            # For speech-to-text
CARTESIA_API_KEY=...            # For text-to-speech
FIREBASE_STORAGE_BUCKET=...     # For story data
```

### Voice Configuration
The conversation uses:
- **Speech-to-Text**: Deepgram (real-time streaming)
- **LLM**: OpenAI GPT-4 (conversation)
- **Text-to-Speech**: Cartesia (low-latency voice)

---

## Error Handling

### Common Errors

#### 401 Unauthorized
```json
{
  "detail": "Invalid or expired token"
}
```
**Solution**: Get a fresh Firebase ID token

#### 404 Not Found
```json
{
  "detail": "Story not found: story-id-123"
}
```
**Solution**: Verify story_id exists in Firebase

#### 400 Bad Request
```json
{
  "detail": "SDP offer is required"
}
```
**Solution**: Include valid WebRTC SDP in request body

#### 500 Internal Server Error
```json
{
  "detail": "Failed to create conversation session"
}
```
**Solution**: Check server logs, verify API keys are configured

---

## Performance

- **Latency**: ~200-500ms for voice response
- **Concurrent Sessions**: Supports multiple simultaneous conversations
- **WebRTC**: Direct peer-to-peer connection for low latency
- **Story Loading**: Cached from Firebase for fast access

---

## Security

✅ **Firebase Authentication Required**: All endpoints require valid Firebase ID token  
✅ **User Isolation**: Users can only access their own stories  
✅ **Story Verification**: Story ownership verified before narration  
✅ **WebRTC Encryption**: Audio streams encrypted via DTLS-SRTP  

---

## Monitoring

### Active Sessions
```bash
curl http://localhost:8000/conversation/health
```

### Server Logs
Watch for conversation events:
```bash
tail -f server.log | grep "conversation"
```

Log entries:
- `🎙️ New conversation session created`
- `📖 Loading story for conversation`
- `🔊 Conversation session active`
- `✅ Story loaded successfully`

---

## Troubleshooting

### No Audio Response
1. Check microphone permissions
2. Verify WebRTC connection established
3. Check browser console for errors
4. Ensure Cartesia API key is valid

### Story Not Loading
1. Verify story exists in Firebase
2. Check story ownership matches user
3. Ensure Firebase credentials are valid
4. Check story has required fields (title, summary, scenes)

### Connection Timeout
1. Check network connectivity
2. Verify STUN server accessible
3. Try different network (firewall may block WebRTC)
4. Check server logs for errors

---

## Rate Limiting

- **Per User**: 10 concurrent sessions max
- **Story Loading**: No limit (cached)
- **Voice Processing**: Based on API provider limits

---

## Coming Soon

🚧 **Features in Development**:
- Voice cloning for personalized narration
- Multi-language support
- Story interruption and navigation
- Emotion detection in voice
- Background music integration

---

## Support

For issues or questions:
- Check server logs: `/var/log/storyteller/`
- API documentation: `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/conversation/health`
