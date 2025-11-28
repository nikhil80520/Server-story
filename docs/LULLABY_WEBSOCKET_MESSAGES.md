# Lullaby WebSocket Messages - Quick Reference

## Connection

```javascript
// Connect with Firebase token
const ws = new WebSocket(`wss://your-api.com/ws/lullabies/${firebaseToken}`);
```

## Client → Server (Messages You Send)

### Subscribe to Lullaby Updates
```json
{
  "action": "subscribe",
  "lullaby_id": "lullaby_89f51c3e8130"
}
```

### Unsubscribe from Updates
```json
{
  "action": "unsubscribe",
  "lullaby_id": "lullaby_89f51c3e8130"
}
```

### Request Heartbeat
```json
{
  "action": "ping"
}
```

## Server → Client (Events You Receive)

### 1. Connected
```json
{
  "event": "connected",
  "message": "Connected to lullaby notifications",
  "timestamp": "2024-11-27T18:48:46.123Z"
}
```

### 2. Subscribed
```json
{
  "event": "subscribed",
  "lullaby_id": "lullaby_89f51c3e8130",
  "message": "Subscribed to lullaby updates",
  "timestamp": "2024-11-27T18:48:46.456Z"
}
```

### 3. Progress Updates

#### Stage 1: Starting (0%)
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

#### Stage 2: Generating Lyrics (10%)
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

#### Stage 3: Lyrics Complete (25%) ⭐ **INCLUDES LYRICS**
```json
{
  "event": "lullaby_progress",
  "lullaby_id": "lullaby_89f51c3e8130",
  "status": "lyrics_complete",
  "progress": 25,
  "message": "Lyrics generated! Creating music...",
  "lyrics": "Twinkle, twinkle, little star,\nHow I wonder what you are...",
  "timestamp": "2024-11-27T18:48:48.000Z"
}
```

#### Stage 4: Music Complete (75%)
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

#### Stage 5: Upload Complete (90%)
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

### 4. Completion (100%) ⭐ **INCLUDES AUDIO URL**
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
    "audio_url": "https://storage.googleapis.com/.../lullaby_89f51c3e8130.mp3",
    "duration_seconds": null,
    "created_at": "2024-11-27T18:48:46Z"
  },
  "timestamp": "2024-11-27T18:50:33.000Z"
}
```

### 5. Failed
```json
{
  "event": "lullaby_failed",
  "lullaby_id": "lullaby_89f51c3e8130",
  "error": "Music generation timeout",
  "message": "Generation failed: Music generation timeout",
  "timestamp": "2024-11-27T18:50:33.000Z"
}
```

### 6. Heartbeat (Every 30s)
```json
{
  "event": "heartbeat",
  "timestamp": "2024-11-27T18:50:00.000Z"
}
```

### 7. Unsubscribed
```json
{
  "event": "unsubscribed",
  "lullaby_id": "lullaby_89f51c3e8130",
  "message": "Unsubscribed from lullaby updates",
  "timestamp": "2024-11-27T18:51:00.000Z"
}
```

### 8. Error
```json
{
  "event": "error",
  "message": "Invalid action",
  "timestamp": "2024-11-27T18:51:00.000Z"
}
```

## Progress Timeline

| Progress | Status | Approx Duration | What's Happening |
|----------|--------|-----------------|------------------|
| 0% | `starting` | < 1s | Initialization |
| 10% | `generating_lyrics` | 10-30s | OpenAI generates lyrics |
| 25% | `lyrics_complete` | - | ✅ Lyrics ready! |
| 25-75% | (music generation) | 60-180s | MiniMax generates audio |
| 75% | `music_complete` | - | ✅ Music ready! |
| 75-90% | (uploading) | 5-10s | Upload to Firebase |
| 90% | `upload_complete` | - | ✅ Uploaded! |
| 90-100% | (saving) | 1-2s | Save metadata |
| 100% | `completed` | - | 🎉 Ready to play! |

## Minimal Client Example

```javascript
const ws = new WebSocket(`wss://api.com/ws/lullabies?user_token=${token}`);

ws.onopen = () => {
  // Subscribe to lullaby
  ws.send(JSON.stringify({
    action: 'subscribe',
    lullaby_id: 'lullaby_89f51c3e8130'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.event) {
    case 'lullaby_progress':
      console.log(`${data.progress}%: ${data.message}`);
      if (data.lyrics) {
        console.log('Lyrics:', data.lyrics);
      }
      break;
      
    case 'lullaby_completed':
      console.log('Audio URL:', data.lullaby.audio_url);
      // Play audio here
      break;
      
    case 'lullaby_failed':
      console.error('Failed:', data.error);
      break;
  }
};
```

## Key Points

1. **Connect with Firebase token** in query parameter
2. **Subscribe to lullaby_id** to receive updates
3. **Lyrics available at 25%** - show them to user!
4. **Audio URL in completion event** - play immediately
5. **Heartbeat every 30 seconds** - connection stays alive
6. **Reconnect on disconnect** - implement exponential backoff

## Status Field Values

- `starting` - Beginning generation
- `generating_lyrics` - Creating lyrics with OpenAI
- `lyrics_complete` - Lyrics done (includes `lyrics` field)
- `music_complete` - Music generated
- `upload_complete` - Uploaded to storage
- `completed` - Fully done (in completion event)
- `failed` - Generation failed (in failed event)
