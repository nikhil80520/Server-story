# Art Style & Reference Image Updates

## Overview
This document describes the changes made to art styles and reference image handling in the storytelling API.

---

## 1. Art Style Changes

### Updated Art Style Options

The art style system has been updated to use more descriptive and recognizable animation styles:

| **Old Value** | **New Value** | **Description** |
|---------------|---------------|-----------------|
| `magical` | `disney` | Disney animation style - classic, polished, expressive characters |
| `realistic` | `ghibli` | Studio Ghibli style - hand-drawn, natural, atmospheric |
| `cartoon` | `pixar` | Pixar 3D animation style - modern, vibrant, detailed |
| `watercolor` | `watercolors` | Watercolor painting style - soft, artistic, painterly |

### Default Value
- **Old Default**: `magical`
- **New Default**: `disney`

### Image Generation Impact

Art styles are now properly mapped to full style descriptions in image generation:

```python
art_style_map = {
    "disney": "Disney animation style",
    "ghibli": "Studio Ghibli style", 
    "pixar": "Pixar 3D animation style",
    "watercolors": "watercolor painting style"
}
```

These are applied to all image generation prompts sent to SeeDream 4 API.

### Example Prompt Transformation

**Input**: `art_style="ghibli"`

**Generated Prompt**:
```
Children's book illustration, Studio Ghibli style, colorful and friendly, 
high quality digital art. [character description]...
```

---

## 2. Reference Image Age Parameter

### New Feature: Age Storage

Reference images now support an **optional age parameter** to store the age of the person in the image.

### Model Updates

#### ReferenceImageCreate
```python
class ReferenceImageCreate(BaseModel):
    firebase_token: str
    person_name: str
    relation: str  # e.g., "self", "parent", "sibling", "friend", "pet"
    age: Optional[int] = None  # NEW: Age of person in image
    image_base64: str
```

#### ReferenceImageResponse
```python
class ReferenceImageResponse(BaseModel):
    reference_image_id: str
    user_id: str
    person_name: str
    relation: str
    age: Optional[int] = None  # NEW: Age of person
    image_url: str
    ai_description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
```

#### ReferenceImageUpdate
```python
class ReferenceImageUpdate(BaseModel):
    firebase_token: str
    person_name: Optional[str] = None
    relation: Optional[str] = None
    age: Optional[int] = None  # NEW: Can update age
```

---

## 3. API Endpoints

### POST /reference-images/upload

Upload a reference image with file upload (multipart/form-data).

**Request Parameters**:
```
file: UploadFile (required) - Image file
person_name: string (required) - Name of person in image
relation: string (required) - Relation (child, parent, sibling, etc.)
age: integer (optional) - Age of person in image
firebase_token: string (required) - Authentication token
```

**Example (cURL)**:
```bash
curl -X POST "https://api.example.com/reference-images/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@photo.jpg" \
  -F "person_name=Millie" \
  -F "relation=child" \
  -F "age=5" \
  -F "firebase_token=YOUR_TOKEN"
```

**Response**:
```json
{
  "reference_image_id": "ref_user123_1732483200",
  "user_id": "user123",
  "person_name": "Millie",
  "relation": "child",
  "age": 5,
  "image_url": "https://storage.googleapis.com/.../ref_user123_1732483200.jpg",
  "ai_description": null,
  "created_at": "2025-11-24T10:30:00Z",
  "updated_at": "2025-11-24T10:30:00Z"
}
```

---

### POST /reference-images/create

Create a reference image with base64-encoded image data (JSON).

**Request Body**:
```json
{
  "firebase_token": "YOUR_TOKEN",
  "person_name": "Jyn",
  "relation": "parent",
  "age": 35,
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAUA..."
}
```

**Response**:
```json
{
  "reference_image_id": "ref_user123_1732483300",
  "user_id": "user123",
  "person_name": "Jyn",
  "relation": "parent",
  "age": 35,
  "image_url": "https://storage.googleapis.com/.../ref_user123_1732483300.jpg",
  "ai_description": null,
  "created_at": "2025-11-24T10:35:00Z",
  "updated_at": "2025-11-24T10:35:00Z"
}
```

---

### PUT /reference-images/{reference_image_id}

Update reference image metadata (name, relation, age).

**Request Body**:
```json
{
  "firebase_token": "YOUR_TOKEN",
  "person_name": "Millie Grace",
  "relation": "child",
  "age": 6
}
```

**Response**: Same as ReferenceImageResponse with updated values.

---

## 4. Enhanced AI Instructions

### OpenAI Prompt Context

When reference images are provided, OpenAI is now explicitly told that:

1. **Visual prompts are for another AI**: OpenAI knows it's writing prompts for SeeDream 4 (image generation AI), not for humans
2. **Character context is prepended**: Each visual prompt automatically starts with character information
3. **Example**: `"Millie is a 5 year old girl, and Jeannie is a 40 year old woman. [scene description]..."`

### Image Generation Instructions

All image generation requests to SeeDream 4 now include these exact instructions:

```
⚠️ {N} REFERENCE IMAGE(S) PROVIDED - USE THESE FACES AS PRIMARY VISUAL SOURCE!

Analyze the provided reference image carefully and recreate the person with a face 
that closely resembles the sample image. Maintain all key physical attributes — 
including the same skin tone, eye color, hair color, hairstyle, facial structure, 
and overall appearance.

FACE MATCHING (HIGHEST PRIORITY):
• The reference images show the EXACT face(s) that must appear in this scene
• Copy the facial features, structure, and likeness from the reference images precisely
• The face in the reference image is THE TRUTH - match it exactly
• Do NOT invent new facial features - use ONLY what you see in the reference
• Ensure the person remains easily recognizable as the same individual from the reference image

PHYSICAL ATTRIBUTES FROM REFERENCE:
• Skin tone: Copy the exact skin tone from the reference image
• Hair: Match color, texture, style, and length from reference
• Eyes: Match eye color and shape from reference
• Face structure: Copy cheekbones, nose, jawline, face shape
• All physical characteristics must match the reference exactly

SCENE ADAPTATION:
• Keep the SAME FACE from reference in different poses/angles as needed
• You may adjust the pose, body position, and facial expression to make the final image 
  more engaging, friendly, and appealing to young children
• Change clothing, background, and setting as described in text prompt
• But NEVER change the face, skin tone, hair, or core physical features

STYLE AND PRESENTATION:
• The composition, colors, and lighting should all contribute to a warm, cheerful, 
  and visually inviting look suitable for children's content
• Child-safe and emotionally positive presentation
• Image should be child friendly, animated but still resemble the given faces
```

These instructions are appended to **every single image generation request** when reference images are present.

---

## 5. Story Generation API Updates

Get all reference images for the authenticated user.

**Query Parameters**:
```
firebase_token: string (required)
```

**Response**:
```json
{
  "reference_images": [
    {
      "reference_image_id": "ref_user123_1732483200",
      "user_id": "user123",
      "person_name": "Millie",
      "relation": "child",
      "age": 5,
      "image_url": "https://storage.googleapis.com/.../ref_user123_1732483200.jpg",
      "ai_description": null,
      "created_at": "2025-11-24T10:30:00Z",
      "updated_at": "2025-11-24T10:30:00Z"
    }
  ],
  "total": 1,
  "max_allowed": 5
}
```

---

### GET /reference-images/{reference_image_id}

Get a specific reference image by ID.

**Query Parameters**:
```
firebase_token: string (required)
```

**Response**: Single ReferenceImageResponse object.

---

### DELETE /reference-images/{reference_image_id}

Delete a reference image.

**Query Parameters**:
```
firebase_token: string (required)
```

**Response**:
```json
{
  "success": true,
  "message": "Reference image deleted successfully",
  "reference_image_id": "ref_user123_1732483200"
}
```

## 5. Story Generation API Updates

### POST /stories/create

The story generation endpoint now accepts the new art style values and automatically handles character context.

**Request Body Example**:
```json
{
  "firebase_token": "YOUR_TOKEN",
  "child_name": "Millie",
  "child_age": 5,
  "morals": ["sharing", "kindness"],
  "story_length": "medium",
  "art_style": "ghibli",
  "language": "english",
  "reference_image_ids": ["ref_user123_1732483200", "ref_user123_1732483201"]
}
```

**Art Style Options**:
- `disney` - Disney animation style (default)
- `ghibli` - Studio Ghibli style
- `pixar` - Pixar 3D animation style
- `watercolors` - Watercolor painting style

**Automatic Character Context**:
When you provide reference images (e.g., Millie as child, Jeannie as parent), the system automatically:
1. Extracts character names, ages, and genders from reference metadata
2. Builds context string: `"Millie is a 5 year old girl, and Jeannie is a 40 year old woman"`
3. Instructs OpenAI to prepend this to every visual_prompt
4. Example generated prompt: `"Millie is a 5 year old girl, and Jeannie is a 40 year old woman. Millie and Jeannie walk through a magical forest..."`

---

## 6. Database Schema Changes

### Firestore Structure

Reference images are stored at:
```
users/{user_id}/reference_images/{reference_image_id}
```

**Document Structure**:
```javascript
{
  reference_image_id: "ref_user123_1732483200",
  user_id: "user123",
  person_name: "Millie",
  relation: "child",
  age: 5,  // NEW FIELD (optional)
  image_url: "https://storage.googleapis.com/.../ref_user123_1732483200.jpg",
  ai_description: null,
  created_at: Timestamp,
  updated_at: Timestamp
}
```

---

## 6. Migration Notes

### Backward Compatibility

✅ **Fully backward compatible**:
- Old art style values will still work (though not recommended)
- Age field is optional - existing reference images without age will still function
- All existing reference image records remain valid

### Recommended Migration Steps

1. **Update frontend to use new art style values**:
   - Replace `magical` → `disney`
   - Replace `realistic` → `ghibli`
   - Replace `cartoon` → `pixar`
   - Replace `watercolor` → `watercolors`

2. **Add age parameter to reference image uploads** (optional but recommended):
   - Update upload forms to include age field
   - Store age when creating new reference images

3. **Test with new art styles**:
   - Generate stories with each new art style
   - Verify visual consistency across scenes

---

## 7. Example Usage

### Complete Workflow

```javascript
// 1. Upload reference image with age
const formData = new FormData();
formData.append('file', photoFile);
formData.append('person_name', 'Millie');
formData.append('relation', 'child');
formData.append('age', 5);
formData.append('firebase_token', token);

const refImageResponse = await fetch('/reference-images/upload', {
  method: 'POST',
  body: formData
});

const refImage = await refImageResponse.json();
// { reference_image_id: "ref_...", age: 5, ... }

// 2. Create story with new art style
const storyResponse = await fetch('/stories/create', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    firebase_token: token,
    child_name: 'Millie',
    child_age: 5,
    morals: ['sharing', 'kindness'],
    art_style: 'ghibli',  // NEW STYLE VALUE
    reference_image_ids: [refImage.reference_image_id]
  })
});

// 3. Story generated with Studio Ghibli style and Millie's face
```

---

## 8. Testing

### Test Cases

✅ **Art Styles**:
- [ ] Generate story with `disney` style
- [ ] Generate story with `ghibli` style
- [ ] Generate story with `pixar` style
- [ ] Generate story with `watercolors` style
- [ ] Verify style is properly applied in all scene images

✅ **Reference Images with Age**:
- [ ] Upload reference image with age
- [ ] Upload reference image without age (should work)
- [ ] Update reference image age
- [ ] List reference images (age should be included)
- [ ] Generate story with aged reference image

✅ **Backward Compatibility**:
- [ ] Old art style values still work
- [ ] Reference images without age still work
- [ ] Existing stories continue to function

---

## 9. Summary of Changes

### Files Modified

1. **Models**:
   - `app/models/content/story.py` - Updated default art_style to "disney"
   - `app/models/content/reference_image.py` - Added age field to all models

2. **Routers**:
   - `app/routers/content/stories.py` - Updated art_style defaults to "disney"
   - `app/routers/content/reference_images.py` - Added age parameter to upload/create/update endpoints

3. **Services**:
   - `app/services/content/story_service.py` - Updated default art_style
   - `app/services/content/parallel_story_service.py` - Updated default art_style
   - `app/services/content/media_service.py` - Added art style mapping for image generation
   - `app/services/infrastructure/enhanced_background_service.py` - Updated default art_style

### Key Improvements

1. ✨ **Better Art Styles**: More recognizable and descriptive animation styles
2. 📸 **Age Tracking**: Store character age with reference images for better consistency
3. 🎨 **Enhanced Prompts**: Art styles properly mapped to full descriptions in image generation
4. 🔄 **Backward Compatible**: All existing functionality preserved

---

## Questions?

For questions or issues, please refer to:
- Main API documentation: `/docs/API_ENDPOINT_DOCUMENTATION.md`
- Developer guide: `/docs/DEVELOPER_GUIDE.md`
- Character consistency guide: `/docs/CHARACTER_CONSISTENCY.md`
