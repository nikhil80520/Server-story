# 📋 Story Response Quick Reference

## What's Included When Fetching Stories

### Core Story Data
```json
{
  "story_id": "story_abc123",
  "title": "Sarah's Adventure",
  "user_prompt": "A story about courage",
  "created_at": "2025-10-27T20:36:08Z",
  "status": "completed",
  "story_number": 42
}
```

### Child Information
```json
{
  "child_name": "Sarah",
  "child_age": 7
}
```

### Educational Content
```json
{
  "morals": ["kindness", "courage", "friendship"],
  "story_length": "medium",
  "art_style": "magical"
}
```

### Voice Information ⭐ NEW
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

### Media Assets
```json
{
  "thumbnail_url": "https://storage.googleapis.com/.../thumbnail.jpg",
  "total_scenes": 5,
  "total_duration": 85420,
  "scenes_data": [
    {
      "scene_number": 1,
      "text": "Once upon a time...",
      "visual_prompt": "A young girl...",
      "audio_url": "https://.../scene_1.opus",
      "image_url": "https://.../scene_1.jpg",
      "duration": 16542,
      "includes_child": true
    }
  ]
}
```

### AI Models Used ⭐ NEW
```json
{
  "ai_models_used": {
    "text_generation": "gpt-4o-mini",
    "audio_generation": "elevenlabs-v2.5-flash",
    "image_generation": "gpt-image-1-mini"
  }
}
```

### Performance Metrics
```json
{
  "generation_method": "parallel_processing_v2",
  "performance_metrics": {
    "total_generation_time": 45.23,
    "success_rate": 100.0
  },
  "optimizations": [
    "parallel_media_generation",
    "batch_audio_processing",
    "opus_audio_optimization"
  ]
}
```

## Endpoints That Return This Data

| Endpoint | Description | Returns |
|----------|-------------|---------|
| `GET /stories/user/stories` | List user's stories | Array of full story objects |
| `GET /stories/details/{story_id}` | Get single story | Full story object |
| `GET /stories/fetch/{story_id}` | Poll story status | Full story when complete |
| `GET /stories/user/{token}/summary` | Quick summary | Latest 3 stories |

## Quick Access Examples

### Get Voice Name
```javascript
const voiceName = story.voice_metadata?.voice_name || "Default Voice";
```

### Get Morals Taught
```javascript
const morals = story.morals || [];
console.log(`Teaches: ${morals.join(', ')}`);
```

### Check if Using Cloned Voice
```javascript
const isCloned = story.voice_metadata?.is_cloned === true;
```

### Get Story Duration
```javascript
const durationSeconds = story.total_duration / 1000;
console.log(`${durationSeconds}s long`);
```

## See Full Documentation
- [Complete Story Metadata Guide](./STORY_METADATA.md)
- [Language Support](../language-support/README.md)
