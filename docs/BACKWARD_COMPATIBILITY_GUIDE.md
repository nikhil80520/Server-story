# Backward Compatibility Guide

**Date:** November 8, 2025  
**API Version:** 3.0.0

---

## Overview

This document ensures the Storyteller API maintains full backward compatibility with existing clients while supporting the new parent-centric child management features.

---

## Key Changes in v3.0.0

### New Features
1. **Multi-Child Support**: Parents can now manage multiple child profiles
2. **Child-Specific Stories**: Stories are associated with specific children
3. **Default Child Selection**: Each parent has a default child for quick story generation

### Backward Compatibility Guarantees
✅ **All legacy endpoints continue to work**  
✅ **All legacy request formats accepted**  
✅ **No breaking changes to existing clients**  
✅ **Automatic migration of single-child data**

---

## Migration Strategies

### 1. Story Generation Endpoint

#### Legacy Request Format (Still Supported ✅)

```json
POST /stories/generate
{
  "firebase_token": "...",
  "prompt": "A story about a brave princess",
  "child_name": "Emma",
  "child_age": 7,
  "story_length": "medium",
  "art_style": "magical"
}
```

**Behavior:**
- ✅ Works exactly as before
- System auto-populates `child_name` and `child_age` from user profile if not provided
- If user has no child profile, uses provided values or defaults
- Story is saved with optional `child_id` linkage

#### New Request Format (Recommended)

```json
POST /stories/generate
{
  "firebase_token": "...",
  "child_id": "child_xyz789",
  "prompt": "A story about a brave princess",
  "story_length": "medium",
  "art_style": "magical"
}
```

**Behavior:**
- Uses specified child's profile data
- Overrides from request take precedence
- Story is explicitly linked to the child

---

### 2. User Profile Data Structure

#### Legacy Profile (Still Supported ✅)

```json
{
  "user_id": "user_abc123",
  "parent_name": "John Doe",
  "child": {
    "name": "Emma",
    "age": 7,
    "gender": "female",
    "interests": ["reading", "adventure"]
  }
}
```

**Behavior:**
- ✅ Still recognized and used
- If `default_child_id` is not set, uses this data
- New stories automatically use this child data
- System can auto-migrate to new format on next update

#### New Profile Format (Recommended)

```json
{
  "user_id": "user_abc123",
  "parent_name": "John Doe",
  "default_child_id": "child_xyz789",
  "children": [
    {
      "child_id": "child_xyz789",
      "name": "Emma",
      "age": 7,
      "gender": "female",
      "interests": ["reading", "adventure"]
    }
  ]
}
```

---

### 3. Story Metadata

#### Legacy Story (No child_id)

```json
{
  "story_id": "story_123",
  "user_id": "user_abc123",
  "title": "The Brave Princess",
  "created_at": "2025-01-01T12:00:00Z"
}
```

**Behavior:**
- ✅ Still fully supported
- Can be retrieved and played
- Appears in user's story list
- No child association shown in UI

#### New Story Format

```json
{
  "story_id": "story_456",
  "user_id": "user_abc123",
  "child_id": "child_xyz789",
  "child_snapshot": {
    "name": "Emma",
    "age": 7
  },
  "title": "Emma's Adventure",
  "created_at": "2025-11-08T12:00:00Z"
}
```

**Behavior:**
- Story linked to specific child
- Child's name/age at time of creation preserved
- Can filter stories by child

---

## Automatic Data Migration

### How It Works

The system automatically handles data migration without user intervention:

#### 1. Profile Access
```python
# When user profile is accessed
user_profile = get_user_profile(user_id)

# System checks:
if user_profile.get('child') and not user_profile.get('default_child_id'):
    # Legacy single-child profile detected
    # Use this data for story generation
    child_data = user_profile['child']
```

#### 2. Story Generation
```python
# Resolution order for child data:
1. Explicit child_id in request
2. User's default_child_id from profile
3. Legacy single child from user_profile['child']
4. Request parameters (child_name, child_age)
5. Defaults (name="Child", age=6)
```

#### 3. Story Retrieval
```python
# Stories without child_id still appear in lists
# Filter /children/{child_id}/stories returns only that child's stories
# Filter /stories/user/stories returns all stories (backward compatible)
```

---

## Client Migration Paths

### Path 1: No Changes Required ✅

**For clients that:**
- Don't need multi-child support
- Already pass `child_name` and `child_age`
- Don't filter by child

**Action:** None! Continue using existing code.

```typescript
// This still works perfectly
await fetch('/stories/generate', {
  method: 'POST',
  body: JSON.stringify({
    firebase_token: token,
    prompt: "A story about adventure",
    child_name: "Emma",
    child_age: 7
  })
});
```

---

### Path 2: Gradual Migration (Recommended)

**Phase 1: Add child_id to requests (Optional)**
```typescript
// Start passing child_id when available
const defaultChildId = userProfile.default_child_id;

await fetch('/stories/generate', {
  method: 'POST',
  body: JSON.stringify({
    firebase_token: token,
    child_id: defaultChildId, // NEW: Optional
    prompt: "A story about adventure"
  })
});
```

**Phase 2: Use children endpoints (Optional)**
```typescript
// Fetch children list
const children = await fetch('/children', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Generate story for specific child
await generateStory(selectedChildId, prompt);
```

**Phase 3: Full multi-child UI (Optional)**
```typescript
// Implement child selection UI
// Filter stories by child
// Manage multiple child profiles
```

---

### Path 3: Full Feature Adoption

**For clients that want:**
- Multi-child support
- Child-specific story filtering
- Enhanced profile management

**Implementation:**
```typescript
// 1. Load all children
const childrenData = await fetch('/children');

// 2. Let user select child
const selectedChild = showChildSelector(childrenData.children);

// 3. Generate story for selected child
await fetch('/stories/generate', {
  method: 'POST',
  body: JSON.stringify({
    firebase_token: token,
    child_id: selectedChild.child_id,
    prompt: userPrompt
  })
});

// 4. Filter stories by child
const childStories = await fetch(`/children/${selectedChild.child_id}/stories`);
```

---

## Testing Backward Compatibility

### Test Case 1: Legacy Client (No child_id)

```bash
# Request without child_id
curl -X POST https://api.storyteller.app/stories/generate \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "...",
    "prompt": "A story about courage",
    "child_name": "Alex",
    "child_age": 6
  }'

# Expected: ✅ Success
# Story generated with provided child data
# child_id: null (or default child if profile exists)
```

### Test Case 2: Legacy Client with Old Profile

```bash
# User profile has old single-child format
{
  "child": {
    "name": "Emma",
    "age": 7
  }
}

# Request without child_name
curl -X POST https://api.storyteller.app/stories/generate \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "...",
    "prompt": "A story about adventure"
  }'

# Expected: ✅ Success
# System uses Emma (age 7) from legacy profile
```

### Test Case 3: New Client with child_id

```bash
# Request with explicit child_id
curl -X POST https://api.storyteller.app/stories/generate \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "...",
    "child_id": "child_xyz789",
    "prompt": "A story about friendship"
  }'

# Expected: ✅ Success
# Story linked to specific child
# Uses child's profile data
```

### Test Case 4: Retrieve Old Stories

```bash
# Fetch stories created before child_id feature
curl https://api.storyteller.app/stories/user/stories \
  -H "Authorization: Bearer ..."

# Expected: ✅ Success
# All stories returned (old and new)
# Old stories show no child association
```

---

## API Endpoint Compatibility Matrix

| Endpoint | Legacy Client | New Client | Notes |
|----------|--------------|------------|-------|
| `POST /stories/generate` | ✅ Full | ✅ Full | Auto-populates child data |
| `GET /stories/user/stories` | ✅ Full | ✅ Full | Returns all user stories |
| `GET /stories/{story_id}` | ✅ Full | ✅ Full | Works for any story |
| `GET /stories/details/{story_id}` | ✅ Full | ✅ Full | Works for any story |
| `DELETE /stories/delete/{story_id}` | ✅ Full | ✅ Full | Works for any story |
| `POST /children` | ⚠️ N/A | ✅ Full | New endpoint |
| `GET /children` | ⚠️ N/A | ✅ Full | New endpoint |
| `GET /children/{child_id}/stories` | ⚠️ N/A | ✅ Full | New endpoint |

**Legend:**
- ✅ Full: Complete functionality
- ⚠️ N/A: Endpoint didn't exist in legacy version
- ❌ Limited: Reduced functionality (none in this case)

---

## Common Migration Scenarios

### Scenario 1: ESP32 Device (Legacy)

**Situation:** Hardware device with fixed firmware

**Solution:**
```python
# Device continues sending:
{
  "firebase_token": "...",
  "prompt": "bedtime story",
  "child_name": "stored_name",
  "child_age": stored_age
}

# Server handles it perfectly ✅
# No device update needed
```

---

### Scenario 2: React Native App (Gradual)

**Phase 1:** No changes
```typescript
// App works as-is
generateStory(token, prompt, childName, childAge)
```

**Phase 2:** Add default child
```typescript
// Start using default child if available
const profile = await getUserProfile();
generateStory(token, prompt, profile.default_child_id)
```

**Phase 3:** Full multi-child
```typescript
// Add child management screens
const children = await getChildren();
selectChild(children[0]);
generateStory(token, prompt, selectedChild.child_id)
```

---

### Scenario 3: Web Dashboard (Full Upgrade)

**Immediate adoption:**
```typescript
// Implement full children management
- Child CRUD operations
- Child selection UI
- Story filtering by child
- Analytics per child
```

---

## Data Consistency Guarantees

### 1. Story Data Integrity

- ✅ Stories without `child_id` remain accessible
- ✅ Stories with `child_id` maintain child association even if child deleted
- ✅ `child_snapshot` preserves child data at story creation time

### 2. Profile Data Safety

- ✅ Legacy single-child profile never deleted automatically
- ✅ Both old and new format coexist
- ✅ System prefers new format but falls back to old

### 3. Migration Rollback

- ✅ Can disable child features without data loss
- ✅ Legacy endpoints remain functional
- ✅ No irreversible data transformations

---

## Monitoring & Alerts

### Track Usage Patterns

```python
# Log which format clients use
if request.child_id:
    metrics.increment('story.generate.new_format')
else:
    metrics.increment('story.generate.legacy_format')
```

### Migration Progress

```python
# Track profile format distribution
users_with_children = count_users_with_children_array()
users_with_legacy = count_users_with_single_child()
migration_percentage = users_with_children / total_users * 100
```

---

## Summary

### Backward Compatibility Status: ✅ FULL

**All legacy clients continue working without modification**

### Migration Timeline

- **Immediate:** All endpoints backward compatible
- **Optional:** Clients can adopt new features gradually
- **No Deadline:** Legacy format supported indefinitely

### Breaking Changes

**None.** All changes are additive and backward compatible.

---

## Support & Documentation

**For Client Developers:**
- Legacy endpoints documented
- Migration guides provided
- Example code for all scenarios

**For Backend:**
- Automatic data format handling
- Graceful fallbacks
- Comprehensive logging

---

**Last Updated:** November 8, 2025  
**Compatibility:** v2.x → v3.0.0 (Fully Compatible ✅)
