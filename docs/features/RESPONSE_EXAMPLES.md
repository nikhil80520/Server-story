# 🎯 Real API Response Examples

## Example 1: Story with Cloned Voice

### Request
```bash
GET /stories/user/stories?limit=1
Authorization: Bearer eyJhbGc...
```

### Response
```json
{
  "success": true,
  "user_id": "CnHUiHOSe0RGDPPev6fAeY4YfXj1",
  "filter": "owned",
  "stories": [
    {
      "story_id": "story_1ea24125",
      "title": "Ava and the Friendship Star",
      "user_prompt": "Create a medium story for Ava (age 6) about kindness, friendship in magical style",
      "created_at": "2025-10-27T20:36:08.737732+00:00",
      "updated_at": "2025-10-27T20:36:08.737732+00:00",
      "total_scenes": 7,
      "total_duration": 118142,
      "status": "completed",
      "story_number": 111,
      "thumbnail_url": "https://storage.googleapis.com/storyteller-7ece7.firebasestorage.app/stories/story_1ea24125/thumbnail.jpg",
      "generation_method": "parallel_processing_v2",
      
      "child_name": "Ava",
      "child_age": 6,
      "morals": ["kindness", "friendship"],
      "story_length": "medium",
      "art_style": "magical",
      "dimensions": "portrait",
      
      "voice_metadata": {
        "voice_id": "xyz123abc456",
        "voice_name": "Mom's Voice",
        "is_cloned": true,
        "language": "english"
      },
      
      "ai_models_used": {
        "audio_generation": "elevenlabs-v2.5-flash",
        "text_generation": "gpt-4o-mini",
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
          "duration": 16542,
          "start_time": 0,
          "includes_child": true,
          "image_url": "https://storage.googleapis.com/storyteller-7ece7.firebasestorage.app/stories/story_1ea24125/images/scene_1_colored.jpg",
          "audio_url": "https://storage.googleapis.com/storyteller-7ece7.firebasestorage.app/stories/story_1ea24125/audio/scene_1-9d7dbbe6.opus?alt=media",
          "scene_number": 1,
          "text": "Once upon a time, in a magical kingdom where the stars twinkled like diamonds, there lived a little girl named Ava. She loved playing basketball with her friends and dreaming about space adventures. One day, while dribbling her basketball near a sparkling stream, she noticed a shimmering star falling from the sky!",
          "visual_prompt": "A vibrant illustration of a young girl named Ava, playing basketball by a sparkling stream. In the background, a star is falling from a colorful sky filled with twinkling stars. The scene is magical and filled with bright colors."
        },
        {
          "duration": 18527,
          "start_time": 16542,
          "includes_child": true,
          "image_url": "https://storage.googleapis.com/storyteller-7ece7.firebasestorage.app/stories/story_1ea24125/images/scene_2_colored.jpg",
          "audio_url": "https://storage.googleapis.com/storyteller-7ece7.firebasestorage.app/stories/story_1ea24125/audio/scene_2-1c14aa0d.opus?alt=media",
          "scene_number": 2,
          "text": "Curious, Ava followed the star as it landed softly on a fluffy cloud. To her surprise, the star turned into a friendly little princess named Lila, who had come from the land of Kindness. 'Thank you for finding me!' Lila exclaimed with a bright smile. 'I was looking for a friend to help me spread kindness in the world!'",
          "visual_prompt": "A magical scene where Ava meets Princess Lila, a glowing star princess. They are on a fluffy cloud surrounded by colorful, friendly animals like rabbits and birds, all smiling and watching."
        }
      ],
      
      "performance_metrics": {
        "success_rate": 100.0,
        "average_task_durations": {
          "image": 33.64,
          "upload": 5.72,
          "story": 0,
          "audio": 124.8
        },
        "parallel_efficiency": {
          "actual_parallel_time": 173.87768602371216,
          "speedup_factor": 7.1,
          "estimated_sequential_time": 1228.5154161453247,
          "max_concurrent_tasks": 10
        },
        "failed_tasks": 0,
        "total_generation_time": 173.88
      }
    }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 19,
    "page_size": 6,
    "offset": 0,
    "returned_count": 1,
    "total_count": 111,
    "has_more": true
  }
}
```

## Example 2: Story with Default Voice

```json
{
  "story_id": "story_abc789",
  "title": "The Brave Little Robot",
  "morals": ["courage", "perseverance"],
  "voice_metadata": {
    "voice_id": "21m00Tcm4TlvDq8ikWAM",
    "voice_name": "Rachel (Default)",
    "is_cloned": false,
    "language": "english"
  }
}
```

## Example 3: Multi-Language Story (Hindi)

```json
{
  "story_id": "story_xyz456",
  "title": "राज और जादुई जंगल",
  "child_name": "राज",
  "morals": ["courage", "friendship"],
  "voice_metadata": {
    "voice_id": "custom_hindi_voice",
    "voice_name": "Papa's Voice",
    "is_cloned": true,
    "language": "hindi"
  },
  "scenes_data": [
    {
      "scene_number": 1,
      "text": "एक बार की बात है, राज नाम का एक बहादुर लड़का था...",
      "audio_url": "https://.../scene_1.opus"
    }
  ]
}
```

## Example 4: Fetching Multiple Stories

### Request
```bash
GET /stories/user/stories?limit=3&offset=0&filter=owned
Authorization: Bearer eyJhbGc...
```

### Response Summary
```json
{
  "success": true,
  "stories": [
    {
      "story_id": "story_001",
      "title": "Adventure 1",
      "morals": ["kindness"],
      "voice_metadata": { "is_cloned": true, "voice_name": "Mom's Voice" }
    },
    {
      "story_id": "story_002",
      "title": "Adventure 2",
      "morals": ["courage", "friendship"],
      "voice_metadata": { "is_cloned": true, "voice_name": "Mom's Voice" }
    },
    {
      "story_id": "story_003",
      "title": "Adventure 3",
      "morals": ["honesty"],
      "voice_metadata": { "is_cloned": false, "voice_name": "Rachel (Default)" }
    }
  ],
  "pagination": {
    "total_count": 111,
    "has_more": true
  }
}
```

## Example 5: Story Status Check (During Generation)

### Request
```bash
GET /stories/fetch/story_xyz123
```

### Response (In Progress)
```json
{
  "success": false,
  "status": "generating_media",
  "message": "Story is still generating... Status: generating_media",
  "story_id": "story_xyz123",
  "title": "Generating..."
}
```

### Response (Completed)
```json
{
  "success": true,
  "message": "Story 'The Amazing Journey' generated successfully!",
  "story": {
    "story_id": "story_xyz123",
    "title": "The Amazing Journey",
    "morals": ["bravery", "teamwork"],
    "voice_metadata": {
      "voice_id": "xyz123",
      "voice_name": "Custom Voice",
      "is_cloned": true,
      "language": "english"
    },
    "total_scenes": 7,
    "scenes": [...],
    "performance_metrics": {...}
  }
}
```

## Key Observations

### ✅ Always Present
- `story_id`
- `title`
- `morals` (array, may be empty)
- `voice_metadata` (new stories only)
- `scenes_data` (when completed)
- `status`

### 🔄 Sometimes Present
- `voice_metadata` (new feature - check for existence)
- `performance_metrics` (completed stories only)
- `thumbnail_url` (when generation successful)

### 📊 Accessing Nested Data

```javascript
// Safe access patterns
const voiceName = story.voice_metadata?.voice_name || "Unknown Voice";
const morals = story.morals || [];
const isCloned = story.voice_metadata?.is_cloned ?? false;
const language = story.voice_metadata?.language || "english";
```

## Testing These Endpoints

### Using cURL
```bash
# Fetch stories
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://your-api.com/stories/user/stories?limit=5"

# Get specific story
curl "https://your-api.com/stories/details/story_abc123"
```

### Using Python
```python
import requests

token = "YOUR_FIREBASE_TOKEN"
headers = {"Authorization": f"Bearer {token}"}

# Fetch stories
response = requests.get(
    "https://your-api.com/stories/user/stories",
    headers=headers,
    params={"limit": 5}
)

stories = response.json()["stories"]

for story in stories:
    print(f"📖 {story['title']}")
    print(f"📚 Morals: {', '.join(story['morals'])}")
    
    voice_info = story.get('voice_metadata', {})
    print(f"🎤 Voice: {voice_info.get('voice_name', 'Unknown')}")
    print(f"🔊 Cloned: {voice_info.get('is_cloned', False)}")
    print()
```

### Using JavaScript/TypeScript
```typescript
const response = await fetch(
  'https://your-api.com/stories/user/stories?limit=5',
  {
    headers: { 'Authorization': `Bearer ${token}` }
  }
);

const { stories } = await response.json();

stories.forEach((story: any) => {
  console.log(`📖 ${story.title}`);
  console.log(`📚 Morals: ${story.morals?.join(', ') || 'None'}`);
  
  const voice = story.voice_metadata || {};
  console.log(`🎤 Voice: ${voice.voice_name || 'Unknown'}`);
  console.log(`🔊 Cloned: ${voice.is_cloned ? 'Yes' : 'No'}`);
});
```

---

**See Also:**
- [Complete Metadata Documentation](./STORY_METADATA.md)
- [Quick Reference Guide](./QUICK_REFERENCE.md)
- [Language Support](../language-support/README.md)

---

## 📸 Story Generation with Reference Images

### Overview

You can include up to **2 reference images** in your story generation request to guide character appearance and maintain visual consistency. Reference images help the AI generate story illustrations that match specific faces, people, or pets.

### How It Works

1. **Upload Reference Images** first using `/reference-images/upload` (max 5 per user)
2. **Select up to 2 reference images** when generating a story
3. **Pass reference_image_ids** in the story generation request
4. **AI uses these images** as visual guidance for character illustrations

### Request Format

**Endpoint:** `POST /stories/generate`

**Request Body:**
```json
{
  "firebase_token": "YOUR_FIREBASE_TOKEN",
  "child_name": "Emma",
  "child_age": 6,
  "morals": ["courage", "friendship"],
  "story_length": "medium",
  "art_style": "magical",
  "dimensions": "portrait",
  "language": "english",
  "reference_image_ids": [
    "ref_abc123_1729800000",
    "ref_abc123_1729801000"
  ]
}
```

### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `firebase_token` | string | ✅ | Authentication token |
| `child_name` | string | ✅ | Child's name (or from profile) |
| `child_age` | integer | ❌ | Child's age (or from profile) |
| `morals` | array[string] | ❌ | Story morals (default: ["kindness", "friendship"]) |
| `story_length` | string | ❌ | "short", "medium", "long" (default: "medium") |
| `art_style` | string | ❌ | "magical", "cartoon", "realistic" (default: "magical") |
| `dimensions` | string | ❌ | "portrait", "landscape", "square" (default: "portrait") |
| `language` | string | ❌ | "english", "hindi", "spanish", etc. (default: "english") |
| `reference_image_ids` | array[string] | ❌ | **Up to 2 reference image IDs** |

### Reference Image Processing

When you provide `reference_image_ids`, the backend:

1. **Validates the count**: Maximum 2 reference images per story
2. **Fetches image URLs**: Looks up reference images from user's profile
3. **Validates ownership**: Ensures all IDs belong to the authenticated user
4. **Passes to AI**: Sends image URLs to the image generation model

**Backend Flow:**
```javascript
// 1. User sends reference_image_ids
{
  "reference_image_ids": ["ref_abc123_1729800000", "ref_abc123_1729801000"]
}

// 2. Backend fetches user profile reference images
const userProfile = await getUserProfile(userId);
const availableRefs = {
  "ref_abc123_1729800000": {
    "image_url": "https://storage.../ref_abc123_1729800000.jpg",
    "person_name": "Mom",
    "relation": "parent"
  },
  "ref_abc123_1729801000": {
    "image_url": "https://storage.../ref_abc123_1729801000.jpg",
    "person_name": "Emma",
    "relation": "self"
  }
}

// 3. Backend extracts image URLs
const referenceImageUrls = [
  "https://storage.../ref_abc123_1729800000.jpg",
  "https://storage.../ref_abc123_1729801000.jpg"
]

// 4. Backend passes to SeeDream 4 image generation
{
  "prompt": "Children's book illustration...",
  "image_input": [
    "https://storage.../ref_abc123_1729800000.jpg",
    "https://storage.../ref_abc123_1729801000.jpg"
  ],
  "size": "2K",
  "aspect_ratio": "1:1",
  "enhance_prompt": true
}
```

### Image Generation API Parameters

The reference images are passed to **SeeDream 4** (ByteDance) image generation model with these parameters:

```json
{
  "prompt": "Children's book illustration style, colorful and friendly, high quality digital art. [Visual description]. Character should resemble the reference image(s) provided, maintaining key facial features, hair color, and distinguishing characteristics while adapting to the story context.",
  "image_input": [
    "https://storage.googleapis.com/.../reference_image_1.jpg",
    "https://storage.googleapis.com/.../reference_image_2.jpg"
  ],
  "size": "2K",
  "aspect_ratio": "1:1",
  "enhance_prompt": true,
  "max_images": 1
}
```

**SeeDream 4 Parameters:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| `prompt` | string | Enhanced prompt with style and character instructions |
| `image_input` | array[string] | URLs of 1-2 reference images |
| `size` | "2K" | 2048x2048 pixels (optimal balance) |
| `aspect_ratio` | "1:1" | Square format for consistency |
| `enhance_prompt` | true | AI enhances prompt for better results |
| `max_images` | 1 | Generate 1 image per scene |

### Complete Example

```javascript
// Step 1: Get user's reference images
const profile = await fetch(
  `${API_BASE_URL}/users/profile?firebase_token=${token}`
);
const profileData = await profile.json();

console.log('Available reference images:');
profileData.profile.reference_images.forEach(img => {
  console.log(`- ${img.person_name} (${img.relation}): ${img.reference_image_id}`);
});

// Step 2: Select up to 2 reference images
const selectedReferenceIds = [
  'ref_abc123_1729800000', // Mom
  'ref_abc123_1729802000'  // Emma
];

// Step 3: Generate story with reference images
const storyRequest = {
  firebase_token: token,
  child_name: 'Emma',
  child_age: 6,
  morals: ['courage', 'friendship'],
  story_length: 'medium',
  art_style: 'magical',
  dimensions: 'portrait',
  language: 'english',
  reference_image_ids: selectedReferenceIds
};

const response = await fetch(`${API_BASE_URL}/stories/generate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(storyRequest)
});

const result = await response.json();
console.log('Story generation started:', result.story_id);
```

### Success Response

```json
{
  "success": true,
  "message": "Story generation started! Connect via WebSocket to receive real-time updates.",
  "story_id": "story_xyz789",
  "job_id": "job_abc123",
  "status": "processing",
  "estimated_completion_time": "60-140 seconds",
  "websocket_endpoint": "/ws/stories/YOUR_FIREBASE_TOKEN",
  "tracking_method": "background_service_with_websocket_notifications"
}
```

### Error Responses

```json
// 400 - Too many reference images
{
  "detail": "Maximum 2 reference images allowed per story"
}

// 404 - Reference image not found
{
  "detail": "Reference image(s) not found for ID(s): ref_xyz_invalid"
}

// 400 - Missing child_name
{
  "detail": "child_name is required. Please provide it in the request or set up your child's profile first."
}

// 401 - Invalid token
{
  "detail": "Invalid Firebase token"
}
```

### Constraints & Limits

- **Maximum reference images per story:** 2
- **Maximum reference images per user:** 5
- **Reference images must be uploaded first** via `/reference-images/upload`
- **Reference images must belong to the authenticated user**
- **Invalid IDs will cause a 404 error** with list of missing IDs
- **Images are automatically resized** to 2048x2048 for processing

### Use Cases

#### 1. Generate Story with Child's Photo

```javascript
// Upload child's photo
const childPhoto = await uploadReferenceImage(
  imageFile,
  'Emma',
  'self',
  token
);

// Generate story with child's likeness
await generateStory({
  reference_image_ids: [childPhoto.reference_image_id],
  child_name: 'Emma',
  morals: ['courage']
});
```

#### 2. Generate Story with Parent and Child

```javascript
// Get reference images from profile
const profile = await getProfile(token);
const momRef = profile.reference_images.find(img => img.relation === 'parent');
const childRef = profile.reference_images.find(img => img.relation === 'self');

// Generate story with both
await generateStory({
  reference_image_ids: [
    momRef.reference_image_id,
    childRef.reference_image_id
  ],
  child_name: 'Emma',
  morals: ['family', 'love']
});
```

#### 3. Generate Story with Pet

```javascript
const petRef = profile.reference_images.find(img => img.relation === 'pet');
const childRef = profile.reference_images.find(img => img.relation === 'self');

await generateStory({
  reference_image_ids: [
    childRef.reference_image_id,
    petRef.reference_image_id
  ],
  child_name: 'Emma',
  morals: ['friendship', 'responsibility']
});
```

### React Component Example

```javascript
import { useState, useEffect } from 'react';

const StoryGeneratorWithReferences = ({ firebaseToken }) => {
  const [profile, setProfile] = useState(null);
  const [selectedRefs, setSelectedRefs] = useState([]);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    const response = await fetch(
      `${API_BASE_URL}/users/profile?firebase_token=${firebaseToken}`
    );
    const data = await response.json();
    setProfile(data.profile);
  };

  const toggleReference = (refId) => {
    if (selectedRefs.includes(refId)) {
      setSelectedRefs(selectedRefs.filter(id => id !== refId));
    } else if (selectedRefs.length < 2) {
      setSelectedRefs([...selectedRefs, refId]);
    } else {
      alert('Maximum 2 reference images allowed');
    }
  };

  const generateStory = async () => {
    if (!profile?.child?.name) {
      alert('Please set up your child profile first');
      return;
    }

    setGenerating(true);
    try {
      const response = await fetch(`${API_BASE_URL}/stories/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          firebase_token: firebaseToken,
          child_name: profile.child.name,
          child_age: profile.child.age,
          morals: ['courage', 'friendship'],
          story_length: 'medium',
          art_style: 'magical',
          reference_image_ids: selectedRefs
        })
      });

      const result = await response.json();
      console.log('Story started:', result.story_id);
      // Navigate to story generation screen...
    } catch (error) {
      alert('Failed to generate story: ' + error.message);
    } finally {
      setGenerating(false);
    }
  };

  if (!profile) return <div>Loading...</div>;

  return (
    <div>
      <h2>Select Reference Images (max 2)</h2>
      <div className="reference-grid">
        {profile.reference_images.map(img => (
          <div
            key={img.reference_image_id}
            className={`ref-card ${
              selectedRefs.includes(img.reference_image_id) ? 'selected' : ''
            }`}
            onClick={() => toggleReference(img.reference_image_id)}
          >
            <img src={img.image_url} alt={img.person_name} />
            <p>{img.person_name}</p>
            <span>{img.relation}</span>
            {selectedRefs.includes(img.reference_image_id) && (
              <div className="check-mark">✓</div>
            )}
          </div>
        ))}
      </div>

      <p>Selected: {selectedRefs.length}/2</p>

      <button onClick={generateStory} disabled={generating}>
        {generating ? 'Generating...' : 'Generate Story'}
      </button>
    </div>
  );
};
```

### Best Practices

1. ✅ **Upload reference images first** before generating stories
2. ✅ **Use high-quality photos** (face clearly visible, good lighting)
3. ✅ **Select relevant images** (e.g., child + parent for family story)
4. ✅ **Maximum 2 images per story** for best results
5. ✅ **Check profile for available images** before requesting
6. ❌ **Don't use blurry or low-quality images**
7. ❌ **Don't select more than 2 images** (will cause error)
8. ❌ **Don't use invalid reference IDs** (check existence first)

### Troubleshooting

**Problem:** "Reference image(s) not found"
- **Solution:** Verify the reference_image_id exists in user's profile
- **Check:** `GET /users/profile` or `GET /reference-images/list`

**Problem:** "Maximum 2 reference images allowed per story"
- **Solution:** Reduce reference_image_ids array to maximum 2 items

**Problem:** Characters don't look like reference images
- **Solution:** Use clearer photos with better lighting and face visibility
- **Note:** AI does artistic interpretation, not exact replication

**Problem:** Story generation fails with reference images
- **Solution:** Try without reference images to isolate the issue
- **Check:** Ensure image URLs are accessible

### Technical Details

**Storage Path:**
```
reference_images/
└── {user_id}/
    ├── ref_{user_id}_{timestamp1}.jpg
    └── ref_{user_id}_{timestamp2}.jpg
```

**Firestore Structure:**
```
users/
└── {user_id}/
    └── reference_images/
        └── {reference_image_id}/
            ├── reference_image_id
            ├── user_id
            ├── person_name
            ├── relation
            ├── image_url
            ├── created_at
            └── updated_at
```

**API Flow:**
```
1. POST /stories/generate with reference_image_ids
2. Backend validates: count ≤ 2
3. Backend fetches: user profile reference_images
4. Backend validates: all IDs exist and belong to user
5. Backend extracts: image_url from each reference
6. Backend passes: URLs to SeeDream 4 as image_input
7. SeeDream 4 generates: images with character consistency
8. Backend saves: story with reference to original IDs
```

---

**See Also:**
- [Reference Images Documentation](../../REFERENCE_IMAGES_IN_PROFILE.md)
- [Complete Metadata Documentation](./STORY_METADATA.md)
- [Quick Reference Guide](./QUICK_REFERENCE.md)
- [Language Support](../language-support/README.md)
