# 🎤 Voice Clone Quick Reference Card

## 📋 Request Format

### Multipart (iOS Recommended)
```bash
-F 'labels={"age":"child","language":"english","accent":"british"}'
-F "remove_background_noise=true"
```

### JSON
```json
{
  "labels": {"age": "child", "language": "english", "accent": "british"},
  "remove_background_noise": true
}
```

---

## 🏷️ Labels Quick Reference

### Age Options
```
child | young | middle_aged | old
```

### Language
```
english (default) | spanish | french | german | italian | portuguese | chinese | japanese | korean
```

### Accents (22 total)
```
🇺🇸 american     🇬🇧 british      🇦🇺 australian   🇨🇦 canadian
🇮🇪 irish        🏴 scottish      🏴 welsh         🇿🇦 south_african
🇳🇿 new_zealand  🇮🇳 indian       🇯🇲 caribbean    

🇪🇸 spanish      🇫🇷 french       🇩🇪 german       🇮🇹 italian
🇷🇺 russian      🇨🇳 chinese      🇯🇵 japanese     

🌍 african       🇪🇺 european     🇦🇪 middle_eastern  ❓ other
```

---

## 🎯 Common Use Cases

### Child Voice (British)
```json
{"age": "child", "language": "english", "accent": "british"}
```

### Adult Voice (American)
```json
{"age": "middle_aged", "language": "english", "accent": "american"}
```

### Just Accent
```json
{"accent": "australian"}
```
*Language defaults to "english"*

---

## 🔇 Background Noise Removal

**Default: `true` (enabled)**

```
✅ Enable: "true" (multipart) or true (JSON)
❌ Disable: "false" (multipart) or false (JSON)
```

**When to disable:**
- Studio-quality recordings
- Professional audio with no background noise
- Already processed/cleaned audio

---

## 📱 iOS Code Snippet

```swift
// Add labels
let labels = ["age": "child", "language": "english", "accent": "british"]
let labelsJSON = try JSONEncoder().encode(labels)
let labelsString = String(data: labelsJSON, encoding: .utf8)!

data.append("--\(boundary)\r\n".data(using: .utf8)!)
data.append("Content-Disposition: form-data; name=\"labels\"\r\n\r\n".data(using: .utf8)!)
data.append("\(labelsString)\r\n".data(using: .utf8)!)

// Add noise removal
data.append("--\(boundary)\r\n".data(using: .utf8)!)
data.append("Content-Disposition: form-data; name=\"remove_background_noise\"\r\n\r\n".data(using: .utf8)!)
data.append("true\r\n".data(using: .utf8)!)
```

---

## 🚀 4 Endpoints Updated

```
POST   /users/voice-clone/create-multipart  ← Recommended
PUT    /users/voice-clone/update-multipart  ← Recommended
POST   /users/voice-clone/create-simple
PUT    /users/voice-clone/update-simple
```

---

## ⚡ Quick Tips

1. **Accent is most important** - Choose carefully for best results
2. **All lowercase** - `"british"` not `"British"`
3. **Optional** - Omit labels to use defaults
4. **Backward compatible** - Old code still works
5. **Test different accents** - Find best match for your audio

---

## 📚 Full Documentation

- `VOICE_CLONE_LABELS_GUIDE.md` - Complete guide with examples
- `API_DOCUMENTATION.md` - Full API reference
- `VOICE_CLONE_UPDATES_SUMMARY.md` - Technical summary

---

**Remember:** Labels and noise removal are **optional enhancements**. Your existing code works without changes!
