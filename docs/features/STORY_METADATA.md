# 🎵 Story Metadata & Voice Information

Complete documentation for story metadata including voice ID details and morals tracking.

## Overview

When you generate or fetch stories, the API returns comprehensive metadata including:
- **Voice Information**: Which voice was used (cloned or default)
- **Morals**: The moral lessons taught in the story
- **AI Models**: Which models generated text, audio, and images
- **Performance Metrics**: Generation time and optimization details

## Voice Metadata in Stories

### What Gets Stored

Every story now includes detailed voice information:

```json
{
  "voice_metadata": {
    "voice_id": "21m00Tcm4TlvDq8ikWAM",
    "voice_name": "Rachel (Default)",
    "is_cloned": false,
    "language": "english"
  }
}
```

**Fields:**
- `voice_id` (string): ElevenLabs voice ID used for audio generation
- `voice_name` (string): Human-readable name of the voice
- `is_cloned` (boolean): Whether this is a user's cloned voice or the default
- `language` (string): Language used for the story and TTS

### When Using Cloned Voices

When a user has a cloned voice active:

```json
{
  "voice_metadata": {
    "voice_id": "xyz123abc456",
    "voice_name": "Mom's Voice",
    "is_cloned": true,
    "language": "english"
  }
}
```

## Morals in Stories

### Storing Morals

Morals are specified during story generation and stored in the manifest:

```json
{
  "morals": ["kindness", "courage", "friendship"],
  "story_length": "medium",
  "art_style": "magical"
}
```

### Request Format

When generating a story, specify morals as an array:

```json
{
  "firebase_token": "YOUR_TOKEN",
  "child_name": "Sarah",
  "child_age": 7,
  "morals": ["honesty", "perseverance"],
  "story_length": "short",
  "language": "english",
  "prompt": "A story about overcoming challenges"
}
```

## Complete Story Response

### Full Story Manifest

When fetching stories via `GET /stories/user/stories`, each story includes:

```json
{
  "story_id": "story_abc123",
  "title": "Sarah's Brave Adventure",
  "user_prompt": "A story about overcoming challenges",
  "created_at": "2025-10-27T20:36:08.737732+00:00",
  "updated_at": "2025-10-27T20:36:08.737732+00:00",
  
  "child_name": "Sarah",
  "child_age": 7,
  "morals": ["honesty", "perseverance"],
  "story_length": "short",
  "art_style": "magical",
  
  "total_scenes": 5,
  "total_duration": 85420,
  "status": "completed",
  "story_number": 42,
  
  "thumbnail_url": "https://storage.googleapis.com/.../thumbnail.jpg",
  "generation_method": "parallel_processing_v2",
  
  "voice_metadata": {
    "voice_id": "xyz123abc456",
    "voice_name": "Mom's Voice",
    "is_cloned": true,
    "language": "english"
  },
  
  "ai_models_used": {
    "text_generation": "gpt-4o-mini",
    "audio_generation": "elevenlabs-v2.5-flash",
    "image_generation": "gpt-image-1-mini"
  },
  
  "image_format": "custom_dimensions_from_deepai",
  
  "optimizations": [
    "parallel_media_generation",
    "batch_audio_processing",
    "batch_image_processing",
    "parallel_uploads",
    "retry_mechanisms",
    "semaphore_rate_limiting",
    "exception_handling",
    "performance_tracking",
    "opus_audio_optimization"
  ],
  
  "scenes_data": [
    {
      "scene_number": 1,
      "text": "Once upon a time, Sarah faced a big challenge...",
      "visual_prompt": "A young girl standing at the edge of a forest...",
      "audio_url": "https://storage.googleapis.com/.../audio/scene_1.opus",
      "image_url": "https://storage.googleapis.com/.../images/scene_1.jpg",
      "start_time": 0,
      "duration": 16542,
      "includes_child": true
    }
  ],
  
  "manifest": {
    "story_id": "story_abc123",
    "title": "Sarah's Brave Adventure",
    "child_name": "Sarah",
    "child_age": 7,
    "morals": ["honesty", "perseverance"],
    "voice_metadata": {
      "voice_id": "xyz123abc456",
      "voice_name": "Mom's Voice",
      "is_cloned": true,
      "language": "english"
    },
    "scenes": [...],
    "performance_metrics": {
      "total_generation_time": 45.23,
      "success_rate": 100.0,
      "parallel_efficiency": {
        "speedup_factor": 7.1,
        "actual_parallel_time": 45.23,
        "estimated_sequential_time": 321.13
      }
    }
  },
  
  "performance_metrics": {
    "total_generation_time": 45.23,
    "success_rate": 100.0,
    "task_breakdown": {
      "audio": {
        "count": 5,
        "completed": 5,
        "failed": 0,
        "avg_duration": 12.4
      },
      "image": {
        "count": 6,
        "completed": 6,
        "failed": 0,
        "avg_duration": 8.2
      }
    }
  }
}
```

## API Endpoints

### 1. Generate Story (with voice metadata)

```bash
POST /stories/generate
Authorization: Bearer {firebase_token}
```

**Request:**
```json
{
  "child_name": "Alex",
  "child_age": 8,
  "morals": ["courage", "friendship"],
  "story_length": "medium",
  "language": "english",
  "art_style": "magical",
  "prompt": "A brave knight helps his friend",
  "should_use_voice_clone": true
}
```

**Response:**
```json
{
  "success": true,
  "story_id": "story_xyz789",
  "message": "Story generation started!",
  "job_id": "job_123",
  "status": "processing"
}
```

### 2. Fetch User Stories (includes all metadata)

```bash
GET /stories/user/stories?limit=10&offset=0
Authorization: Bearer {firebase_token}
```

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "filter": "owned",
  "stories": [
    {
      "story_id": "story_xyz789",
      "title": "The Brave Knight",
      "morals": ["courage", "friendship"],
      "voice_metadata": {
        "voice_id": "custom_voice_id",
        "voice_name": "Dad's Voice",
        "is_cloned": true,
        "language": "english"
      },
      "scenes_data": [...],
      "...": "..."
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 5,
    "page_size": 10,
    "has_more": true,
    "total_count": 47
  }
}
```

### 3. Get Story Details

```bash
GET /stories/details/{story_id}
```

Returns complete story with voice_metadata and morals included in the manifest.

### 4. Fetch Story Status (during generation)

```bash
GET /stories/fetch/{story_id}
```

While generating:
```json
{
  "success": false,
  "status": "generating_media",
  "message": "Story is still generating...",
  "story_id": "story_xyz789",
  "title": "The Brave Knight"
}
```

When complete:
```json
{
  "success": true,
  "message": "Story generated successfully!",
  "story": {
    "story_id": "story_xyz789",
    "title": "The Brave Knight",
    "morals": ["courage", "friendship"],
    "voice_metadata": {
      "voice_id": "custom_voice_id",
      "voice_name": "Dad's Voice",
      "is_cloned": true,
      "language": "english"
    },
    "scenes": [...],
    "...": "..."
  }
}
```

## Legacy Support

For backward compatibility, stories generated before this update will:
- Not have `voice_metadata` field (check for existence)
- Still have `morals` array if specified during generation
- Use `voice_option` field instead (`"female"` or `"male"`)

## Examples

### Python Example

```python
import requests

# Generate story with morals and voice clone
response = requests.post(
    "https://your-api.com/stories/generate",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "child_name": "Emma",
        "child_age": 6,
        "morals": ["kindness", "sharing"],
        "story_length": "short",
        "language": "english",
        "should_use_voice_clone": True,
        "prompt": "A story about sharing toys"
    }
)

story_id = response.json()["story_id"]

# Fetch the completed story
stories = requests.get(
    "https://your-api.com/stories/user/stories",
    headers={"Authorization": f"Bearer {token}"},
    params={"limit": 1}
).json()

story = stories["stories"][0]

print(f"Title: {story['title']}")
print(f"Morals: {', '.join(story['morals'])}")
print(f"Voice: {story['voice_metadata']['voice_name']}")
print(f"Is Cloned: {story['voice_metadata']['is_cloned']}")
```

### JavaScript Example

```javascript
// Generate story
const response = await fetch('https://your-api.com/stories/generate', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    child_name: 'Liam',
    child_age: 7,
    morals: ['honesty', 'bravery'],
    story_length: 'medium',
    language: 'english',
    should_use_voice_clone: true,
    prompt: 'A story about being honest'
  })
});

const { story_id } = await response.json();

// Fetch stories
const storiesResponse = await fetch(
  'https://your-api.com/stories/user/stories?limit=10',
  {
    headers: { 'Authorization': `Bearer ${token}` }
  }
);

const { stories } = await storiesResponse.json();

stories.forEach(story => {
  console.log(`📖 ${story.title}`);
  console.log(`📚 Morals: ${story.morals.join(', ')}`);
  console.log(`🎤 Voice: ${story.voice_metadata.voice_name}`);
  console.log(`🔊 Cloned: ${story.voice_metadata.is_cloned ? 'Yes' : 'No'}`);
});
```

## Voice Cloning Integration

### How Voice Selection Works

1. **User creates voice clone** → Voice ID stored in Firebase
2. **Story generation** → System automatically uses cloned voice if available
3. **Story metadata** → Voice details stored in story manifest
4. **Story playback** → Audio URLs already use the correct voice

### Checking Voice Status

```bash
GET /users/voice-clone/status
Authorization: Bearer {firebase_token}
```

**Response:**
```json
{
  "has_voice_clone": true,
  "voice_id": "custom_voice_id",
  "voice_name": "My Voice",
  "created_at": "2025-10-15T10:30:00Z",
  "language": "english"
}
```

## Best Practices

### 1. Always Check voice_metadata

```javascript
// Safe access to voice metadata
const voiceInfo = story.voice_metadata || {
  voice_name: "Default Voice",
  is_cloned: false
};

console.log(`Using ${voiceInfo.voice_name}`);
```

### 2. Display Morals to Parents

```javascript
// Show which morals were taught
if (story.morals && story.morals.length > 0) {
  console.log(`📚 This story teaches: ${story.morals.join(', ')}`);
}
```

### 3. Filter by Voice Type

```javascript
// Find stories using cloned voice
const clonedVoiceStories = stories.filter(
  s => s.voice_metadata?.is_cloned === true
);

console.log(`${clonedVoiceStories.length} stories using your custom voice`);
```

### 4. Multi-Language Support

```javascript
// Group stories by language
const storiesByLanguage = stories.reduce((acc, story) => {
  const lang = story.voice_metadata?.language || 'english';
  acc[lang] = (acc[lang] || []).concat(story);
  return acc;
}, {});

console.log(`Stories in English: ${storiesByLanguage.english?.length || 0}`);
console.log(`Stories in Hindi: ${storiesByLanguage.hindi?.length || 0}`);
```

## Troubleshooting

### Voice Metadata Missing

**Issue**: Old stories don't have `voice_metadata`

**Solution**: Check for field existence before accessing
```javascript
const voiceName = story.voice_metadata?.voice_name || "Legacy Voice";
```

### Morals Array Empty

**Issue**: Story has empty morals array

**Solution**: This means no specific morals were specified during generation
```javascript
const morals = story.morals?.length > 0 
  ? story.morals 
  : ["general life lessons"];
```

### Voice ID Changed

**Issue**: User updated their voice clone after story was generated

**Solution**: Story keeps the voice metadata from generation time (historical record)

---

**Last Updated**: October 2025 | **Status**: ✅ Production Ready
