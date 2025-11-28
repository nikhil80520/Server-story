# Lullaby API Documentation

## Overview

The Lullaby API allows users to generate personalized AI-powered lullabies with custom lyrics and music. The system uses OpenAI GPT-4o for lyrics generation and Replicate's MiniMax Music-1.5 model for music generation.

## Features

- 🎵 **AI-Generated Lyrics**: Creates soothing lullaby lyrics based on user descriptions using OpenAI
- 🎼 **AI-Generated Music**: Generates gentle sleep music using Replicate's MiniMax Music-1.5
- ☁️ **Firebase Storage**: Stores audio files securely in Firebase Storage
- 📝 **Metadata Management**: Tracks lyrics, prompts, and creation timestamps
- 🔒 **User-Specific**: Each user's lullabies are private and tied to their account

## API Endpoints

### 1. Generate Lullaby

**POST** `/lullabies/generate`

Generates a new lullaby with AI-created lyrics and music.

#### Request Body

```json
{
  "description": "A gentle lullaby about stars and dreams for my baby"
}
```

**Parameters:**
- `description` (string, required): Description of what the lullaby should be about (10-500 characters)

#### Response (201 Created)

```json
{
  "lullaby": {
    "lullaby_id": "lullaby_abc123def456",
    "user_id": "user_xyz789",
    "description": "A gentle lullaby about stars and dreams for my baby",
    "lyrics": "[Verse]\nIn the hush of night, we find our space,\nWrapped in moonlight's gentle embrace.\nYour whisper's soft, like a velvet song,\nIn this tender moment, where we both belong.\n\n[Chorus]\nJust you and me, in this lazy jazz,\nOur souls entwined, nothing else we ask.\nIn this serenade, we sway and sigh,\nLost in this love, beneath the starry sky.\n\n[Bridge]\nYour voice, a lullaby, soothes my soul,\nIn this night, together, we feel whole.\nEach moment shared, a timeless flight,\nIn this gentle jazz, we find our light.\n\n[Outro]\nAs dawn approaches, and stars fade away,\nIn your arms, I wish to forever stay.",
    "prompt": "soft, loving, lullaby, sleep music, gentle piano, calm",
    "audio_url": "https://firebasestorage.googleapis.com/v0/b/storyteller-7ece7.appspot.com/o/lullabies%2Fuser_xyz789%2Flullaby_abc123def456.mp3?alt=media",
    "duration_seconds": null,
    "created_at": "2025-11-27T12:34:56.789Z"
  },
  "message": "Lullaby generated successfully! Your personalized sleep music is ready."
}
```

#### Generation Process

1. **Lyrics Generation** (~10-30s): Uses OpenAI GPT-4o to create structured lyrics with [Verse], [Chorus], [Bridge], and [Outro] sections
2. **Music Generation** (~60-180s): Uses Replicate MiniMax Music-1.5 to generate MP3 audio based on lyrics
3. **Storage Upload** (~5-10s): Uploads MP3 to Firebase Storage with public access
4. **Metadata Save**: Stores metadata in Firestore for future retrieval

**Total Generation Time**: ~2-4 minutes

---

### 2. Get All User Lullabies

**GET** `/lullabies/`

Retrieves all lullabies for the authenticated user.

#### Response (200 OK)

```json
{
  "lullabies": [
    {
      "lullaby_id": "lullaby_abc123def456",
      "user_id": "user_xyz789",
      "description": "A gentle lullaby about stars and dreams",
      "lyrics": "[Verse]\n...",
      "prompt": "soft, loving, lullaby, sleep music",
      "audio_url": "https://firebasestorage.googleapis.com/...",
      "duration_seconds": null,
      "created_at": "2025-11-27T12:34:56.789Z"
    },
    {
      "lullaby_id": "lullaby_xyz789abc123",
      "user_id": "user_xyz789",
      "description": "A peaceful lullaby about the ocean",
      "lyrics": "[Verse]\n...",
      "prompt": "soft, loving, lullaby, sleep music",
      "audio_url": "https://firebasestorage.googleapis.com/...",
      "duration_seconds": null,
      "created_at": "2025-11-26T08:15:30.123Z"
    }
  ],
  "total_count": 2,
  "message": "Retrieved 2 lullabies"
}
```

**Sorting**: Results are sorted by creation date (newest first)

---

### 3. Get Specific Lullaby

**GET** `/lullabies/{lullaby_id}`

Retrieves a specific lullaby by ID.

#### Path Parameters

- `lullaby_id` (string, required): The unique ID of the lullaby

#### Response (200 OK)

```json
{
  "lullaby": {
    "lullaby_id": "lullaby_abc123def456",
    "user_id": "user_xyz789",
    "description": "A gentle lullaby about stars and dreams",
    "lyrics": "[Verse]\n...",
    "prompt": "soft, loving, lullaby, sleep music",
    "audio_url": "https://firebasestorage.googleapis.com/...",
    "duration_seconds": null,
    "created_at": "2025-11-27T12:34:56.789Z"
  },
  "message": "Lullaby retrieved successfully"
}
```

#### Error Response (404 Not Found)

```json
{
  "detail": "Lullaby lullaby_abc123def456 not found or you don't have access"
}
```

---

### 4. Delete Lullaby

**DELETE** `/lullabies/{lullaby_id}`

Deletes a lullaby (both audio file and metadata).

#### Path Parameters

- `lullaby_id` (string, required): The unique ID of the lullaby to delete

#### Response (200 OK)

```json
{
  "lullaby_id": "lullaby_abc123def456",
  "message": "Lullaby deleted successfully"
}
```

#### Error Response (404 Not Found)

```json
{
  "detail": "Lullaby lullaby_abc123def456 not found or you don't have access"
}
```

---

## Authentication

All endpoints require Firebase authentication via Bearer token in the `Authorization` header:

```
Authorization: Bearer <firebase_id_token>
```

## Example Usage

### cURL Examples

#### Generate a Lullaby

```bash
curl -X POST "https://your-domain.com/lullabies/generate" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "A gentle lullaby about stars and dreams for my baby"
  }'
```

#### Get All Lullabies

```bash
curl -X GET "https://your-domain.com/lullabies/" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN"
```

#### Get Specific Lullaby

```bash
curl -X GET "https://your-domain.com/lullabies/lullaby_abc123def456" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN"
```

#### Delete Lullaby

```bash
curl -X DELETE "https://your-domain.com/lullabies/lullaby_abc123def456" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN"
```

### JavaScript/TypeScript Example

```typescript
const API_URL = 'https://your-domain.com';

// Generate lullaby
async function generateLullaby(token: string, description: string) {
  const response = await fetch(`${API_URL}/lullabies/generate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ description })
  });
  
  if (!response.ok) {
    throw new Error(`Failed to generate lullaby: ${response.statusText}`);
  }
  
  return await response.json();
}

// Get all lullabies
async function getLullabies(token: string) {
  const response = await fetch(`${API_URL}/lullabies/`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return await response.json();
}

// Delete lullaby
async function deleteLullaby(token: string, lullabyId: string) {
  const response = await fetch(`${API_URL}/lullabies/${lullabyId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return await response.json();
}

// Usage
const token = await firebase.auth().currentUser.getIdToken();
const result = await generateLullaby(token, 'A lullaby about the moon');
console.log('Generated:', result.lullaby.audio_url);
```

## Technical Details

### Lyrics Structure

Lyrics are generated with the following structure tags:
- `[Verse]`: Story/narrative sections
- `[Chorus]`: Repeated emotional core
- `[Bridge]`: Transition/variation
- `[Outro]`: Gentle ending

**Length**: Target 400-450 characters, **Maximum 500 characters** (strict limit for MiniMax API compatibility)

### Music Generation

**Model**: MiniMax Music-1.5 (via Replicate)

**Default Parameters**:
- `prompt`: "soft, loving, lullaby, sleep music, gentle piano, calm"
- `audio_format`: "mp3"
- `sample_rate`: 44100 Hz
- `bitrate`: 256000 bps

**Output**: MP3 file stored in Firebase Storage at:
```
lullabies/{user_id}/{lullaby_id}.mp3
```

### Data Storage

**Firestore Collection**: `lullabies`

**Document Structure**:
```typescript
{
  lullaby_id: string,      // Unique ID (e.g., "lullaby_abc123def456")
  user_id: string,         // Firebase UID of owner
  description: string,     // User's input description
  lyrics: string,          // Generated lyrics with structure tags
  prompt: string,          // Music generation prompt used
  audio_url: string,       // Public Firebase Storage URL
  duration_seconds: number | null,  // Duration (currently not calculated)
  created_at: timestamp    // ISO 8601 timestamp
}
```

### Firestore Security Rules

Ensure your Firestore security rules allow users to read/write their own lullabies:

```javascript
match /lullabies/{lullabyId} {
  allow read, write: if request.auth != null 
    && request.auth.uid == resource.data.user_id;
  allow create: if request.auth != null 
    && request.auth.uid == request.resource.data.user_id;
}
```

### Firebase Storage Security Rules

Storage rules for lullaby audio files:

```
match /lullabies/{userId}/{lullabyId}.mp3 {
  allow read: if true;  // Public read (or add auth if needed)
  allow write: if request.auth != null && request.auth.uid == userId;
  allow delete: if request.auth != null && request.auth.uid == userId;
}
```

## Error Handling

### Common Errors

**400 Bad Request**
```json
{
  "detail": [
    {
      "loc": ["body", "description"],
      "msg": "ensure this value has at least 10 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

**401 Unauthorized**
```json
{
  "detail": "Not authenticated"
}
```

**404 Not Found**
```json
{
  "detail": "Lullaby lullaby_xyz123 not found or you don't have access"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Failed to generate lullaby: Music generation timed out - please try again"
}
```

### Timeout Scenarios

- **Lyrics Generation**: 60s timeout (usually completes in 10-30s)
- **Music Generation**: 300s (5 minute) timeout (usually completes in 60-180s)
- **Total Request**: May take 2-4 minutes for complete generation

**Recommendation**: Use webhooks or polling for production apps to avoid client timeouts.

## Rate Limiting

- Lullaby generation is compute-intensive (2-4 minutes per request)
- Consider implementing per-user rate limits (e.g., 10 lullabies per day)
- OpenAI and Replicate APIs have their own rate limits

## Best Practices

1. **User Experience**: Show progress indicators during generation (lyrics → music → upload)
2. **Error Handling**: Implement retry logic for failed generations
3. **Caching**: Cache generated lullabies locally to reduce API calls
4. **Validation**: Validate description length and content before submission
5. **Storage Management**: Consider implementing lullaby limits per user to manage storage costs

## Costs

Estimated costs per lullaby generation:

- **OpenAI GPT-4o Lyrics**: ~$0.002 (500 tokens @ $5/1M tokens)
- **Replicate Music Generation**: ~$0.10-0.20 per generation
- **Firebase Storage**: ~$0.026/GB/month for storage

**Total per lullaby**: ~$0.10-0.25

## Interactive Documentation

Visit `/docs` for interactive Swagger UI documentation where you can test all endpoints directly.

## Support

For issues or questions, please refer to the main API documentation or contact support.
