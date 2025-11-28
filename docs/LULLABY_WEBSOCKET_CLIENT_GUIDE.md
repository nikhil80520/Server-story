# Lullaby WebSocket Integration Guide

## Overview

The lullaby generation system uses **asynchronous processing** with **WebSocket notifications** to provide a non-blocking, real-time experience. When a client requests lullaby generation:

1. **API returns immediately** (HTTP 202 Accepted) with `lullaby_id` and WebSocket endpoint
2. **Generation happens in background** (2-4 minutes)
3. **Progress updates sent via WebSocket** (0% → 25% → 75% → 90% → 100%)
4. **Completion notification** includes final audio URL

## API Flow

### 1. Start Generation (HTTP POST)

```http
POST /lullabies/generate
Authorization: Bearer <firebase_token>
Content-Type: application/json

{
  "description": "A gentle lullaby about stars and moon",
  "child_id": "child_abc123"  // Optional - for personalization
}
```

**Response (HTTP 202 Accepted):**

```json
{
  "lullaby": {
    "lullaby_id": "lullaby_89f51c3e8130",
    "user_id": "eTU0u0xTfrbcIk7k9THk77RgUrI2",
    "child_id": "child_abc123",
    "child_name": null,
    "description": "A gentle lullaby about stars and moon",
    "lyrics": "",
    "audio_url": "",
    "status": "processing",
    "created_at": "2024-11-27T18:48:46Z"
  },
  "message": "Lullaby generation started! Connect via WebSocket for real-time updates.",
  "websocket_endpoint": "/ws/lullabies"
}
```

### 2. Connect to WebSocket

```javascript
// Get Firebase auth token
const token = await firebase.auth().currentUser.getIdToken();

// Connect to WebSocket
const ws = new WebSocket(`wss://your-api.com/ws/lullabies/${token}`);
```

## WebSocket Events

### Client → Server Messages

```javascript
// Subscribe to specific lullaby (optional)
ws.send(JSON.stringify({
  action: 'subscribe',
  lullaby_id: 'lullaby_89f51c3e8130'
}));

// Unsubscribe from lullaby
ws.send(JSON.stringify({
  action: 'unsubscribe',
  lullaby_id: 'lullaby_89f51c3e8130'
}));

// Request heartbeat
ws.send(JSON.stringify({
  action: 'ping'
}));
```

### Server → Client Events

#### 1. Connection Established

```json
{
  "event": "connected",
  "message": "Connected to lullaby notifications",
  "timestamp": "2024-11-27T18:48:46.123Z"
}
```

#### 2. Subscribed to Lullaby

```json
{
  "event": "subscribed",
  "lullaby_id": "lullaby_89f51c3e8130",
  "message": "Subscribed to lullaby updates",
  "timestamp": "2024-11-27T18:48:46.456Z"
}
```

#### 3. Progress Updates

**Starting (0% - 10%)**
```json
{
  "event": "lullaby_progress",
  "lullaby_id": "lullaby_89f51c3e8130",
  "status": "starting",
  "progress": 0,
  "message": "Initializing lullaby generation...",
  "timestamp": "2024-11-27T18:48:46.789Z"
}
```

**Generating Lyrics (10% - 25%)**
```json
{
  "event": "lullaby_progress",
  "lullaby_id": "lullaby_89f51c3e8130",
  "status": "generating_lyrics",
  "progress": 10,
  "message": "Generating personalized lyrics...",
  "timestamp": "2024-11-27T18:48:47.000Z"
}
```

**Lyrics Complete (25%)**
```json
{
  "event": "lullaby_progress",
  "lullaby_id": "lullaby_89f51c3e8130",
  "status": "lyrics_complete",
  "progress": 25,
  "message": "Lyrics generated! Creating music...",
  "lyrics": "Twinkle, twinkle, little star...\n[Full lyrics here]",
  "timestamp": "2024-11-27T18:48:48.000Z"
}
```

**Music Complete (75%)**
```json
{
  "event": "lullaby_progress",
  "lullaby_id": "lullaby_89f51c3e8130",
  "status": "music_complete",
  "progress": 75,
  "message": "Music generated! Uploading to storage...",
  "timestamp": "2024-11-27T18:50:31.000Z"
}
```

**Upload Complete (90%)**
```json
{
  "event": "lullaby_progress",
  "lullaby_id": "lullaby_89f51c3e8130",
  "status": "upload_complete",
  "progress": 90,
  "message": "Upload complete! Saving metadata...",
  "timestamp": "2024-11-27T18:50:32.000Z"
}
```

#### 4. Generation Complete

```json
{
  "event": "lullaby_completed",
  "lullaby_id": "lullaby_89f51c3e8130",
  "message": "Your lullaby is ready!",
  "lullaby": {
    "lullaby_id": "lullaby_89f51c3e8130",
    "user_id": "eTU0u0xTfrbcIk7k9THk77RgUrI2",
    "child_id": "child_abc123",
    "child_name": "Emma",
    "description": "A gentle lullaby about stars and moon",
    "lyrics": "Twinkle, twinkle, little star...",
    "audio_url": "https://storage.googleapis.com/storyteller-7ece7.firebasestorage.app/lullabies/eTU0u0xTfrbcIk7k9THk77RgUrI2/lullaby_89f51c3e8130.mp3",
    "duration_seconds": null,
    "created_at": "2024-11-27T18:48:46Z"
  },
  "timestamp": "2024-11-27T18:50:33.000Z"
}
```

#### 5. Generation Failed

```json
{
  "event": "lullaby_failed",
  "lullaby_id": "lullaby_89f51c3e8130",
  "error": "Music generation timeout",
  "message": "Generation failed: Music generation timeout",
  "timestamp": "2024-11-27T18:50:33.000Z"
}
```

#### 6. Heartbeat (Keep-Alive)

```json
{
  "event": "heartbeat",
  "timestamp": "2024-11-27T18:50:00.000Z"
}
```

## Complete Client Implementation

### JavaScript/TypeScript Example

```typescript
import { initializeApp } from 'firebase/app';
import { getAuth, onAuthStateChanged } from 'firebase/auth';

class LullabyClient {
  private ws: WebSocket | null = null;
  private wsUrl: string;
  private apiUrl: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(apiUrl: string) {
    this.apiUrl = apiUrl;
    this.wsUrl = apiUrl.replace('https://', 'wss://').replace('http://', 'ws://');
  }

  /**
   * Start lullaby generation
   */
  async generateLullaby(description: string, childId?: string): Promise<LullabyResponse> {
    const token = await this.getFirebaseToken();
    
    const response = await fetch(`${this.apiUrl}/lullabies/generate`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ description, child_id: childId })
    });

    if (response.status !== 202) {
      throw new Error(`Generation failed: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Connect to WebSocket for real-time updates
   */
  async connectWebSocket(
    onProgress: (data: ProgressEvent) => void,
    onComplete: (data: CompleteEvent) => void,
    onError: (error: string) => void
  ): Promise<void> {
    const token = await this.getFirebaseToken();
    
    this.ws = new WebSocket(`${this.wsUrl}/ws/lullabies/${token}`);

    this.ws.onopen = () => {
      console.log('✅ WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('📨 WebSocket event:', data.event);

      switch (data.event) {
        case 'lullaby_progress':
          onProgress(data);
          break;
        
        case 'lullaby_completed':
          onComplete(data);
          this.ws?.close();
          break;
        
        case 'lullaby_failed':
          onError(data.message);
          this.ws?.close();
          break;
        
        case 'heartbeat':
          // Connection alive
          break;
      }
    };

    this.ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      onError('WebSocket connection error');
    };

    this.ws.onclose = () => {
      console.log('🔌 WebSocket closed');
      this.attemptReconnect(onProgress, onComplete, onError);
    };
  }

  /**
   * Subscribe to specific lullaby updates
   */
  subscribeToLullaby(lullabyId: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'subscribe',
        lullaby_id: lullabyId
      }));
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnect(): void {
    this.ws?.close();
    this.ws = null;
  }

  private async getFirebaseToken(): Promise<string> {
    const auth = getAuth();
    const user = auth.currentUser;
    if (!user) throw new Error('User not authenticated');
    return await user.getIdToken();
  }

  private attemptReconnect(
    onProgress: (data: ProgressEvent) => void,
    onComplete: (data: CompleteEvent) => void,
    onError: (error: string) => void
  ): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
      
      setTimeout(() => {
        this.connectWebSocket(onProgress, onComplete, onError);
      }, delay);
    }
  }
}

// Type definitions
interface LullabyResponse {
  lullaby: {
    lullaby_id: string;
    user_id: string;
    status: string;
    // ... other fields
  };
  message: string;
  websocket_endpoint: string;
}

interface ProgressEvent {
  event: 'lullaby_progress';
  lullaby_id: string;
  status: string;
  progress: number;
  message: string;
  lyrics?: string;
}

interface CompleteEvent {
  event: 'lullaby_completed';
  lullaby_id: string;
  lullaby: any;
  message: string;
}

// Usage example
async function generateAndPlayLullaby() {
  const client = new LullabyClient('https://your-api.com');
  
  // Show loading UI
  showLoadingScreen();
  
  try {
    // Start generation
    const response = await client.generateLullaby(
      'A gentle lullaby about the ocean',
      'child_abc123'
    );
    
    console.log('Generation started:', response.lullaby.lullaby_id);
    
    // Connect to WebSocket for updates
    await client.connectWebSocket(
      // Progress handler
      (data) => {
        updateProgressBar(data.progress);
        updateStatusMessage(data.message);
        
        if (data.lyrics) {
          displayLyrics(data.lyrics);
        }
      },
      
      // Completion handler
      (data) => {
        hideLoadingScreen();
        playAudio(data.lullaby.audio_url);
        showSuccessMessage('Your lullaby is ready!');
      },
      
      // Error handler
      (error) => {
        hideLoadingScreen();
        showErrorMessage(error);
      }
    );
    
    // Subscribe to this specific lullaby
    client.subscribeToLullaby(response.lullaby.lullaby_id);
    
  } catch (error) {
    hideLoadingScreen();
    showErrorMessage(error.message);
  }
}
```

### React Hook Example

```typescript
import { useState, useEffect, useCallback, useRef } from 'react';

interface UseLullabyGenerationReturn {
  generateLullaby: (description: string, childId?: string) => Promise<void>;
  progress: number;
  status: string;
  message: string;
  lyrics: string | null;
  audioUrl: string | null;
  isGenerating: boolean;
  error: string | null;
}

export function useLullabyGeneration(): UseLullabyGenerationReturn {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('');
  const [message, setMessage] = useState('');
  const [lyrics, setLyrics] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const clientRef = useRef<LullabyClient | null>(null);

  useEffect(() => {
    clientRef.current = new LullabyClient('https://your-api.com');
    
    return () => {
      clientRef.current?.disconnect();
    };
  }, []);

  const generateLullaby = useCallback(async (description: string, childId?: string) => {
    if (!clientRef.current) return;
    
    setIsGenerating(true);
    setError(null);
    setProgress(0);
    setLyrics(null);
    setAudioUrl(null);

    try {
      // Start generation
      const response = await clientRef.current.generateLullaby(description, childId);
      
      // Connect to WebSocket
      await clientRef.current.connectWebSocket(
        // Progress
        (data) => {
          setProgress(data.progress);
          setStatus(data.status);
          setMessage(data.message);
          if (data.lyrics) setLyrics(data.lyrics);
        },
        // Complete
        (data) => {
          setProgress(100);
          setStatus('completed');
          setMessage('Your lullaby is ready!');
          setAudioUrl(data.lullaby.audio_url);
          setIsGenerating(false);
        },
        // Error
        (errorMsg) => {
          setError(errorMsg);
          setIsGenerating(false);
        }
      );
      
      // Subscribe to updates
      clientRef.current.subscribeToLullaby(response.lullaby.lullaby_id);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed');
      setIsGenerating(false);
    }
  }, []);

  return {
    generateLullaby,
    progress,
    status,
    message,
    lyrics,
    audioUrl,
    isGenerating,
    error
  };
}

// Usage in component
function LullabyGenerator() {
  const {
    generateLullaby,
    progress,
    message,
    lyrics,
    audioUrl,
    isGenerating,
    error
  } = useLullabyGeneration();

  return (
    <div>
      <button 
        onClick={() => generateLullaby('A soothing lullaby about clouds')}
        disabled={isGenerating}
      >
        Generate Lullaby
      </button>

      {isGenerating && (
        <div>
          <ProgressBar value={progress} />
          <p>{message}</p>
          {lyrics && <pre>{lyrics}</pre>}
        </div>
      )}

      {audioUrl && (
        <audio controls src={audioUrl} autoPlay />
      )}

      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
}
```

## Progress Stages

| Progress | Status | Duration | Description |
|----------|--------|----------|-------------|
| 0-10% | `starting` | < 1s | Initialization and validation |
| 10-25% | `generating_lyrics` | 10-30s | OpenAI generates personalized lyrics |
| 25-75% | `music_complete` | 60-180s | MiniMax generates music from lyrics |
| 75-90% | `upload_complete` | 5-10s | Upload audio to Firebase Storage |
| 90-100% | Saving | 1-2s | Save metadata to Firestore |
| 100% | `completed` | - | Ready to play! |

## Error Handling

### Common Errors

1. **Authentication Failed** (401)
   - Token expired or invalid
   - Solution: Refresh Firebase token and reconnect

2. **Generation Timeout**
   - Music generation took too long (> 5 minutes)
   - Solution: Retry generation

3. **WebSocket Disconnect**
   - Network interruption
   - Solution: Implement exponential backoff reconnection

4. **Child Profile Not Found** (404)
   - Invalid child_id provided
   - Solution: Validate child_id before generation

## Best Practices

1. **Connect WebSocket Before Generation**
   ```javascript
   // Connect first
   await client.connectWebSocket(...);
   
   // Then generate
   const response = await client.generateLullaby(...);
   client.subscribeToLullaby(response.lullaby.lullaby_id);
   ```

2. **Handle Reconnections**
   - Implement exponential backoff
   - Max 5 reconnection attempts
   - Reconnect delays: 1s, 2s, 4s, 8s, 16s

3. **Show Progress to User**
   - Display progress bar (0-100%)
   - Show current status message
   - Preview lyrics when available (25% mark)

4. **Cleanup on Unmount**
   ```javascript
   useEffect(() => {
     return () => {
       client.disconnect();
     };
   }, []);
   ```

5. **Cache Audio URLs**
   - Store audio_url for offline playback
   - Implement retry logic for failed downloads

## Testing

### Manual Testing with wscat

```bash
# Install wscat
npm install -g wscat

# Get Firebase token
TOKEN="your_firebase_token_here"

# Connect to WebSocket
wscat -c "wss://your-api.com/ws/lullabies/$TOKEN"

# Subscribe to lullaby
> {"action": "subscribe", "lullaby_id": "lullaby_89f51c3e8130"}

# You'll receive events in real-time
< {"event": "subscribed", "lullaby_id": "lullaby_89f51c3e8130"}
< {"event": "lullaby_progress", "progress": 25, "message": "Lyrics generated!"}
< {"event": "lullaby_completed", "lullaby": {...}}
```

## Troubleshooting

### WebSocket Not Connecting

1. Check Firebase token is valid:
   ```javascript
   const token = await firebase.auth().currentUser.getIdToken(true); // Force refresh
   ```

2. Verify WebSocket URL format:
   ```javascript
   const url = `wss://your-api.com/ws/lullabies/${token}`;
   ```

3. Check CORS and firewall rules

### No Progress Updates Received

1. Verify subscription:
   ```javascript
   ws.send(JSON.stringify({
     action: 'subscribe',
     lullaby_id: lullabyId
   }));
   ```

2. Check WebSocket state:
   ```javascript
   console.log('WebSocket state:', ws.readyState);
   // 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED
   ```

### Generation Stuck

1. Check server logs for errors
2. Verify lullaby status in Firestore:
   ```javascript
   const doc = await db.collection('lullabies').doc(lullabyId).get();
   console.log('Status:', doc.data().status);
   ```

3. Timeout after 5 minutes and show error

## Support

For issues or questions:
- Check API logs for detailed error messages
- Verify Firebase authentication is working
- Test WebSocket connection independently
- Contact support with `lullaby_id` for tracking
