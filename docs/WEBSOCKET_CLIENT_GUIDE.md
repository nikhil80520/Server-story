# WebSocket Client Guide - Story Generation Updates

## Overview

The WebSocket endpoint provides real-time updates for story generation progress, allowing clients to receive instant notifications about story creation status without polling.

## Endpoint

```
wss://api.junekids.xyz/ws/stories/{firebase_token}
```

**Authentication**: Firebase ID token in the URL path

---

## Connection Flow

### 1. Establish Connection

```javascript
const firebaseToken = "eyJhbGciOiJSUzI1NiIs..."; // Get from Firebase Auth
const ws = new WebSocket(`wss://api.junekids.xyz/ws/stories/${firebaseToken}`);
```

### 2. Handle Connection Open

```javascript
ws.onopen = () => {
  console.log('WebSocket connected');
};
```

### 3. Listen for Messages

```javascript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
  
  // Handle different event types
  switch(message.event) {
    case 'connected':
      handleConnected(message);
      break;
    case 'story_progress':
      handleProgress(message);
      break;
    case 'story_completed':
      handleComplete(message);
      break;
    case 'story_failed':
      handleError(message);
      break;
    case 'heartbeat':
      // Server keep-alive ping
      break;
    case 'pong':
      handlePong(message);
      break;
    case 'subscribed':
      handleSubscribed(message);
      break;
    case 'unsubscribed':
      handleUnsubscribed(message);
      break;
  }
};
```

### 4. Handle Errors and Close

```javascript
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket closed');
};
```

---

## Server → Client Messages

### 1. Connection Established

**Sent**: Immediately after successful connection

```json
{
  "event": "connected",
  "user_id": "CnHUiHOSe0RGDPPev6fAeY4YfXj1",
  "message": "WebSocket connection established",
  "timestamp": "2025-11-20T07:59:45.695257"
}
```

**Fields**:
- `event`: Always `"connected"`
- `user_id`: Authenticated user's Firebase UID
- `message`: Confirmation message
- `timestamp`: ISO 8601 timestamp

---

### 2. Story Progress Update

**Sent**: During story generation at various stages

```json
{
  "event": "story_progress",
  "story_id": "story_abc123def456",
  "progress": 35,
  "message": "Generating images for scene 3 of 7...",
  "current_step": "generating_images",
  "scene_number": 3,
  "total_scenes": 7,
  "timestamp": "2025-11-20T08:00:15.123456"
}
```

**Fields**:
- `event`: Always `"story_progress"`
- `story_id`: Unique identifier for the story
- `progress`: Integer 0-100 representing completion percentage
- `message`: Human-readable status message
- `current_step`: Current generation phase (e.g., `"generating_text"`, `"generating_images"`, `"generating_audio"`)
- `scene_number`: Current scene being processed (optional)
- `total_scenes`: Total number of scenes (optional)
- `timestamp`: ISO 8601 timestamp

**Possible `current_step` values**:
- `"initializing"` - Setting up generation
- `"generating_text"` - Creating story narrative
- `"generating_images"` - Creating scene images
- `"generating_audio"` - Creating narration audio
- `"finalizing"` - Assembling final manifest

---

### 3. Story Completed

**Sent**: When story generation finishes successfully

```json
{
  "event": "story_completed",
  "story_id": "story_abc123def456",
  "title": "Emma's Magical Forest Adventure",
  "message": "Your story 'Emma's Magical Forest Adventure' is ready!",
  "manifest": {
    "story_id": "story_abc123def456",
    "title": "Emma's Magical Forest Adventure",
    "total_scenes": 7,
    "total_duration": 420,
    "scenes": [
      {
        "scene_number": 1,
        "text": "Once upon a time...",
        "image_url": "https://storage.googleapis.com/...",
        "audio_url": "https://storage.googleapis.com/...",
        "duration": 60
      }
    ],
    "generated_at": "2025-11-20T08:02:30.456789",
    "status": "completed"
  },
  "timestamp": "2025-11-20T08:02:30.789012"
}
```

**Fields**:
- `event`: Always `"story_completed"`
- `story_id`: Unique identifier for the story
- `title`: Generated story title
- `message`: Success message
- `manifest`: Complete story data object (same as GET /stories/{story_id} response)
- `timestamp`: ISO 8601 timestamp

**Action**: Client should fetch full story details or use the provided manifest

---

### 4. Story Failed

**Sent**: When story generation encounters an error

```json
{
  "event": "story_failed",
  "story_id": "story_abc123def456",
  "message": "Story generation failed: Image generation timeout",
  "error": "Image generation timeout after 3 retries",
  "error_code": "GENERATION_TIMEOUT",
  "timestamp": "2025-11-20T08:01:45.123456"
}
```

**Fields**:
- `event`: Always `"story_failed"`
- `story_id`: Unique identifier for the story
- `message`: User-friendly error message
- `error`: Detailed error description
- `error_code`: Machine-readable error code (optional)
- `timestamp`: ISO 8601 timestamp

**Possible `error_code` values**:
- `"GENERATION_TIMEOUT"` - Generation took too long
- `"AI_SERVICE_ERROR"` - AI service returned an error
- `"STORAGE_ERROR"` - Failed to save generated content
- `"VALIDATION_ERROR"` - Invalid input parameters
- `"QUOTA_EXCEEDED"` - User quota limits reached

**Action**: Client should display error and optionally retry

---

### 5. Heartbeat

**Sent**: Every 30 seconds to keep connection alive

```json
{
  "event": "heartbeat",
  "timestamp": "2025-11-20T08:00:30.123456"
}
```

**Fields**:
- `event`: Always `"heartbeat"`
- `timestamp`: ISO 8601 timestamp

**Action**: No action required; connection is still active

---

### 6. Pong Response

**Sent**: In response to client ping

```json
{
  "event": "pong",
  "timestamp": "2025-11-20T08:00:15.123456"
}
```

**Fields**:
- `event`: Always `"pong"`
- `timestamp`: ISO 8601 timestamp

---

### 7. Subscription Confirmed

**Sent**: After client subscribes to a story

```json
{
  "event": "subscribed",
  "story_id": "story_abc123def456",
  "message": "Subscribed to story story_abc123def456 updates",
  "timestamp": "2025-11-20T08:00:10.123456"
}
```

**Fields**:
- `event`: Always `"subscribed"`
- `story_id`: Story subscribed to
- `message`: Confirmation message
- `timestamp`: ISO 8601 timestamp

---

### 8. Unsubscription Confirmed

**Sent**: After client unsubscribes from a story

```json
{
  "event": "unsubscribed",
  "story_id": "story_abc123def456",
  "message": "Unsubscribed from story story_abc123def456 updates",
  "timestamp": "2025-11-20T08:00:20.123456"
}
```

**Fields**:
- `event`: Always `"unsubscribed"`
- `story_id`: Story unsubscribed from
- `message`: Confirmation message
- `timestamp`: ISO 8601 timestamp

---

### 9. Error Message

**Sent**: When client sends invalid message

```json
{
  "event": "error",
  "message": "story_id is required for subscribe action"
}
```

**Fields**:
- `event`: Always `"error"`
- `message`: Error description

---

## Client → Server Messages

### 1. Ping (Keep-Alive)

**Purpose**: Keep connection active and check server responsiveness

```json
{
  "action": "ping"
}
```

**Response**: Server sends `pong` message

**Example**:
```javascript
// Send ping every 20 seconds
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "ping" }));
  }
}, 20000);
```

---

### 2. Subscribe to Story

**Purpose**: Receive updates for a specific story

```json
{
  "action": "subscribe",
  "story_id": "story_abc123def456"
}
```

**Fields**:
- `action`: Must be `"subscribe"`
- `story_id`: Story ID to receive updates for

**Response**: Server sends `subscribed` confirmation

**Example**:
```javascript
ws.send(JSON.stringify({
  action: "subscribe",
  story_id: storyId
}));
```

**Note**: By default, you receive updates for all your stories. Subscribing is useful for filtering specific stories.

---

### 3. Unsubscribe from Story

**Purpose**: Stop receiving updates for a specific story

```json
{
  "action": "unsubscribe",
  "story_id": "story_abc123def456"
}
```

**Fields**:
- `action`: Must be `"unsubscribe"`
- `story_id`: Story ID to stop receiving updates for

**Response**: Server sends `unsubscribed` confirmation

**Example**:
```javascript
ws.send(JSON.stringify({
  action: "unsubscribe",
  story_id: storyId
}));
```

---

## Complete Integration Examples

### React Hook Example

```javascript
import { useEffect, useState, useRef } from 'react';

function useStoryWebSocket(firebaseToken) {
  const [status, setStatus] = useState('disconnected');
  const [messages, setMessages] = useState([]);
  const ws = useRef(null);

  useEffect(() => {
    if (!firebaseToken) return;

    // Connect
    ws.current = new WebSocket(`wss://api.junekids.xyz/ws/stories/${firebaseToken}`);
    
    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setStatus('connected');
    };
    
    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setMessages(prev => [...prev, message]);
      
      // Handle events
      if (message.event === 'story_completed') {
        // Story is ready!
        console.log('Story completed:', message.story_id);
      }
    };
    
    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setStatus('error');
    };
    
    ws.current.onclose = () => {
      console.log('WebSocket closed');
      setStatus('disconnected');
    };
    
    // Send ping every 20 seconds
    const pingInterval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ action: "ping" }));
      }
    }, 20000);
    
    // Cleanup
    return () => {
      clearInterval(pingInterval);
      ws.current?.close();
    };
  }, [firebaseToken]);

  const subscribe = (storyId) => {
    ws.current?.send(JSON.stringify({
      action: "subscribe",
      story_id: storyId
    }));
  };

  const unsubscribe = (storyId) => {
    ws.current?.send(JSON.stringify({
      action: "unsubscribe",
      story_id: storyId
    }));
  };

  return { status, messages, subscribe, unsubscribe };
}

// Usage in component
function StoryGenerator() {
  const [firebaseToken, setFirebaseToken] = useState(null);
  const { status, messages, subscribe } = useStoryWebSocket(firebaseToken);

  useEffect(() => {
    // Get Firebase token
    firebase.auth().currentUser?.getIdToken().then(setFirebaseToken);
  }, []);

  const generateStory = async () => {
    const response = await fetch('https://api.junekids.xyz/stories/generate', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${firebaseToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        firebase_token: firebaseToken,
        user_prompt: "A magical adventure",
        child_name: "Emma",
        child_age: 7
      })
    });
    
    const data = await response.json();
    // Subscribe to story updates
    subscribe(data.story_id);
  };

  return (
    <div>
      <p>WebSocket Status: {status}</p>
      <button onClick={generateStory}>Generate Story</button>
      
      {messages.map((msg, i) => (
        <div key={i}>
          {msg.event === 'story_progress' && (
            <div>Progress: {msg.progress}% - {msg.message}</div>
          )}
          {msg.event === 'story_completed' && (
            <div>✅ Story ready: {msg.title}</div>
          )}
          {msg.event === 'story_failed' && (
            <div>❌ Error: {msg.message}</div>
          )}
        </div>
      ))}
    </div>
  );
}
```

---

### Vanilla JavaScript Example

```javascript
class StoryWebSocketClient {
  constructor(firebaseToken) {
    this.token = firebaseToken;
    this.ws = null;
    this.pingInterval = null;
    this.handlers = {};
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(`wss://api.junekids.xyz/ws/stories/${this.token}`);
      
      this.ws.onopen = () => {
        console.log('Connected to story updates');
        this.startPing();
        resolve();
      };
      
      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket closed');
        this.stopPing();
      };
    });
  }

  handleMessage(message) {
    const handler = this.handlers[message.event];
    if (handler) {
      handler(message);
    }
  }

  on(event, handler) {
    this.handlers[event] = handler;
  }

  subscribe(storyId) {
    this.send({ action: "subscribe", story_id: storyId });
  }

  unsubscribe(storyId) {
    this.send({ action: "unsubscribe", story_id: storyId });
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  startPing() {
    this.pingInterval = setInterval(() => {
      this.send({ action: "ping" });
    }, 20000);
  }

  stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  close() {
    this.stopPing();
    this.ws?.close();
  }
}

// Usage
const client = new StoryWebSocketClient(firebaseToken);

// Set up event handlers
client.on('connected', (msg) => {
  console.log('Connected as user:', msg.user_id);
});

client.on('story_progress', (msg) => {
  updateProgressBar(msg.progress);
  showStatusMessage(msg.message);
});

client.on('story_completed', (msg) => {
  showSuccessNotification(`Story "${msg.title}" is ready!`);
  loadStory(msg.story_id);
});

client.on('story_failed', (msg) => {
  showErrorNotification(msg.message);
});

// Connect
await client.connect();

// Generate story and subscribe
const response = await generateStory(params);
client.subscribe(response.story_id);
```

---

### Python Example

```python
import asyncio
import websockets
import json

async def story_websocket_client(firebase_token):
    uri = f"wss://api.junekids.xyz/ws/stories/{firebase_token}"
    
    async with websockets.connect(uri, ping_interval=30) as websocket:
        print("Connected to story updates")
        
        # Send ping periodically
        async def send_ping():
            while True:
                await asyncio.sleep(20)
                await websocket.send(json.dumps({"action": "ping"}))
        
        # Start ping task
        ping_task = asyncio.create_task(send_ping())
        
        try:
            # Listen for messages
            async for message in websocket:
                data = json.loads(message)
                event = data.get("event")
                
                if event == "connected":
                    print(f"Connected as user: {data['user_id']}")
                
                elif event == "story_progress":
                    print(f"Progress: {data['progress']}% - {data['message']}")
                
                elif event == "story_completed":
                    print(f"Story completed: {data['title']}")
                    print(f"Story ID: {data['story_id']}")
                    break
                
                elif event == "story_failed":
                    print(f"Story failed: {data['message']}")
                    break
                
                elif event == "heartbeat":
                    pass  # Server keep-alive
                
                elif event == "pong":
                    pass  # Response to our ping
        
        finally:
            ping_task.cancel()

# Usage
firebase_token = "your_firebase_token_here"
asyncio.run(story_websocket_client(firebase_token))
```

---

### Swift/iOS Example

```swift
import Foundation

class StoryWebSocketClient: NSObject {
    private var webSocketTask: URLSessionWebSocketTask?
    private var pingTimer: Timer?
    
    func connect(firebaseToken: String) {
        let url = URL(string: "wss://api.junekids.xyz/ws/stories/\(firebaseToken)")!
        webSocketTask = URLSession.shared.webSocketTask(with: url)
        webSocketTask?.resume()
        
        receiveMessage()
        startPing()
    }
    
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self?.handleMessage(text)
                default:
                    break
                }
                self?.receiveMessage() // Continue listening
                
            case .failure(let error):
                print("WebSocket error: \(error)")
            }
        }
    }
    
    private func handleMessage(_ text: String) {
        guard let data = text.data(using: .utf8),
              let json = try? JSONDecoder().decode([String: Any].self, from: data),
              let event = json["event"] as? String else {
            return
        }
        
        switch event {
        case "connected":
            print("Connected as user: \(json["user_id"] ?? "")")
            
        case "story_progress":
            let progress = json["progress"] as? Int ?? 0
            let message = json["message"] as? String ?? ""
            onProgress(progress: progress, message: message)
            
        case "story_completed":
            let storyId = json["story_id"] as? String ?? ""
            let title = json["title"] as? String ?? ""
            onComplete(storyId: storyId, title: title)
            
        case "story_failed":
            let message = json["message"] as? String ?? ""
            onError(message: message)
            
        default:
            break
        }
    }
    
    func subscribe(storyId: String) {
        let message = ["action": "subscribe", "story_id": storyId]
        send(message)
    }
    
    func unsubscribe(storyId: String) {
        let message = ["action": "unsubscribe", "story_id": storyId]
        send(message)
    }
    
    private func send(_ message: [String: String]) {
        guard let data = try? JSONSerialization.data(withJSONObject: message),
              let text = String(data: data, encoding: .utf8) else {
            return
        }
        
        webSocketTask?.send(.string(text)) { error in
            if let error = error {
                print("Send error: \(error)")
            }
        }
    }
    
    private func startPing() {
        pingTimer = Timer.scheduledTimer(withTimeInterval: 20, repeats: true) { [weak self] _ in
            self?.send(["action": "ping"])
        }
    }
    
    func disconnect() {
        pingTimer?.invalidate()
        webSocketTask?.cancel(with: .goingAway, reason: nil)
    }
    
    // Callbacks - override or set as closures
    var onProgress: (Int, String) -> Void = { _, _ in }
    var onComplete: (String, String) -> Void = { _, _ in }
    var onError: (String) -> Void = { _ in }
}
```

---

## Best Practices

### 1. Connection Management

- **Always close connections** when done to free server resources
- **Implement reconnection logic** for network interruptions
- **Send periodic pings** (every 20-30 seconds) to keep connection alive
- **Handle heartbeat messages** from server (every 30 seconds)

### 2. Error Handling

- **Check `readyState`** before sending messages
- **Implement exponential backoff** for reconnection attempts
- **Display user-friendly error messages** from `story_failed` events
- **Log errors** for debugging

### 3. Performance

- **Subscribe to specific stories** if tracking multiple generations
- **Unsubscribe when done** to reduce unnecessary messages
- **Buffer progress updates** to avoid UI thrashing
- **Close connections** when navigating away

### 4. Security

- **Never share Firebase tokens** in logs or error messages
- **Use secure WSS protocol** (not WS)
- **Refresh expired tokens** and reconnect
- **Validate message structure** before processing

---

## Troubleshooting

### Connection Fails

**Problem**: WebSocket connection fails immediately

**Solutions**:
- Verify Firebase token is valid and not expired
- Check domain name is correct (`api.junekids.xyz`)
- Ensure using `wss://` (secure WebSocket)
- Check network/firewall settings

### No Messages Received

**Problem**: Connected but no story updates

**Solutions**:
- Verify story generation was started successfully
- Check story_id matches the generation request
- Ensure WebSocket stays connected (check for close events)
- Try subscribing explicitly to the story_id

### Connection Drops

**Problem**: WebSocket disconnects unexpectedly

**Solutions**:
- Implement ping/pong keep-alive (every 20 seconds)
- Handle heartbeat messages from server
- Add reconnection logic with exponential backoff
- Check for network stability issues

### Token Expired

**Problem**: Connection rejected with 401 error

**Solutions**:
- Refresh Firebase token using `getIdToken(true)`
- Implement token refresh before expiration
- Reconnect with new token

---

## Rate Limits

- **Concurrent connections**: 5 per user
- **Message rate**: No limit on receiving
- **Ping rate**: Recommended every 20-30 seconds
- **Connection duration**: No limit (will auto-close if idle for 30+ minutes)

---

## Support

For issues or questions:
- Check server logs for connection errors
- Verify Firebase authentication is working
- Test with the provided examples
- Contact support with connection logs

---

## Version History

- **v1.0** (2025-11-20): Initial WebSocket implementation
  - Real-time story progress updates
  - Story completion notifications
  - Error handling and heartbeat support
  - Subscribe/unsubscribe to specific stories
