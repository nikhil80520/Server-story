# Parent-Centric Multi-Child System - Quick Start Guide

## 🚀 TL;DR - What You Need to Know

Your server **already supports multiple children per parent**! Here's what you can do right now:

### ✅ What Works NOW (70% Complete)
1. **Create multiple children** for each parent
2. **Generate stories** by just passing `child_id` (server fetches name/age/interests automatically)
3. **Filter stories** by child
4. **Switch between children** easily
5. **Each child has their own settings** (name, age, interests, system_prompt)

### ⚠️ What Needs Work (30% Remaining)
- Voice clones are NOT yet per-child (still at parent level)
- Reference images are NOT yet per-child (still at parent level)
- Migration script for old users not implemented

---

## 📖 5-Minute Tutorial

### Step 1: Parent Signs Up & Creates First Child

```bash
# Parent registers (creates parent + first child automatically)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "eyJhbGci...",
    "parent": {
      "name": "Jane Smith",
      "email": "jane@example.com",
      "phone_number": "+1234567890"
    },
    "child": {
      "name": "Emma",
      "age": 8,
      "interests": ["reading", "science", "animals"]
    }
  }'

# Response includes:
# - parent profile
# - first_child (Emma)
# - default_child_id = Emma's ID
```

**Result:** ✅ Parent account created with Emma as the first child

---

### Step 2: Add a Second Child

```bash
# Parent adds another child (Noah)
curl -X POST http://localhost:8000/children \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "eyJhbGci...",
    "name": "Noah",
    "age": 6,
    "interests": ["dinosaurs", "space", "building"]
  }'

# Response:
{
  "success": true,
  "message": "Child profile created successfully",
  "child": {
    "child_id": "child_noah_xyz789",
    "name": "Noah",
    "age": 6,
    "interests": ["dinosaurs", "space", "building"],
    "story_count": 0,
    "is_active": true
  }
}
```

**Result:** ✅ Noah added as second child

---

### Step 3: List All Children

```bash
# Get all children for the parent
curl "http://localhost:8000/children?firebase_token=eyJhbGci..."

# Response:
{
  "success": true,
  "children": [
    {
      "child_id": "child_emma_abc123",
      "name": "Emma",
      "age": 8,
      "story_count": 0
    },
    {
      "child_id": "child_noah_xyz789",
      "name": "Noah",
      "age": 6,
      "story_count": 0
    }
  ],
  "default_child_id": "child_emma_abc123",  // Emma is default
  "total_count": 2
}
```

**Result:** ✅ See both children, Emma is default

---

### Step 4: Generate Story for Emma (Default Child)

```bash
# Generate story WITHOUT specifying child_id
# Server automatically uses default_child_id (Emma)
curl -X POST http://localhost:8000/stories/generate \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "eyJhbGci...",
    "prompt": "A magical forest adventure",
    "morals": ["kindness", "courage"],
    "story_length": "medium"
  }'

# Server automatically:
# 1. Uses default_child_id = child_emma_abc123
# 2. Fetches Emma's data (name: "Emma", age: 8, interests: ["reading", "science", "animals"])
# 3. Uses Emma's system_prompt
# 4. Links story to Emma (child_id = child_emma_abc123)
```

**Result:** ✅ Story generated for Emma with her settings, WITHOUT having to pass name/age/interests!

---

### Step 5: Generate Story for Noah (Specific Child)

```bash
# Generate story EXPLICITLY for Noah
curl -X POST http://localhost:8000/stories/generate \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "eyJhbGci...",
    "child_id": "child_noah_xyz789",  // Specify Noah
    "prompt": "A dinosaur discovery adventure"
  }'

# Server automatically:
# 1. Fetches Noah's data (name: "Noah", age: 6, interests: ["dinosaurs", "space", "building"])
# 2. Uses Noah's system_prompt
# 3. Links story to Noah
```

**Result:** ✅ Story generated for Noah with his settings!

---

### Step 6: Switch Default Child to Noah

```bash
# Make Noah the default child
curl -X POST http://localhost:8000/children/child_noah_xyz789/select \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "eyJhbGci..."
  }'

# Response:
{
  "success": true,
  "message": "Child selected successfully",
  "default_child_id": "child_noah_xyz789"
}
```

**Result:** ✅ Noah is now the default child

Now when you generate stories WITHOUT `child_id`, they'll use Noah's settings automatically!

---

### Step 7: View Stories by Child

```bash
# Get ALL stories (both Emma's and Noah's)
curl "http://localhost:8000/stories?firebase_token=eyJhbGci..."

# Response:
{
  "stories": [
    {
      "story_id": "story_001",
      "title": "Emma's Magical Forest",
      "child_id": "child_emma_abc123",
      "child_name": "Emma"
    },
    {
      "story_id": "story_002",
      "title": "Noah's Dinosaur Discovery",
      "child_id": "child_noah_xyz789",
      "child_name": "Noah"
    }
  ]
}

# Get ONLY Emma's stories
curl "http://localhost:8000/stories?firebase_token=eyJhbGci...&child_id=child_emma_abc123"

# Get ONLY Noah's stories
curl "http://localhost:8000/stories?firebase_token=eyJhbGci...&child_id=child_noah_xyz789"
```

**Result:** ✅ Filter stories by child!

---

### Step 8: Update a Child's Profile

```bash
# Emma had a birthday! Update her age
curl -X PUT http://localhost:8000/children/child_emma_abc123 \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "eyJhbGci...",
    "age": 9,
    "interests": ["reading", "science", "animals", "coding"]
  }'

# Response:
{
  "success": true,
  "message": "Child profile updated successfully",
  "child": {
    "child_id": "child_emma_abc123",
    "name": "Emma",
    "age": 9,  // Updated!
    "interests": ["reading", "science", "animals", "coding"]
  }
}
```

**Result:** ✅ Emma's profile updated. Future stories will use age 9!

---

### Step 9: Delete a Child (Soft Delete)

```bash
# Soft delete Noah (keeps data, hides from UI)
curl -X DELETE "http://localhost:8000/children/child_noah_xyz789?firebase_token=eyJhbGci..."

# Response:
{
  "success": true,
  "message": "Child profile deleted successfully",
  "child_id": "child_noah_xyz789"
}

# Noah's stories are preserved but he won't show in children list
# His is_active is set to false
```

**Result:** ✅ Noah soft-deleted (data preserved)

---

## 🎓 Key Concepts

### 1. Default Child
- Every parent has a `default_child_id`
- When generating stories WITHOUT `child_id`, the default child is used
- Change default using `POST /children/{child_id}/select`

### 2. Child-Specific Settings
Each child has:
- ✅ **Name, Age, Interests** - Used in story generation
- ✅ **System Prompt** - Custom AI prompt for this child
- ✅ **Profile Image** - Child's photo
- ✅ **Avatar Settings** - Avatar seed/style
- ⚠️ **Voice Clone** - NOT YET per-child (still at parent level)
- ⚠️ **Reference Images** - NOT YET per-child (still at parent level)

### 3. Automatic Data Fetching
When you pass `child_id` in story generation:
```json
{
  "child_id": "child_emma_abc123",
  "prompt": "Space adventure"
}
```

The server automatically fetches:
- ✅ Child's name ("Emma")
- ✅ Child's age (8)
- ✅ Child's interests (["reading", "science", "animals"])
- ✅ Child's system_prompt
- ⚠️ Parent's voice clone (NOT child-specific yet)
- ⚠️ Parent's reference images (NOT child-specific yet)

**You don't need to pass name, age, or interests anymore!**

---

## 📱 Frontend Integration Checklist

### When Building Your React Native App:

#### ✅ On App Launch / Login
1. Fetch all children: `GET /children`
2. Display children list
3. Highlight default child

#### ✅ Child Selection UI
```typescript
const children = await fetchChildren(firebaseToken);

// UI: Show grid of children
children.forEach(child => {
  renderChildCard({
    name: child.name,
    age: child.age,
    storyCount: child.story_count,
    isDefault: child.child_id === defaultChildId,
    onSelect: () => selectChild(child.child_id)
  });
});
```

#### ✅ Story Generation Screen
```typescript
// Option 1: Use default child (easiest)
await generateStory({
  firebase_token: token,
  // No child_id needed!
  prompt: userInput
});

// Option 2: Use specific child
await generateStory({
  firebase_token: token,
  child_id: selectedChildId,
  prompt: userInput
});
```

#### ✅ Story List with Filter
```typescript
// Dropdown or tabs to filter by child
const selectedChild = "all" | child_id;

if (selectedChild === "all") {
  stories = await fetchStories(token);
} else {
  stories = await fetchStories(token, selectedChild);
}
```

---

## ⚠️ Current Limitations

### What's NOT Ready Yet

#### 1. Voice Clones Per Child
**Current Behavior:**
- Only ONE voice clone per parent
- All children use the same voice

**Desired Behavior (TODO #2):**
- Each child can have multiple voice clones
- Emma has "Emma's Voice", Noah has "Noah's Voice"
- Automatic voice switching when changing children

**Workaround:**
- Use default Cartesia voices for now
- Wait for TODO #2 implementation

#### 2. Reference Images Per Child
**Current Behavior:**
- Only ONE set of reference images per parent
- All children use the same reference images

**Desired Behavior (TODO #3):**
- Each child can have their own reference images
- Emma's reference images show her appearance
- Noah's reference images show his appearance

**Workaround:**
- Use child profile image only
- Wait for TODO #3 implementation

#### 3. Data Migration for Existing Users
**Current Behavior:**
- Old users with single-child structure need manual intervention

**Desired Behavior (TODO #4):**
- Automatic migration script
- Move existing child to children sub-collection
- Update all stories with child_id

**Workaround:**
- New registrations work perfectly
- Old users: manually create children via API

---

## 🧪 Testing Examples

### Test Script: Complete Multi-Child Workflow

```bash
#!/bin/bash

TOKEN="your_firebase_token_here"

echo "1. Register parent with first child (Emma)"
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"firebase_token\": \"$TOKEN\",
    \"parent\": {
      \"name\": \"Jane Smith\",
      \"email\": \"jane@example.com\"
    },
    \"child\": {
      \"name\": \"Emma\",
      \"age\": 8,
      \"interests\": [\"reading\", \"science\"]
    }
  }"

echo "\n2. Add second child (Noah)"
curl -X POST http://localhost:8000/children \
  -H "Content-Type: application/json" \
  -d "{
    \"firebase_token\": \"$TOKEN\",
    \"name\": \"Noah\",
    \"age\": 6,
    \"interests\": [\"dinosaurs\", \"space\"]
  }"

echo "\n3. List all children"
curl "http://localhost:8000/children?firebase_token=$TOKEN"

echo "\n4. Generate story for Emma (default child)"
curl -X POST http://localhost:8000/stories/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"firebase_token\": \"$TOKEN\",
    \"prompt\": \"A magical forest adventure\"
  }"

echo "\n5. Get Emma's child_id and generate story specifically for Noah"
NOAH_ID="child_noah_xyz789"  # Replace with actual ID from step 2
curl -X POST http://localhost:8000/stories/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"firebase_token\": \"$TOKEN\",
    \"child_id\": \"$NOAH_ID\",
    \"prompt\": \"A dinosaur discovery\"
  }"

echo "\n6. Get all stories (both children)"
curl "http://localhost:8000/stories?firebase_token=$TOKEN"

echo "\n7. Get only Noah's stories"
curl "http://localhost:8000/stories?firebase_token=$TOKEN&child_id=$NOAH_ID"

echo "\n8. Switch default to Noah"
curl -X POST "http://localhost:8000/children/$NOAH_ID/select" \
  -H "Content-Type: application/json" \
  -d "{
    \"firebase_token\": \"$TOKEN\"
  }"

echo "\n✅ Multi-child workflow complete!"
```

---

## 📖 Read More

- **Full Implementation Guide:** `PARENT_CENTRIC_IMPLEMENTATION.md`
- **Implementation Status:** `IMPLEMENTATION_STATUS_REPORT.md`
- **Migration Plan:** `PARENT_CENTRIC_MIGRATION_PLAN.md`
- **API Documentation:** http://localhost:8000/docs

---

## 🆘 Common Questions

### Q: Do I need to pass `child_name` and `child_age` when generating stories?
**A:** No! Just pass `child_id` (or nothing to use default child). The server fetches everything automatically.

### Q: How many children can a parent have?
**A:** Unlimited (no enforced limit currently).

### Q: What happens when I delete a child?
**A:** Soft delete - sets `is_active: false`. The child's stories are preserved but the child doesn't show in the list.

### Q: Can I restore a deleted child?
**A:** Not through the API yet, but the data is still there. You can manually update `is_active: true` in Firestore.

### Q: How do I change which child is the default?
**A:** `POST /children/{child_id}/select`

### Q: Will voice clones be per-child in the future?
**A:** Yes! See TODO #2 in the implementation status report.

---

**Happy Multi-Child Storytelling!** 🎉
