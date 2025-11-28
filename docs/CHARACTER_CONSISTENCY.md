# Character Consistency & Reference Images

## Overview

The story generation system now supports **character consistency** using reference images with AI-generated visual descriptions. This ensures that characters appear visually identical across all story scenes and images.

## Key Features

### 1. Reference Image Management

- **Upload & AI Analysis**: When you upload a reference image, the system automatically generates a detailed visual description (face features, hair, clothing, etc.)
- **Character Metadata**: Each reference includes:
  - `reference_image_id`: Unique identifier
  - `person_name`: Character name (e.g., "Sukhman", "Emma")
  - `relation`: Relationship (e.g., "child", "dad", "mom", "friend", "pet")
  - `ai_description`: AI-generated visual description for consistency
  - `image_url`: Firebase storage URL

### 2. @Mention Support

You can mention characters directly in story prompts using `@name` or `@relation`:

```
Examples:
- "@sukhman goes on an adventure"
- "A story where @dad teaches the child to ride a bike"
- "@emma and @mom bake cookies together"
```

**How it works:**
- System automatically detects `@name` patterns in the prompt
- Matches mentions to reference images by `person_name` or `relation` (case-insensitive)
- Auto-includes matched reference images even if not explicitly listed in `reference_image_ids`

### 3. Per-Scene Character Control

OpenAI generates stories with **per-scene reference tracking**:

```json
{
  "scene_number": 1,
  "text": "Story text in chosen language...",
  "visual_prompt": "Detailed English prompt with consistent character traits...",
  "reference_image_ids": ["ref_abc123", "ref_def456"],
  "emotion": "happy"
}
```

- Each scene lists only the characters **visually depicted** in that scene
- Image generation receives **only the relevant reference images** for that scene
- Ensures accurate face matching and visual consistency

### 4. Consistent Visual Prompts

The system instructs OpenAI to:
- Use AI-generated descriptions from reference images
- Maintain consistent physical traits across all scenes:
  - Hair color, style, length
  - Skin tone and facial features
  - Eye color and shape
  - Clothing colors/patterns
  - Distinctive accessories
- Specify clothing details so characters are recognizable scene-to-scene

## API Usage

### Request Format

```json
{
  "firebase_token": "...",
  "prompt": "@sukhman and @dad go fishing",
  "reference_image_ids": ["ref_abc123", "ref_def456"],
  "child_name": "Sukhman",
  "story_length": "medium",
  "art_style": "watercolor",
  "language": "english"
}
```

### Request Parameters

- `reference_image_ids` (optional): List of reference image IDs to use
  - Maximum 2 reference images per story (configurable via `MAX_STORY_REFERENCE_IMAGES`)
  - System will auto-add any `@mentioned` characters
- `prompt`: Story request with optional `@mentions`
- Other parameters: Standard story generation settings

### Response

Story manifest includes per-scene reference tracking:

```json
{
  "story_id": "story_xyz",
  "title": "Fishing Adventure",
  "scenes": [
    {
      "scene_number": 1,
      "text": "...",
      "visual_prompt": "...",
      "image_url": "https://...",
      "reference_image_ids": ["ref_abc123", "ref_def456"]
    }
  ]
}
```

## Implementation Details

### Story Generation Flow

1. **Reference Resolution**:
   - User provides `reference_image_ids` in request
   - System fetches full metadata (id, name, relation, ai_description, image_url)
   - Parses prompt for `@mentions` and auto-adds matching references

2. **OpenAI Prompt Enhancement**:
   - Injects character consistency block with:
     - List of all reference characters
     - AI-generated visual descriptions
     - Explicit instructions for consistent traits
     - Required output format with `reference_image_ids` per scene

3. **Scene Processing**:
   - OpenAI returns scenes with `reference_image_ids` arrays
   - System maps IDs to URLs: `{"ref_abc123": "https://firebase.com/image1.jpg"}`
   - Each scene's image generation receives **only its listed reference URLs**

4. **Image Generation (SeeDream)**:
   - Receives visual prompt + relevant reference image URLs
   - Face consistency instructions applied automatically
   - Generates images matching reference faces

### Code Architecture

**Key Components:**

- `StoryService._parse_mentions_from_prompt()`: Detects and matches `@mentions`
- `StoryService.generate_story_scenes()`: Builds OpenAI prompt with character consistency block
- `StoryScene.reference_image_ids`: Per-scene reference tracking
- `process_scenes_parallel_optimized()`: Maps per-scene IDs to URLs
- `MediaService.generate_image()`: Receives per-scene reference URLs

**Flow:**
```
Request → Parse @mentions → Fetch metadata → OpenAI (with consistency instructions)
  ↓
Scenes with reference_image_ids → Map IDs to URLs per scene
  ↓
Image generation (per-scene reference URLs) → Consistent visual output
```

## Testing

Run character consistency tests:

```bash
pytest tests/test_character_consistency.py -v
```

Tests cover:
- `@mention` parsing and matching
- Per-scene `reference_image_ids` capture
- Reference ID to URL mapping

## Best Practices

### 1. Reference Image Quality
- Use clear, well-lit photos showing the person's face
- Front-facing or 3/4 angle works best
- Avoid group photos (one person per reference)

### 2. AI Descriptions
- Generated automatically on upload
- Include physical traits, clothing, and distinctive features
- Used by OpenAI to write consistent visual prompts

### 3. Story Prompts
- Use `@name` or `@relation` to mention characters
- Example: "@emma discovers a magic garden with @grandma"
- System auto-includes mentioned characters

### 4. Scene-Level Control
- OpenAI decides which characters appear in each scene
- Only depicted characters get their reference images passed to image generation
- Ensures accurate face matching without confusion

## Limitations

- **Maximum 2 reference images per story** (prevents visual clutter)
- **English-only visual prompts** (for image generation compatibility)
- **Story text in chosen language** (audio/narration language)
- **OpenAI compliance required** (must return `reference_image_ids` per scene)

## Future Enhancements

- Support for 3+ references (with careful prompt engineering)
- Reference image versioning (track changes over time)
- Automatic character relationship inference
- Reference image suggestions based on story themes

## Troubleshooting

**Characters not appearing consistently:**
- Check AI descriptions in reference image metadata
- Verify `reference_image_ids` in scene data
- Ensure visual prompts mention character traits

**@Mentions not working:**
- Verify `person_name` and `relation` in reference metadata
- Check spelling (case-insensitive but must match exactly)
- Ensure reference images exist in user profile

**Images missing reference faces:**
- Check scene's `reference_image_ids` array
- Verify ID-to-URL mapping in logs
- Ensure SeeDream receives correct reference URLs

## Example Workflow

1. **Upload Reference Images**:
```bash
POST /reference-images
{
  "firebase_token": "...",
  "person_name": "Sukhman",
  "relation": "child",
  "image_base64": "..."
}
```

2. **Generate Story with @Mention**:
```bash
POST /stories/generate
{
  "firebase_token": "...",
  "prompt": "@sukhman finds a lost puppy",
  "story_length": "short"
}
```

3. **System Processing**:
   - Detects `@sukhman` mention
   - Finds matching reference: `ref_abc123`
   - Passes AI description to OpenAI
   - OpenAI generates scenes with `reference_image_ids`
   - Image generation uses reference face per scene

4. **Result**:
   - Story with consistent character appearance
   - Sukhman looks identical across all scenes
   - Natural story flow with character involvement

---

**Last Updated**: November 11, 2025  
**Feature Status**: ✅ Production Ready
