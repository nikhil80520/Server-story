# 🌍 Multi-Language Story Generation

This server supports story generation in 30+ languages with native script support for non-Latin languages.

## Features

✅ **30+ Languages Supported**: English, Hindi, Spanish, French, Arabic, Chinese, Japanese, Korean, and more  
✅ **Native Script Generation**: Stories generated in native scripts (Devanagari, Arabic, Chinese characters, etc.)  
✅ **Text-to-Speech Ready**: Native scripts ensure proper pronunciation for TTS systems  
✅ **Voice Cloning**: Automatic voice cloning enabled by default  
✅ **Multi-Language Audio**: ElevenLabs multilingual support with language-specific pronunciation

## API Usage

### Generate Story in Any Language

```bash
POST /stories/generate
```

**Request Body:**
```json
{
  "firebase_token": "YOUR_TOKEN",
  "child_name": "राज",
  "child_age": 6,
  "morals": ["courage", "friendship"],
  "story_length": "short",
  "language": "hindi",
  "prompt": "A brave boy in a magical forest"
}
```

**Response:**
```json
{
  "story_id": "story_xxxxx",
  "title": "राज और जादुई जंगल",
  "language": "hindi",
  "use_cloned_voice": true,
  "morals": ["courage", "friendship"],
  "voice_metadata": {
    "voice_id": "xyz123abc456",
    "voice_name": "Mom's Voice",
    "is_cloned": true,
    "language": "hindi"
  },
  "scenes": [
    {
      "scene_number": 1,
      "text": "राज एक बहादुर लड़का था...",
      "audio_url": "https://...",
      "image_url": "https://..."
    }
  ]
}
```

> **📚 For complete details on story metadata including voice information and morals, see [Story Metadata Documentation](../api/STORY_METADATA.md)**

## Supported Languages

### Non-Latin Scripts (15 languages)
Stories generated in native scripts with enhanced language instructions:

- **Hindi** (हिंदी) - Devanagari script
- **Arabic** (العربية) - Arabic script
- **Chinese** (中文) - Chinese characters
- **Japanese** (日本語) - Hiragana/Katakana/Kanji
- **Korean** (한국어) - Hangul
- **Thai** (ไทย) - Thai script
- **Bengali** (বাংলা) - Bengali script
- **Tamil** (தமிழ்) - Tamil script
- **Telugu** (తెలుగు) - Telugu script
- **Gujarati** (ગુજરાતી) - Gujarati script
- **Punjabi** (ਪੰਜਾਬੀ) - Gurmukhi script
- **Urdu** (اردو) - Urdu script
- **Marathi** (मराठी) - Devanagari script
- **Russian** (Русский) - Cyrillic script
- **Greek** (Ελληνικά) - Greek alphabet

### Latin Scripts (15+ languages)
Stories generated in Latin-based languages:

- English, Spanish, French, German, Italian, Portuguese
- Dutch, Swedish, Norwegian, Danish, Finnish, Polish
- Romanian, Turkish, Indonesian, and more

## Language Parameter

The `language` parameter (default: `"english"`) controls:

1. **Story Text**: Generated in the specified language using native script
2. **Audio Generation**: TTS uses appropriate language code for pronunciation
3. **Voice Selection**: ElevenLabs multilingual model with language-specific settings

## Implementation Details

### System Prompt Priority

Language instructions are placed **FIRST** in the system prompt to ensure they take priority over any user-specific prompts:

```python
# Language instructions come FIRST
enhanced_system_prompt = f"{script_instructions}\n\n{system_prompt}"
```

This guarantees that:
- Non-Latin languages generate text in native scripts
- English/romanized text is not mixed with native scripts
- Text-to-speech systems receive properly formatted text

### Voice Cloning

Voice cloning is **enabled by default**:

```python
voice_clone: Optional[bool] = True  # Default
```

Users with cloned voices will automatically use them without specifying the parameter.

### ElevenLabs Integration

Audio generation uses:
- **Model**: `eleven_multilingual_v2`
- **Language Codes**: Automatic mapping from language name to ElevenLabs language code
- **Voice Consistency**: Enabled for multi-scene stories

## Testing

### Quick Test

```bash
# Test Hindi story generation
.venv/bin/python tests/language/test_multilanguage.py
```

### Test Results

All languages tested successfully:
- ✅ Hindi (Devanagari): Perfect native script generation
- ✅ Spanish: Proper Spanish text
- ✅ French: Correct French grammar and vocabulary
- ✅ Arabic: Right-to-left Arabic script
- ✅ Chinese: Traditional/Simplified Chinese characters
- ✅ Japanese: Mixed Hiragana/Katakana/Kanji

## Documentation

Detailed documentation available in `docs/language-support/`:

- **BUGS_FIXED.md**: Complete list of bug fixes
- **ROOT_CAUSE_ANALYSIS.md**: Investigation findings
- **FINAL_FIXES_SUMMARY.md**: Technical implementation details
- **TESTING_INSTRUCTIONS.md**: How to test the feature
- **QUICK_FIX_REFERENCE.md**: Quick reference card

## Examples

### Hindi Story
```json
{
  "title": "राज और जादुई जंगल",
  "scenes": [{
    "text": "एक बार की बात है, राज नाम का एक बहादुर लड़का था..."
  }]
}
```

### Spanish Story
```json
{
  "title": "Raj y el Bosque Mágico",
  "scenes": [{
    "text": "Había una vez un niño valiente llamado Raj..."
  }]
}
```

### Chinese Story
```json
{
  "title": "勇敢的小男孩和魔法森林",
  "scenes": [{
    "text": "在一个阳光明媚的早晨，六岁的小男孩拉杰决定去探索附近的魔法森林..."
  }]
}
```

## Troubleshooting

### Story Generated in Wrong Language

**Symptom**: Story generated in English despite setting `language: "hindi"`

**Cause**: User's Firebase profile contains a custom `system_prompt` that conflicts with language instructions

**Solution**: Language instructions are now placed FIRST in the system prompt to take priority

### Voice Cloning Not Working

**Symptom**: Default voice used instead of user's cloned voice

**Cause**: `voice_clone` parameter defaulted to `False`

**Solution**: Now defaults to `True` - voice cloning enabled automatically

## Performance

- **Generation Time**: ~10-30 seconds depending on story length and language
- **API Calls**: 1 OpenAI call per story (parallel scene processing)
- **Audio Generation**: Parallel processing for all scenes
- **Image Generation**: Parallel processing for all scenes

## Future Enhancements

- [ ] Add more languages (Swahili, Vietnamese, etc.)
- [ ] Support for regional dialects
- [ ] Custom pronunciation guides
- [ ] Language-specific illustration styles
- [ ] Cultural adaptation for different regions

---

**Status**: ✅ Production Ready | **Last Updated**: October 2025
