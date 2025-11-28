# Features Documentation# Voice Clone Labels Documentation



This directory contains detailed documentation for specific features and capabilities of the ESP32 Storytelling Server.This folder contains comprehensive documentation for the Voice Clone Labels feature implementation.



## 📑 Contents## 📚 Documentation Files



### 🎤 Conversational AI & WebRTC### Quick Start

- **[CONVERSATIONAL_AI_DOCS.md](./CONVERSATIONAL_AI_DOCS.md)** - Complete conversational AI architecture and implementation- **[VOICE_CLONE_QUICK_REFERENCE.md](VOICE_CLONE_QUICK_REFERENCE.md)** - Quick reference card (start here!)

- **[CONVERSATION_AI_API.md](./CONVERSATION_AI_API.md)** - Conversational AI API reference and examples- **[VOICE_CLONE_MULTIPART_REFERENCE.md](VOICE_CLONE_MULTIPART_REFERENCE.md)** - Complete multipart endpoint reference

- **[MOBILE_WEBRTC_GUIDE.md](./MOBILE_WEBRTC_GUIDE.md)** - Mobile WebRTC integration guide for iOS/Android

### Comprehensive Guides

### 🗣️ Voice Cloning- **[VOICE_CLONE_LABELS_GUIDE.md](VOICE_CLONE_LABELS_GUIDE.md)** - Full implementation guide with examples

- **[VOICE_CLONE_LABELS_GUIDE.md](./VOICE_CLONE_LABELS_GUIDE.md)** - Comprehensive guide for voice clone labels (age, language, accent)- **[VOICE_CLONE_API_DOCUMENTATION.md](VOICE_CLONE_API_DOCUMENTATION.md)** - Complete API documentation

- **[VOICE_CLONE_QUICK_REFERENCE.md](./VOICE_CLONE_QUICK_REFERENCE.md)** - Quick reference card for voice cloning

- **[VOICE_CLONE_API_DOCUMENTATION.md](./VOICE_CLONE_API_DOCUMENTATION.md)** - Complete voice clone API documentation### Technical Documentation

- **[VOICE_CLONE_MULTIPART_REFERENCE.md](./VOICE_CLONE_MULTIPART_REFERENCE.md)** - Multipart form-data reference for iOS- **[VOICE_CLONE_UPDATES_SUMMARY.md](VOICE_CLONE_UPDATES_SUMMARY.md)** - Technical implementation summary

- **[UPDATE_COMPLETE.md](UPDATE_COMPLETE.md)** - Update completion summary

### 🌍 Multi-Language Support

- **[LANGUAGE_SUPPORT.md](./LANGUAGE_SUPPORT.md)** - 30+ language story generation with native scripts### Testing & Validation

- **[TEST_RESULTS.md](TEST_RESULTS.md)** - Complete test results

### 📖 Story API References- **[TESTING_COMPLETE.txt](TESTING_COMPLETE.txt)** - Testing summary

- **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** - Quick reference for story API responses- **[IMPLEMENTATION_SUMMARY.txt](IMPLEMENTATION_SUMMARY.txt)** - Implementation overview

- **[RESPONSE_EXAMPLES.md](./RESPONSE_EXAMPLES.md)** - Complete API response examples

- **[STORY_METADATA.md](./STORY_METADATA.md)** - Story metadata structure and fields## 🎯 Feature Overview



## 🎯 Quick Navigation### What's New

- ✅ Labels support (age, language, accent)

### For Voice Clone Implementation- ✅ Background noise removal control

1. Start with [VOICE_CLONE_QUICK_REFERENCE.md](./VOICE_CLONE_QUICK_REFERENCE.md)- ✅ 22 accent options available

2. Read [VOICE_CLONE_LABELS_GUIDE.md](./VOICE_CLONE_LABELS_GUIDE.md) for label details- ✅ Multipart form-data format (recommended)

3. Check [VOICE_CLONE_MULTIPART_REFERENCE.md](./VOICE_CLONE_MULTIPART_REFERENCE.md) for iOS multipart implementation- ✅ Simple JSON format (base64)



### For Conversational AI### Endpoints Updated

1. Read [CONVERSATIONAL_AI_DOCS.md](./CONVERSATIONAL_AI_DOCS.md) for architecture1. `POST /users/voice-clone/create-multipart` - Create with file upload

2. Check [CONVERSATION_AI_API.md](./CONVERSATION_AI_API.md) for API details2. `PUT /users/voice-clone/update-multipart` - Update with file upload

3. Follow [MOBILE_WEBRTC_GUIDE.md](./MOBILE_WEBRTC_GUIDE.md) for mobile integration3. `POST /users/voice-clone/create-simple` - Create with base64

4. `PUT /users/voice-clone/update-simple` - Update with base64

### For Multi-Language Stories

1. Read [LANGUAGE_SUPPORT.md](./LANGUAGE_SUPPORT.md) for supported languages## 🚀 Quick Example

2. Use API examples to generate stories in different languages

### Multipart Format (Recommended)

### For Story API Integration```bash

1. Check [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) for quick API overviewcurl -X POST "https://your-api.com/users/voice-clone/create-multipart" \

2. Review [RESPONSE_EXAMPLES.md](./RESPONSE_EXAMPLES.md) for sample responses  -F "firebase_token=YOUR_TOKEN" \

3. Understand [STORY_METADATA.md](./STORY_METADATA.md) for data structure  -F "voice_name=Millie's Voice" \

  -F 'labels={"age":"child","accent":"british"}' \

---  -F "remove_background_noise=true" \

  -F "audio_file=@voice.wav"

**Parent Documentation**: [../README.md](../README.md)```


### Simple JSON Format (Base64)
```bash
curl -X POST "https://your-api.com/users/voice-clone/create-simple" \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_token": "YOUR_TOKEN",
    "voice_name": "Millie'\''s Voice",
    "audio_base64": "BASE64_DATA",
    "audio_format": "wav",
    "labels": {"age": "child", "accent": "british"},
    "remove_background_noise": true
  }'
```

## 🌍 All 22 Available Accents

**English:** american, british, australian, canadian, irish, scottish, welsh, south_african, new_zealand, indian, caribbean

**Other:** spanish, french, german, italian, russian, chinese, japanese, african, european, middle_eastern, other

## 📝 Label Options

- **Age:** child | young | middle_aged | old
- **Language:** english (default) | spanish | french | german | italian | ...
- **Accent:** (see 22 options above)

## ✅ Status

- **Implementation:** Complete
- **Testing:** All tests passed
- **Documentation:** Complete
- **Backward Compatibility:** Maintained
- **Ready for:** Production deployment

## 📞 Support

For questions or issues, check the comprehensive guides above or review server logs for detailed error messages.

---

**Last Updated:** October 12, 2025  
**Version:** 1.0  
**Status:** 🟢 Production Ready
