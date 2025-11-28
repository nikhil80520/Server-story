# Lullaby API - Quick Start Guide

## Overview

Generate personalized AI-powered lullabies with custom lyrics and music in minutes. Perfect for bedtime stories, relaxation apps, or sleep aids.

## Quick Example

```bash
# Generate a lullaby
curl -X POST "https://your-api.com/lullabies/generate" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "A gentle lullaby about twinkling stars and sweet dreams"
  }'

# Response (takes 2-4 minutes):
{
  "lullaby": {
    "lullaby_id": "lullaby_6f476a005638",
    "audio_url": "https://storage.googleapis.com/.../lullaby_6f476a005638.mp3",
    "lyrics": "[Verse]\nTwinkling stars in the velvet sky...",
    "created_at": "2025-11-27T18:10:18Z"
  },
  "message": "Lullaby generated successfully!"
}
```

## Authentication

All endpoints require Firebase authentication:

```bash
Authorization: Bearer <your_firebase_id_token>
```

**Get your token:**
- From your app: `await firebase.auth().currentUser.getIdToken()`
- Token expires after 1 hour - refresh as needed

## Endpoints

### 1. Generate Lullaby

**POST** `/lullabies/generate`

Creates a new lullaby with AI-generated lyrics and music.

**Request:**
```json
{
  "description": "A peaceful lullaby about ocean waves and starlight",
  "child_id": "child_abc123"  // Optional: personalize for specific child
}
```

**Requirements:**
- `description`: 10-500 characters (required)
- `child_id`: Optional - if provided, personalizes lyrics with child's name, age, and interests
- Active account (trial or paid subscription)

**Response (201 Created):**
```json
{
  "lullaby": {
    "lullaby_id": "lullaby_abc123",
    "user_id": "user_xyz",
    "child_id": "child_abc123",
    "child_name": "Emma",
    "description": "A peaceful lullaby about ocean waves and starlight",
    "lyrics": "[Verse]\nGentle waves upon the shore, Emma...",
    "prompt": "soft, loving, lullaby, sleep music, gentle piano, calm",
    "audio_url": "https://storage.googleapis.com/.../lullaby_abc123.mp3",
    "duration_seconds": null,
    "created_at": "2025-11-27T18:10:18Z"
  },
  "message": "Lullaby generated successfully!"
}
```

**Generation Time:** 2-4 minutes  
**Cost:** ~$0.10-0.25 per lullaby

---

### 2. List Your Lullabies

**GET** `/lullabies/`

Get all lullabies you've created (newest first).

**Response (200 OK):**
```json
{
  "lullabies": [
    {
      "lullaby_id": "lullaby_abc123",
      "description": "A peaceful lullaby...",
      "audio_url": "https://...",
      "created_at": "2025-11-27T18:10:18Z"
    }
  ],
  "total_count": 1,
  "message": "Retrieved 1 lullabies"
}
```

---

### 3. Get Specific Lullaby

**GET** `/lullabies/{lullaby_id}`

Retrieve a single lullaby by ID.

**Response (200 OK):**
```json
{
  "lullaby": {
    "lullaby_id": "lullaby_abc123",
    "lyrics": "...",
    "audio_url": "https://..."
  },
  "message": "Lullaby retrieved successfully"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Lullaby not found or you don't have access"
}
```

---

### 4. Delete Lullaby

**DELETE** `/lullabies/{lullaby_id}`

Permanently delete a lullaby (removes audio file and metadata).

**Response (200 OK):**
```json
{
  "lullaby_id": "lullaby_abc123",
  "message": "Lullaby deleted successfully"
}
```

---

## Code Examples

### JavaScript/TypeScript

```typescript
const API_URL = 'https://your-api.com';

// Get Firebase token
const token = await firebase.auth().currentUser.getIdToken();

// Generate lullaby
async function generateLullaby(description: string) {
  const response = await fetch(`${API_URL}/lullabies/generate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ description })
  });
  
  if (!response.ok) {
    throw new Error(`Failed: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.lullaby;
}

// Generate personalized lullaby for a specific child
async function generatePersonalizedLullaby(description: string, childId: string) {
  const response = await fetch(`${API_URL}/lullabies/generate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ 
      description,
      child_id: childId  // Personalizes with child's name and interests
    })
  });
  
  if (!response.ok) {
    throw new Error(`Failed: ${response.statusText}`);
  }
  
  const data = await response.json();
  return data.lullaby;
}

// Usage
const lullaby = await generateLullaby('A gentle lullaby about moonlight');
console.log('Audio URL:', lullaby.audio_url);
console.log('Lyrics:', lullaby.lyrics);

// Personalized for child
const personalizedLullaby = await generatePersonalizedLullaby(
  'A gentle lullaby about moonlight',
  'child_abc123'
);
console.log('Personalized for:', personalizedLullaby.child_name);
console.log('Lyrics:', personalizedLullaby.lyrics);

// Play audio
const audio = new Audio(lullaby.audio_url);
audio.play();
```

### Python

```python
import requests

API_URL = 'https://your-api.com'
TOKEN = 'your_firebase_token'

headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

# Generate lullaby
response = requests.post(
    f'{API_URL}/lullabies/generate',
    headers=headers,
    json={'description': 'A gentle lullaby about moonlight'},
    timeout=300  # 5 minute timeout
)

# Generate personalized lullaby for a child
response = requests.post(
    f'{API_URL}/lullabies/generate',
    headers=headers,
    json={
        'description': 'A gentle lullaby about moonlight',
        'child_id': 'child_abc123'  # Personalizes with child's info
    },
    timeout=300
)

if response.status_code == 201:
    lullaby = response.json()['lullaby']
    print(f"Generated: {lullaby['lullaby_id']}")
    if lullaby.get('child_name'):
        print(f"Personalized for: {lullaby['child_name']}")
    print(f"Audio: {lullaby['audio_url']}")
    print(f"Lyrics:\n{lullaby['lyrics']}")
else:
    print(f"Error: {response.text}")
```

### React Native Example

```typescript
import { Audio } from 'expo-av';
import { getAuth } from 'firebase/auth';

const LullabyGenerator = () => {
  const [loading, setLoading] = useState(false);
  const [lullaby, setLullaby] = useState(null);
  const [selectedChildId, setSelectedChildId] = useState(null);

  const generateLullaby = async (description: string, childId?: string) => {
    setLoading(true);
    
    try {
      const auth = getAuth();
      const token = await auth.currentUser?.getIdToken();
      
      const payload: any = { description };
      if (childId) {
        payload.child_id = childId;  // Personalize for specific child
      }
      
      const response = await fetch('https://your-api.com/lullabies/generate', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });
      
      const data = await response.json();
      setLullaby(data.lullaby);
      
      // Play the lullaby
      const { sound } = await Audio.Sound.createAsync(
        { uri: data.lullaby.audio_url }
      );
      await sound.playAsync();
      
    } catch (error) {
      console.error('Generation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View>
      {/* Child selector (optional) */}
      <ChildPicker 
        onSelectChild={(childId) => setSelectedChildId(childId)}
      />
      
      <TextInput
        placeholder="Describe your lullaby..."
        onSubmitEditing={(e) => generateLullaby(e.nativeEvent.text, selectedChildId)}
      />
      {loading && <Text>Generating lullaby (2-4 minutes)...</Text>}
      {lullaby && (
        <View>
          {lullaby.child_name && (
            <Text>Personalized for {lullaby.child_name}</Text>
          )}
          <Text>{lullaby.lyrics}</Text>
          <Button title="Play" onPress={() => { /* play audio */ }} />
        </View>
      )}
    </View>
  );
};
```

---

## Best Practices

### 1. **Progress Indicators**
Since generation takes 2-4 minutes, show clear progress:

```typescript
const [status, setStatus] = useState('');

setStatus('📝 Generating lyrics...');
// ... lyrics generation (10-30s)

setStatus('🎵 Creating music...');
// ... music generation (60-180s)

setStatus('☁️ Uploading to storage...');
// ... upload (5-10s)

setStatus('✅ Lullaby ready!');
```

### 2. **Error Handling**
```typescript
try {
  const lullaby = await generateLullaby(description);
} catch (error) {
  if (error.status === 401) {
    // Refresh Firebase token
    token = await firebase.auth().currentUser.getIdToken(true);
  } else if (error.status === 403) {
    // Account inactive - prompt upgrade
    showUpgradeModal();
  } else if (error.status === 422) {
    // Invalid input
    showError('Description must be 10-500 characters');
  } else {
    // Generation failed - retry or show error
    showError('Generation failed. Please try again.');
  }
}
```

### 3. **Caching**
Cache generated lullabies locally to avoid regeneration:

```typescript
// Save to local storage
localStorage.setItem(`lullaby_${id}`, JSON.stringify(lullaby));

// Check cache before generating
const cached = localStorage.getItem(`lullaby_${id}`);
if (cached) {
  return JSON.parse(cached);
}
```

### 4. **Input Validation**
```typescript
function validateDescription(text: string): string | null {
  if (text.length < 10) {
    return 'Description too short (minimum 10 characters)';
  }
  if (text.length > 500) {
    return 'Description too long (maximum 500 characters)';
  }
  if (!text.trim()) {
    return 'Description cannot be empty';
  }
  return null; // Valid
}
```

---

## Technical Details

### Audio Specifications
- **Format:** MP3
- **Sample Rate:** 44.1 kHz
- **Bitrate:** 256 kbps
- **Typical Size:** 2-4 MB
- **Duration:** ~1-2 minutes

### Lyrics Format
```
[Verse]
Opening lines...

[Chorus]
Repeated section...

[Bridge]
Transition...

[Outro]
Closing lines...
```

- **Length:** 300-450 characters (max 500)
- **Style:** Gentle, soothing, child-safe
- **Themes:** Sleep, dreams, comfort, nature

### Storage
- **Audio Files:** Firebase Storage (`lullabies/{user_id}/{lullaby_id}.mp3`)
- **Metadata:** Firestore collection `lullabies`
- **URLs:** Publicly accessible, cached for 1 hour

---

## Rate Limits & Costs

### Per-User Limits
Consider implementing:
- 10 lullabies per day (suggested)
- 50 lullabies per month (suggested)
- Rate limiting via account status

### Cost Breakdown
- **OpenAI Lyrics:** ~$0.002 per generation
- **Replicate Music:** ~$0.10-0.20 per generation
- **Firebase Storage:** ~$0.026/GB/month
- **Total:** ~$0.10-0.25 per lullaby

---

## Common Issues

### 1. **Token Expired**
```
Error: "Invalid Firebase token"
```
**Solution:** Refresh token: `getIdToken(true)`

### 2. **Account Inactive**
```
Error: "Account status does not allow content access"
```
**Solution:** User needs active trial or paid subscription

### 3. **Generation Timeout**
```
Error: Request timeout after 5 minutes
```
**Solution:** Retry the request. Generation may have succeeded but response was lost.

### 4. **Description Too Short/Long**
```
Error: "String should have at least 10 characters"
```
**Solution:** Validate input: 10-500 characters required

---

## Testing

### Test Data
```json
{
  "description": "A gentle lullaby about twinkling stars and sweet dreams"
}
```

### Expected Results
- Generation time: 2-4 minutes
- Lyrics: ~300-400 characters
- Audio: MP3, 2-4 MB
- HTTP 201 status code

### Test Script
```bash
# Run provided test suite
python3 test_lullaby_api.py

# Quick test
curl -X POST "http://localhost:8000/lullabies/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "A peaceful lullaby about the ocean"}'
```

---

## Support

For issues or questions:
- API Documentation: `/docs` (Swagger UI)
- OpenAPI Schema: `/openapi.json`
- Health Check: `/health`

## Next Steps

1. Get your Firebase authentication token
2. Try the quick example above
3. Integrate into your app
4. Add proper error handling and progress indicators
5. Consider implementing caching and rate limiting

Happy lullaby generation! 🎵✨
