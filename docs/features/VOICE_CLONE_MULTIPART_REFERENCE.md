# Voice Clone Multipart Endpoints - Complete Reference

## 📋 Endpoints Overview

### 1. Create Voice Clone - Multipart
**Endpoint:** `POST /users/voice-clone/create-multipart`

**Purpose:** Create a new voice clone using multipart form data (recommended for iOS)

### 2. Update Voice Clone - Multipart
**Endpoint:** `PUT /users/voice-clone/update-multipart`

**Purpose:** Update existing voice clone by replacing it with a new one

---

## 🔑 Request Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `firebase_token` | Form Data (String) | Firebase authentication token |
| `voice_name` | Form Data (String) | Name for the voice clone (e.g., "Millie's Voice") |
| `audio_file` | File Upload | Audio file (WAV, MP3, FLAC, M4A, OGG) - Max 25MB |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `description` | Form Data (String) | `null` | Description for the voice clone |
| `labels` | Form Data (JSON String) | `null` | Voice characteristics (see below) |
| `remove_background_noise` | Form Data (String) | `"true"` | Background noise removal: `"true"` or `"false"` |

---

## 🏷️ Labels Format

Labels must be provided as a **JSON string** (not a dictionary) in the form data.

### Label Structure
```json
{
  "age": "child",
  "language": "english",
  "accent": "british"
}
```

### All Label Options

#### Age Options (4)
- `"child"` - Child voice
- `"young"` - Young adult voice
- `"middle_aged"` - Middle-aged adult voice
- `"old"` - Elderly voice

#### Language Options
- `"english"` (default - used if not specified)
- `"spanish"`
- `"french"`
- `"german"`
- `"italian"`
- `"portuguese"`
- `"polish"`
- `"turkish"`
- `"russian"`
- `"dutch"`
- `"czech"`
- `"arabic"`
- `"chinese"`
- `"japanese"`
- `"korean"`
- `"hindi"`

#### Accent Options (22)

**English Accents (11):**
1. 🇺🇸 `"american"` - American English
2. 🇬🇧 `"british"` - British English
3. 🇦🇺 `"australian"` - Australian English
4. 🇨🇦 `"canadian"` - Canadian English
5. 🇮🇪 `"irish"` - Irish English
6. 🏴 `"scottish"` - Scottish English
7. 🏴 `"welsh"` - Welsh English
8. 🇿🇦 `"south_african"` - South African English
9. 🇳🇿 `"new_zealand"` - New Zealand English
10. 🇮🇳 `"indian"` - Indian English
11. 🇯🇲 `"caribbean"` - Caribbean English

**Other Accents (11):**
12. 🇪🇸 `"spanish"` - Spanish accent
13. 🇫🇷 `"french"` - French accent
14. 🇩🇪 `"german"` - German accent
15. 🇮🇹 `"italian"` - Italian accent
16. 🇷🇺 `"russian"` - Russian accent
17. 🇨🇳 `"chinese"` - Chinese accent
18. 🇯🇵 `"japanese"` - Japanese accent
19. 🌍 `"african"` - General African accent
20. 🇪🇺 `"european"` - General European accent
21. 🇦🇪 `"middle_eastern"` - Middle Eastern accent
22. ❓ `"other"` - Other/unspecified accent

---

## 📱 iOS Implementation Examples

### Example 1: Create Voice Clone with Labels (British Child)

```swift
import Foundation

func createVoiceCloneWithLabels(
    firebaseToken: String,
    voiceName: String,
    audioURL: URL,
    completion: @escaping (Result<[String: Any], Error>) -> Void
) {
    let url = URL(string: "https://your-api.com/users/voice-clone/create-multipart")!
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    
    let boundary = UUID().uuidString
    request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
    
    var data = Data()
    
    // Add firebase_token
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"firebase_token\"\r\n\r\n".data(using: .utf8)!)
    data.append("\(firebaseToken)\r\n".data(using: .utf8)!)
    
    // Add voice_name
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"voice_name\"\r\n\r\n".data(using: .utf8)!)
    data.append("\(voiceName)\r\n".data(using: .utf8)!)
    
    // Add description (optional)
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"description\"\r\n\r\n".data(using: .utf8)!)
    data.append("British child voice for storytelling\r\n".data(using: .utf8)!)
    
    // Add labels (JSON string)
    let labels = ["age": "child", "language": "english", "accent": "british"]
    let labelsJSON = try! JSONEncoder().encode(labels)
    let labelsString = String(data: labelsJSON, encoding: .utf8)!
    
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"labels\"\r\n\r\n".data(using: .utf8)!)
    data.append("\(labelsString)\r\n".data(using: .utf8)!)
    
    // Add remove_background_noise
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"remove_background_noise\"\r\n\r\n".data(using: .utf8)!)
    data.append("true\r\n".data(using: .utf8)!)
    
    // Add audio file
    let audioData = try! Data(contentsOf: audioURL)
    let audioFilename = audioURL.lastPathComponent
    
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"audio_file\"; filename=\"\(audioFilename)\"\r\n".data(using: .utf8)!)
    data.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
    data.append(audioData)
    data.append("\r\n".data(using: .utf8)!)
    
    // Close boundary
    data.append("--\(boundary)--\r\n".data(using: .utf8)!)
    
    request.httpBody = data
    
    let task = URLSession.shared.dataTask(with: request) { responseData, response, error in
        if let error = error {
            completion(.failure(error))
            return
        }
        
        guard let responseData = responseData,
              let json = try? JSONSerialization.jsonObject(with: responseData) as? [String: Any] else {
            completion(.failure(NSError(domain: "Invalid response", code: -1)))
            return
        }
        
        completion(.success(json))
    }
    
    task.resume()
}
```

### Example 2: Update Voice Clone (American Adult)

```swift
func updateVoiceCloneToAmerican(
    firebaseToken: String,
    voiceName: String,
    audioURL: URL,
    completion: @escaping (Result<[String: Any], Error>) -> Void
) {
    let url = URL(string: "https://your-api.com/users/voice-clone/update-multipart")!
    
    var request = URLRequest(url: url)
    request.httpMethod = "PUT"
    
    let boundary = UUID().uuidString
    request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
    
    var data = Data()
    
    // Add firebase_token
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"firebase_token\"\r\n\r\n".data(using: .utf8)!)
    data.append("\(firebaseToken)\r\n".data(using: .utf8)!)
    
    // Add voice_name
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"voice_name\"\r\n\r\n".data(using: .utf8)!)
    data.append("\(voiceName)\r\n".data(using: .utf8)!)
    
    // Add labels for American middle-aged adult
    let labels = ["age": "middle_aged", "language": "english", "accent": "american"]
    let labelsJSON = try! JSONEncoder().encode(labels)
    let labelsString = String(data: labelsJSON, encoding: .utf8)!
    
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"labels\"\r\n\r\n".data(using: .utf8)!)
    data.append("\(labelsString)\r\n".data(using: .utf8)!)
    
    // Add audio file
    let audioData = try! Data(contentsOf: audioURL)
    let audioFilename = audioURL.lastPathComponent
    
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"audio_file\"; filename=\"\(audioFilename)\"\r\n".data(using: .utf8)!)
    data.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
    data.append(audioData)
    data.append("\r\n".data(using: .utf8)!)
    
    // Close boundary
    data.append("--\(boundary)--\r\n".data(using: .utf8)!)
    
    request.httpBody = data
    
    let task = URLSession.shared.dataTask(with: request) { responseData, response, error in
        if let error = error {
            completion(.failure(error))
            return
        }
        
        guard let responseData = responseData,
              let json = try? JSONSerialization.jsonObject(with: responseData) as? [String: Any] else {
            completion(.failure(NSError(domain: "Invalid response", code: -1)))
            return
        }
        
        completion(.success(json))
    }
    
    task.resume()
}
```

### Example 3: Create Without Labels (Minimal)

```swift
func createVoiceCloneMinimal(
    firebaseToken: String,
    voiceName: String,
    audioURL: URL,
    completion: @escaping (Result<[String: Any], Error>) -> Void
) {
    let url = URL(string: "https://your-api.com/users/voice-clone/create-multipart")!
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    
    let boundary = UUID().uuidString
    request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
    
    var data = Data()
    
    // Add firebase_token
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"firebase_token\"\r\n\r\n".data(using: .utf8)!)
    data.append("\(firebaseToken)\r\n".data(using: .utf8)!)
    
    // Add voice_name
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"voice_name\"\r\n\r\n".data(using: .utf8)!)
    data.append("\(voiceName)\r\n".data(using: .utf8)!)
    
    // Add audio file
    let audioData = try! Data(contentsOf: audioURL)
    let audioFilename = audioURL.lastPathComponent
    
    data.append("--\(boundary)\r\n".data(using: .utf8)!)
    data.append("Content-Disposition: form-data; name=\"audio_file\"; filename=\"\(audioFilename)\"\r\n".data(using: .utf8)!)
    data.append("Content-Type: audio/wav\r\n\r\n".data(using: .utf8)!)
    data.append(audioData)
    data.append("\r\n".data(using: .utf8)!)
    
    // Close boundary
    data.append("--\(boundary)--\r\n".data(using: .utf8)!)
    
    request.httpBody = data
    
    let task = URLSession.shared.dataTask(with: request) { responseData, response, error in
        if let error = error {
            completion(.failure(error))
            return
        }
        
        guard let responseData = responseData,
              let json = try? JSONSerialization.jsonObject(with: responseData) as? [String: Any] else {
            completion(.failure(NSError(domain: "Invalid response", code: -1)))
            return
        }
        
        completion(.success(json))
    }
    
    task.resume()
}
```

---

## 🔄 cURL Examples

### Create Voice Clone with British Child Labels

```bash
curl -X POST "https://your-api.com/users/voice-clone/create-multipart" \
  -F "firebase_token=YOUR_FIREBASE_TOKEN" \
  -F "voice_name=Millie's Voice" \
  -F "description=British child voice for storytelling" \
  -F 'labels={"age":"child","language":"english","accent":"british"}' \
  -F "remove_background_noise=true" \
  -F "audio_file=@/path/to/voice.wav"
```

### Update Voice Clone with Australian Young Adult Labels

```bash
curl -X PUT "https://your-api.com/users/voice-clone/update-multipart" \
  -F "firebase_token=YOUR_FIREBASE_TOKEN" \
  -F "voice_name=Updated Voice" \
  -F "description=Australian young adult voice" \
  -F 'labels={"age":"young","language":"english","accent":"australian"}' \
  -F "remove_background_noise=true" \
  -F "audio_file=@/path/to/new_voice.wav"
```

### Create Voice Clone Without Labels (Minimal)

```bash
curl -X POST "https://your-api.com/users/voice-clone/create-multipart" \
  -F "firebase_token=YOUR_FIREBASE_TOKEN" \
  -F "voice_name=Simple Voice" \
  -F "audio_file=@/path/to/voice.wav"
```

### Disable Background Noise Removal

```bash
curl -X POST "https://your-api.com/users/voice-clone/create-multipart" \
  -F "firebase_token=YOUR_FIREBASE_TOKEN" \
  -F "voice_name=Studio Voice" \
  -F "remove_background_noise=false" \
  -F "audio_file=@/path/to/studio_quality.wav"
```

---

## 📊 Response Format

### Success Response (Create)

```json
{
  "success": true,
  "message": "Voice clone created successfully",
  "voice_clone_id": "abc123xyz",
  "voice_name": "Millie's Voice",
  "user_id": "user_123",
  "audio_format": "wav",
  "audio_size_bytes": 1234567
}
```

### Success Response (Update)

```json
{
  "success": true,
  "message": "Voice clone updated successfully",
  "old_voice_clone_id": "old_abc123",
  "new_voice_clone_id": "new_xyz789",
  "voice_name": "Updated Voice",
  "user_id": "user_123",
  "audio_format": "wav",
  "audio_size_bytes": 1234567,
  "operation": "replace"
}
```

### Error Response

```json
{
  "detail": "Audio file too large (max 25MB)"
}
```

---

## ⚠️ Important Notes

### Labels
- ✅ Labels are **optional** - you can omit them entirely
- ✅ Must be valid JSON string in form data
- ✅ All label fields (age, language, accent) are optional
- ✅ Language defaults to `"english"` if not specified
- ❌ Case sensitive: use `"british"` not `"British"`

### Background Noise Removal
- ✅ Defaults to `true` if not specified
- ✅ Use `"false"` (string) to disable
- ✅ Recommended to keep enabled unless using studio-quality audio

### Audio Files
- ✅ Supported formats: WAV, MP3, FLAC, M4A, OGG
- ✅ Max size: 25MB
- ✅ Min size: 1KB
- ❌ Server detects actual format (ignores client-provided format if wrong)

### Backward Compatibility
- ✅ All existing code continues to work
- ✅ No changes required to existing implementations
- ✅ Labels and noise removal are completely optional

---

## 🎯 Common Use Cases

### 1. British Child for Storytelling
```json
{
  "age": "child",
  "language": "english",
  "accent": "british"
}
```

### 2. American Middle-Aged Adult
```json
{
  "age": "middle_aged",
  "language": "english",
  "accent": "american"
}
```

### 3. Just Accent (Language Auto-Defaults)
```json
{
  "accent": "australian"
}
```
**Note:** Language will automatically default to `"english"`

### 4. Just Age
```json
{
  "age": "young"
}
```

### 5. No Labels at All
Simply omit the `labels` parameter from your request - perfectly valid!

---

## 🚀 Migration Path

If you're currently using the old `/create` or `/update` endpoints:

1. **No Immediate Changes Required** - Old endpoints still work
2. **Gradual Migration** - Update to multipart format when convenient
3. **Add Labels Incrementally** - Start with accent, then add age/language
4. **Test Both** - Multipart is more stable for large files

---

## 📞 Support

For issues or questions about these endpoints, check the server logs for detailed error messages prefixed with emojis:
- 🔄 = Processing
- ✅ = Success
- ❌ = Error
- ⚠️ = Warning
- 🏷️ = Labels
- 🔇 = Noise removal
- 🔍 = Format detection
