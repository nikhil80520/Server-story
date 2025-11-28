# Parent-Centric Multi-Child Architecture - Complete Implementation Guide

## 📋 Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current Architecture](#current-architecture)
3. [Implementation Status](#implementation-status)
4. [API Reference](#api-reference)
5. [Frontend Integration Guide](#frontend-integration-guide)
6. [Data Migration](#data-migration)
7. [Testing Guide](#testing-guide)
8. [Best Practices](#best-practices)

---

## 📊 Executive Summary

### What This System Does
This server implements a **parent-centric multi-child architecture** where:

✅ **Parents are the main account holders** (authenticated via Firebase)  
✅ **Each parent can create multiple child profiles** (with CRUD operations)  
✅ **Each child has their own settings**: name, age, interests, voice clones, reference images  
✅ **Story generation uses child context**: Just pass `child_id`, server fetches everything  
✅ **Stories are organized by child**: Filter and view stories per child  
✅ **No re-entering child data**: Select a child, and all settings are automatically applied  

### Key Benefits
- **Better UX**: Parents don't re-enter name/age/interests when switching children
- **Better Organization**: Stories are clearly associated with each child
- **More Scalable**: Support families with multiple children seamlessly
- **Child-Specific Voice Clones**: Each child can have their own custom voice
- **Child-Specific Reference Images**: Different children can have different character references

---

## 🏗️ Current Architecture

### Database Structure

```
Firestore:
  users/
    {user_id}/                              // Parent account
      parent: {
        name: string
        email: string
        phone_number: string
        avatar_seed: string
        avatar_style: string
      }
      children_count: number                // Count of active children
      default_child_id: string              // Currently selected child
      account_status: {...}
      created_at: timestamp
      updated_at: timestamp
      
      children/                             // SUB-COLLECTION: Children
        {child_id}/
          child_id: string
          name: string
          age: number
          interests: [string]
          image_url: string
          avatar_seed: string
          avatar_style: string
          avatar_url: string
          system_prompt: string             // Child-specific AI prompt
          is_active: boolean                // For soft deletion
          created_at: timestamp
          updated_at: timestamp
          
          voice_clones/                     // SUB-COLLECTION: Voice clones per child
            {voice_clone_id}/
              voice_clone_id: string
              voice_id: string              // Cartesia voice ID
              voice_name: string
              description: string
              is_active: boolean            // Currently selected voice
              created_at: timestamp
              updated_at: timestamp
          
          reference_images/                 // SUB-COLLECTION: Reference images per child
            {reference_image_id}/
              reference_image_id: string
              person_name: string
              relation: string
              image_url: string
              created_at: timestamp
              updated_at: timestamp
  
  stories/
    {story_id}/
      user_id: string                       // Parent user ID
      child_id: string                      // Associated child ID (NEW)
      title: string
      user_prompt: string
      child_snapshot: {                     // Child data at story creation time
        name: string
        age: number
        interests: [string]
      }
      scenes: [...]
      created_at: timestamp
```

### Core Components

#### 1. **Child Service** (`app/services/child_service.py`)
Manages all child-related operations:
- ✅ Create child profiles
- ✅ Read/Get child data
- ✅ Update child profiles
- ✅ Soft delete children
- ✅ Set default/selected child
- ✅ Get child with statistics (story count, voice clones count, etc.)
- ✅ Generate personalized system prompts per child

#### 2. **Children Router** (`app/routers/children.py`)
RESTful API endpoints for child management:
- ✅ `POST /children` - Create new child
- ✅ `GET /children` - List all children
- ✅ `GET /children/{child_id}` - Get specific child
- ✅ `PUT /children/{child_id}` - Update child
- ✅ `DELETE /children/{child_id}` - Delete child (soft)
- ✅ `POST /children/{child_id}/select` - Set as default
- ✅ `GET /children/{child_id}/stories` - Get child's stories

#### 3. **User Service** (`app/services/user_service.py`)
Updated to support parent-centric model:
- ✅ Creates parent account with first child automatically on registration
- ✅ Tracks `children_count` and `default_child_id`
- ✅ Backward compatible with old single-child structure

#### 4. **Story Models** (`app/models/story.py`)
Enhanced to support child selection:
- ✅ `child_id` parameter in `StoryPromptRequest`
- ✅ If `child_id` not provided, uses default child
- ✅ Child-specific overrides (name, age) still supported for flexibility

---

## ✅ Implementation Status

### Completed Features

#### ✅ Database Schema
- [x] Children sub-collection structure
- [x] Voice clones per child sub-collection
- [x] Reference images per child sub-collection
- [x] Stories linked to child_id
- [x] Parent profile with children tracking

#### ✅ Child Management (CRUD)
- [x] Create child profile with image upload
- [x] Get all children for a parent
- [x] Get specific child details
- [x] Update child profile (name, age, interests, image, etc.)
- [x] Soft delete child
- [x] Set default/selected child
- [x] Get child with statistics (stories, voice clones, reference images count)

#### ✅ Story Integration
- [x] `child_id` parameter in story generation request
- [x] Auto-fetch child data when `child_id` provided
- [x] Use default child if no `child_id` specified
- [x] Store child snapshot in story metadata
- [x] Filter stories by child_id

#### ✅ User Registration
- [x] Creates parent profile
- [x] Automatically creates first child
- [x] Sets first child as default
- [x] Initializes account status

#### ✅ API Endpoints
- [x] All children CRUD endpoints implemented
- [x] Child selection endpoint
- [x] Get stories per child endpoint
- [x] Health check endpoint

### Partially Implemented (Needs Verification)

#### ⚠️ Voice Clones Per Child
The infrastructure is in place (sub-collections exist), but need to verify:
- [ ] Voice clone creation uses child_id
- [ ] Voice clone listing is child-specific
- [ ] Story generation uses child's active voice clone
- [ ] Voice clone deletion per child

#### ⚠️ Reference Images Per Child
Similar to voice clones:
- [ ] Reference image upload uses child_id
- [ ] Reference images stored in child sub-collection
- [ ] Story generation uses child's reference images

### Not Yet Implemented

#### ❌ Data Migration Script
- [ ] Script to migrate existing single-child users to parent-centric model
- [ ] Backup mechanism before migration
- [ ] Rollback capability

#### ❌ Comprehensive Testing
- [ ] Unit tests for ChildService
- [ ] Integration tests for child workflows
- [ ] End-to-end tests for story generation with multiple children

---

## 📚 API Reference

### Authentication
All endpoints require a Firebase authentication token passed as `firebase_token` in request body or query parameters.

---

### 1. Children Management

#### `POST /children` - Create Child Profile

**Request:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1...",
  "name": "Emma",
  "age": 8,
  "gender": "girl",                                        // Optional: "boy", "girl", or omit
  "interests": ["reading", "science", "animals"],
  "image_base64": "data:image/jpeg;base64,/9j/4AAQ...",  // Optional
  "avatar_seed": "emma_custom_seed",                      // Optional
  "avatar_style": "avataaars",                            // Optional
  "system_prompt": "Custom AI prompt for Emma..."         // Optional
}
```

**Response:**
```json
{
  "success": true,
  "message": "Child profile created successfully",
  "child": {
    "child_id": "child_a1b2c3d4e5f6",
    "name": "Emma",
    "age": 8,
    "gender": "girl",
    "interests": ["reading", "science", "animals"],
    "image_url": "https://storage.googleapis.com/...",
    "avatar_seed": "emma_custom_seed",
    "avatar_style": "avataaars",
    "avatar_url": null,
    "system_prompt": "You are a creative children's storyteller...",
    "is_active": true,
    "story_count": 0,
    "voice_clones_count": 0,
    "reference_images_count": 0,
    "created_at": "2025-11-07T10:30:00Z",
    "updated_at": "2025-11-07T10:30:00Z"
  }
}
```

**Important Note about Gender:**
- Including `gender` ensures **consistent character appearance** across all story images
- Without `gender`, the AI may inconsistently render the child as a boy or girl in different scenes
- Valid values: `"boy"`, `"girl"`, or omit for unspecified
- Once set, update using `PUT /children/{child_id}`

---

#### `GET /children` - List All Children

**Request:**
```
GET /children?firebase_token=eyJhbGciOiJSUzI1...
```

**Response:**
```json
{
  "success": true,
  "children": [
    {
      "child_id": "child_a1b2c3d4e5f6",
      "name": "Emma",
      "age": 8,
      "interests": ["reading", "science"],
      "story_count": 12,
      "voice_clones_count": 2,
      "reference_images_count": 3,
      "is_active": true,
      "created_at": "2025-11-01T10:00:00Z",
      "updated_at": "2025-11-07T10:30:00Z"
    },
    {
      "child_id": "child_x9y8z7w6v5u4",
      "name": "Noah",
      "age": 6,
      "interests": ["dinosaurs", "space"],
      "story_count": 8,
      "voice_clones_count": 1,
      "reference_images_count": 2,
      "is_active": true,
      "created_at": "2025-11-02T14:20:00Z",
      "updated_at": "2025-11-06T09:15:00Z"
    }
  ],
  "default_child_id": "child_a1b2c3d4e5f6",
  "total_count": 2
}
```

---

#### `GET /children/{child_id}` - Get Specific Child

**Request:**
```
GET /children/child_a1b2c3d4e5f6?firebase_token=eyJhbGciOiJSUzI1...
```

**Response:**
```json
{
  "success": true,
  "child": {
    "child_id": "child_a1b2c3d4e5f6",
    "name": "Emma",
    "age": 8,
    "interests": ["reading", "science", "animals"],
    "image_url": "https://storage.googleapis.com/...",
    "avatar_seed": "emma_custom_seed",
    "avatar_style": "avataaars",
    "avatar_url": null,
    "system_prompt": "You are a creative children's storyteller creating stories for Emma...",
    "is_active": true,
    "story_count": 12,
    "voice_clones_count": 2,
    "reference_images_count": 3,
    "created_at": "2025-11-01T10:00:00Z",
    "updated_at": "2025-11-07T10:30:00Z"
  }
}
```

---

#### `PUT /children/{child_id}` - Update Child Profile

**Request:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1...",
  "name": "Emma Rose",              // Optional
  "age": 9,                         // Optional
  "interests": ["reading", "math"], // Optional
  "image_base64": "data:image/...", // Optional
  "avatar_seed": "new_seed",        // Optional
  "avatar_style": "avataaars",      // Optional
  "system_prompt": "Updated..."     // Optional
}
```

**Response:**
```json
{
  "success": true,
  "message": "Child profile updated successfully",
  "child": {
    "child_id": "child_a1b2c3d4e5f6",
    "name": "Emma Rose",
    "age": 9,
    "interests": ["reading", "math"],
    // ... updated fields
  }
}
```

---

#### `DELETE /children/{child_id}` - Delete Child (Soft Delete)

**Request:**
```
DELETE /children/child_a1b2c3d4e5f6?firebase_token=eyJhbGciOiJSUzI1...
```

**Response:**
```json
{
  "success": true,
  "message": "Child profile deleted successfully",
  "child_id": "child_a1b2c3d4e5f6"
}
```

**Note:** This is a soft delete - sets `is_active: false`. The child's stories and data remain but are hidden.

---

#### `POST /children/{child_id}/select` - Set Default Child

**Request:**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Child selected successfully",
  "default_child_id": "child_a1b2c3d4e5f6"
}
```

---

#### `GET /children/{child_id}/stories` - Get Child's Stories

**Request:**
```
GET /children/child_a1b2c3d4e5f6/stories?firebase_token=eyJhbGciOiJSUzI1...&limit=20&offset=0
```

**Response:**
```json
{
  "success": true,
  "child_id": "child_a1b2c3d4e5f6",
  "child_name": "Emma",
  "stories": [
    {
      "story_id": "story_abc123",
      "title": "Emma's Space Adventure",
      "user_prompt": "A story about exploring Mars",
      "created_at": "2025-11-07T10:00:00Z",
      "total_scenes": 7,
      "total_duration": 420,
      "status": "completed",
      "thumbnail_url": "https://...",
      // ...
    }
  ],
  "total_count": 12,
  "has_more": false
}
```

---

### 2. Story Generation with Child Context

#### `POST /stories/generate` - Generate Story for Child

**Request (NEW - Recommended):**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1...",
  "child_id": "child_a1b2c3d4e5f6",           // Child to generate for
  "prompt": "A magical adventure in the forest",
  "morals": ["kindness", "bravery"],
  "story_length": "medium",                    // short, medium, long
  "art_style": "magical",
  "language": "english",
  "voice_clone": true,                         // Use child's voice clone
  "reference_image_ids": ["ref_img_123"]       // Use child's reference images
}
```

**Request (Legacy - Still Supported):**
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1...",
  // No child_id = uses default child
  "prompt": "A story about dinosaurs",
  "child_name": "Emma",    // Optional override
  "child_age": 8           // Optional override
}
```

**How It Works:**
1. If `child_id` provided → Fetch that child's data (name, age, interests, system_prompt, voice clone, reference images)
2. If `child_id` not provided → Use `default_child_id` from parent account
3. Optional overrides (`child_name`, `child_age`) still work for flexibility
4. Story is automatically associated with the child

**Response:**
```json
{
  "success": true,
  "story_id": "story_abc123def456",
  "status": "generating",
  "message": "Story generation started for Emma",
  "child_id": "child_a1b2c3d4e5f6",
  "child_name": "Emma",
  "estimated_completion_time": 45,
  "websocket_url": "wss://yourserver.com/ws/story_abc123def456"
}
```

---

### 3. Get Stories with Child Filter

#### `GET /stories` - List Stories (All Children or Filtered)

**Request (All Children):**
```
GET /stories?firebase_token=eyJhbGciOiJSUzI1...&limit=20
```

**Request (Specific Child):**
```
GET /stories?firebase_token=eyJhbGciOiJSUzI1...&child_id=child_a1b2c3d4e5f6&limit=20
```

**Response:**
```json
{
  "success": true,
  "user_id": "firebase_user_123",
  "stories": [
    {
      "story_id": "story_abc123",
      "title": "Emma's Space Adventure",
      "child_id": "child_a1b2c3d4e5f6",
      "child_name": "Emma",
      "created_at": "2025-11-07T10:00:00Z",
      // ...
    },
    {
      "story_id": "story_xyz789",
      "title": "Noah's Dinosaur Discovery",
      "child_id": "child_x9y8z7w6v5u4",
      "child_name": "Noah",
      "created_at": "2025-11-06T15:30:00Z",
      // ...
    }
  ],
  "total_count": 20,
  "has_more": true
}
```

---

## 📱 Frontend Integration Guide

### User Registration Flow

```typescript
// Step 1: Sign up with Firebase
const firebaseToken = await firebaseAuth.signUp(email, password);

// Step 2: Create parent + first child profile
const response = await fetch('/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    firebase_token: firebaseToken,
    parent: {
      name: "Jane Smith",
      email: "jane@example.com",
      phone_number: "+1234567890"
    },
    child: {  // This becomes the FIRST child
      name: "Emma",
      age: 8,
      interests: ["reading", "science", "animals"]
    },
    child_image_base64: base64ImageData,  // Optional
    voice_audio_base64: base64AudioData    // Optional
  })
});

// Response includes parent profile and first child
const { user_id, first_child, default_child_id } = await response.json();
```

---

### Dashboard: Display Children

```typescript
// Fetch all children for the logged-in parent
const response = await fetch(`/children?firebase_token=${firebaseToken}`);
const { children, default_child_id, total_count } = await response.json();

// UI Display
children.forEach(child => {
  console.log(`
    Name: ${child.name}
    Age: ${child.age}
    Stories: ${child.story_count}
    Voice Clones: ${child.voice_clones_count}
    Is Default: ${child.child_id === default_child_id}
  `);
});
```

**Example UI:**
```
┌──────────────────────────────────────┐
│ 👨‍👩‍👧‍👦 My Children                     │
├──────────────────────────────────────┤
│ ┌─────────┐  ┌─────────┐             │
│ │  Emma   │  │  Noah   │  [+ Add]    │
│ │  Age 8  │  │  Age 6  │             │
│ │ 12 📖   │  │ 8 📖    │             │
│ │   ✓     │  │         │             │
│ └─────────┘  └─────────┘             │
└──────────────────────────────────────┘
```

---

### Add New Child

```typescript
const response = await fetch('/children', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    firebase_token: firebaseToken,
    name: "Noah",
    age: 6,
    interests: ["dinosaurs", "space", "building"],
    image_base64: childPhotoBase64  // Optional
  })
});

const { child } = await response.json();
console.log(`Created child: ${child.child_id}`);
```

---

### Switch Active Child

```typescript
// When user taps on a child to select them
const response = await fetch(`/children/${child_id}/select`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    firebase_token: firebaseToken
  })
});

// Now this child is the default for story generation
const { default_child_id } = await response.json();
```

---

### Generate Story for Selected Child

```typescript
// Option 1: Use default child (no child_id needed)
const response = await fetch('/stories/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    firebase_token: firebaseToken,
    // No child_id = uses default_child_id automatically
    prompt: "A magical adventure in the enchanted forest",
    morals: ["kindness", "courage"],
    story_length: "medium"
  })
});

// Option 2: Explicitly specify a child
const response = await fetch('/stories/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    firebase_token: firebaseToken,
    child_id: "child_a1b2c3d4e5f6",  // Generate for Emma specifically
    prompt: "An adventure on Mars"
  })
});
```

**No need to pass name, age, interests - the server fetches them automatically!**

---

### Filter Stories by Child

```typescript
// Get all stories
const allStories = await fetch(`/stories?firebase_token=${firebaseToken}`);

// Get only Emma's stories
const emmaStories = await fetch(
  `/stories?firebase_token=${firebaseToken}&child_id=child_a1b2c3d4e5f6`
);

// Or use the dedicated child endpoint
const emmaStoriesAlt = await fetch(
  `/children/child_a1b2c3d4e5f6/stories?firebase_token=${firebaseToken}`
);
```

**Example UI - Story List with Child Filter:**
```
┌──────────────────────────────────────┐
│ My Stories                            │
├──────────────────────────────────────┤
│ Show: [All Children ▼]                │
│       • All Children                  │
│       • Emma                          │
│       • Noah                          │
│                                       │
│ ┌────────────────────────────────┐   │
│ │ 📖 Emma's Space Adventure      │   │
│ │    For: Emma (8)               │   │
│ │ 📖 Noah's Dinosaur Discovery   │   │
│ │    For: Noah (6)               │   │
│ └────────────────────────────────┘   │
└──────────────────────────────────────┘
```

---

### Update Child Profile

```typescript
// User edits Emma's profile
const response = await fetch(`/children/child_a1b2c3d4e5f6`, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    firebase_token: firebaseToken,
    name: "Emma Rose",  // Updated name
    age: 9,             // Birthday!
    interests: ["reading", "science", "math", "coding"]  // New interest
  })
});

const { child } = await response.json();
console.log(`Updated: ${child.name}, age ${child.age}`);
```

---

### Delete Child Profile

```typescript
// Soft delete - data is preserved but hidden
const response = await fetch(
  `/children/child_a1b2c3d4e5f6?firebase_token=${firebaseToken}`,
  { method: 'DELETE' }
);

const { success, message } = await response.json();
console.log(message);  // "Child profile deleted successfully"
```

---

## 🔄 Data Migration

### Migrating Existing Single-Child Users

**Status:** ❌ Not yet implemented (TODO #4)

For existing users with the old single-child structure, you need to:

1. **Identify old users**: Check for users with a `child` field directly under the user document
2. **Create children sub-collection**: Move the `child` data to `users/{user_id}/children/{child_id}`
3. **Update stories**: Add `child_id` field to all existing stories
4. **Set default child**: Update parent's `default_child_id` and `children_count`

**Migration Script Pseudocode:**
```python
# scripts/migrate_to_parent_centric.py
for user in get_all_users():
    if 'child' in user and 'children' not in user:
        # Old structure - needs migration
        child_data = user['child']
        
        # Create new child in sub-collection
        child_id = create_child_from_legacy(user.id, child_data)
        
        # Update all stories for this user
        update_stories_with_child_id(user.id, child_id)
        
        # Update parent document
        update_parent_metadata(user.id, child_id)
        
        # Mark as migrated
        set_migration_flag(user.id)
```

**We'll implement this in TODO #4.**

---

## 🧪 Testing Guide

### Manual Testing Workflow

#### Test 1: Create Parent and First Child
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "TEST_TOKEN",
    "parent": {
      "name": "Jane Smith",
      "email": "jane@example.com",
      "phone_number": "+1234567890"
    },
    "child": {
      "name": "Emma",
      "age": 8,
      "interests": ["reading", "science"]
    }
  }'
```

#### Test 2: Add Second Child
```bash
curl -X POST http://localhost:8000/children \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "TEST_TOKEN",
    "name": "Noah",
    "age": 6,
    "interests": ["dinosaurs", "space"]
  }'
```

#### Test 3: List All Children
```bash
curl "http://localhost:8000/children?firebase_token=TEST_TOKEN"
```

#### Test 4: Generate Story for Specific Child
```bash
curl -X POST http://localhost:8000/stories/generate \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "TEST_TOKEN",
    "child_id": "child_abc123",
    "prompt": "A magical forest adventure"
  }'
```

#### Test 5: Filter Stories by Child
```bash
curl "http://localhost:8000/stories?firebase_token=TEST_TOKEN&child_id=child_abc123"
```

### Automated Tests (TODO)

**We need to create:**
- Unit tests for `ChildService`
- Integration tests for children CRUD operations
- End-to-end tests for multi-child story generation

**This will be covered in TODO #5.**

---

## 📋 Best Practices

### For Frontend Developers

1. **Always cache the children list**: Fetch once per session, update on changes
2. **Show default child indicator**: Visually mark which child is currently selected
3. **Confirm before deletion**: Soft deletes are safe, but confirm with user
4. **Use default child for quick story generation**: Don't force child selection every time
5. **Display child name in story cards**: Make it clear which child each story is for

### For Backend Developers

1. **Always validate child ownership**: Ensure `child_id` belongs to authenticated parent
2. **Use soft deletes**: Never hard-delete children - set `is_active: false`
3. **Handle missing child_id gracefully**: Fall back to default child
4. **Log child selection changes**: Track which child is being used for analytics
5. **Denormalize child data in stories**: Store child snapshot to preserve historical accuracy

### For System Administrators

1. **Monitor children_count per user**: Track adoption of multi-child feature
2. **Watch for orphaned children**: Children without active stories or parent
3. **Plan for data growth**: More children = more stories = more storage
4. **Backup before migration**: Always backup before running migration scripts

---

## 🚀 Next Steps

### Immediate Priorities (TODO List)

1. ✅ **Documentation** (This document - COMPLETED)
2. ⏳ **Verify voice clones and reference images per child** (TODO #2)
3. ⏳ **Update story service to use child_id** (TODO #3)
4. ⏳ **Create data migration script** (TODO #4)
5. ⏳ **Add comprehensive testing** (TODO #5)

### Future Enhancements

- **Child analytics**: Track which child generates the most stories
- **Child switching UI improvements**: Quick-switch dropdown in story generation
- **Bulk operations**: Archive all stories for a child, export child data
- **Child permissions**: Age-appropriate content filtering per child
- **Shared children**: Support for co-parenting scenarios (future consideration)

---

## 📞 Support & Troubleshooting

### Common Issues

**Issue:** "Child profile not found"
- **Solution**: Verify `child_id` belongs to authenticated parent. Check if child was soft-deleted (`is_active: false`).

**Issue:** Stories not showing child name
- **Solution**: Ensure `child_id` field exists in story document. May need to run migration for old stories.

**Issue:** Default child not being used
- **Solution**: Check `default_child_id` field in parent document. If null, set it using `/children/{child_id}/select`.

**Issue:** Voice clone not working for child
- **Solution**: Verify voice clone is in child's sub-collection, not parent's. Check `is_active: true`.

### Getting Help

- Check the API documentation: `/docs`
- Review the implementation summary: `IMPLEMENTATION_SUMMARY.md`
- See the migration plan: `PARENT_CENTRIC_MIGRATION_PLAN.md`
- Contact the development team

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-07  
**Status:** Complete Implementation Guide ✅  
**Maintainer:** Development Team
