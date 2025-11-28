# Child Profile Picture API Documentation

## Overview

The Child Profile Picture API allows parents to upload, update, and delete profile pictures for their children. All endpoints require Firebase authentication and validate that the requesting user is the parent of the child.

**Base URL**: `https://api.junekids.xyz`

---

## Endpoints

### 1. Get Child Profile Picture

Get information about a child's profile picture.

**Endpoint**: `GET /children/{child_id}/profile-picture`

**Authentication**: Firebase ID token in query parameter or header

**Path Parameters**:
- `child_id` (string, required): The child's unique identifier

**Query Parameters**:
- `firebase_token` (string, optional): Firebase authentication token

**Headers** (alternative):
- `Authorization: Bearer {firebase_token}`

**Response** (200 OK) - With profile picture:
```json
{
  "success": true,
  "child_id": "child_abc123def456",
  "image_url": "https://storage.googleapis.com/storyteller-bucket/users/user123/children/child_abc/profile_image_20251121_083045.jpg",
  "has_profile_picture": true
}
```

**Response** (200 OK) - Without profile picture:
```json
{
  "success": true,
  "child_id": "child_abc123def456",
  "image_url": null,
  "has_profile_picture": false
}
```

**Error Responses**:

**401 Unauthorized** - No token provided:
```json
{
  "detail": "Firebase token required"
}
```

**404 Not Found** - Child not found:
```json
{
  "detail": "Child profile not found"
}
```

---

### 2. Upload Child Profile Picture

Upload a new profile picture for a child.

**Endpoint**: `POST /children/{child_id}/profile-picture`

**Authentication**: Firebase ID token in request body

**Path Parameters**:
- `child_id` (string, required): The child's unique identifier

**Request Body**:
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

**Fields**:
- `firebase_token` (string, required): Firebase authentication token
- `image_base64` (string, required): Base64 encoded image data (JPEG, PNG, etc.)

**Image Requirements**:
- **Maximum size**: 10MB
- **Supported formats**: JPEG, PNG, GIF, WebP
- **Recommended dimensions**: 512x512 pixels minimum for best quality
- **Encoding**: Base64 string (without data URI prefix)

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Profile picture uploaded successfully",
  "image_url": "https://storage.googleapis.com/storyteller-bucket/users/user123/children/child_abc/profile_image_20251121_083045.jpg",
  "child_id": "child_abc123def456"
}
```

**Error Responses**:

**401 Unauthorized** - Invalid Firebase token:
```json
{
  "detail": "Invalid Firebase token"
}
```

**404 Not Found** - Child not found:
```json
{
  "detail": "Child profile not found"
}
```

**400 Bad Request** - Invalid image data:
```json
{
  "detail": "Invalid base64 image data"
}
```

**400 Bad Request** - Image too large:
```json
{
  "detail": "Image size exceeds 10MB limit"
}
```

**503 Service Unavailable** - Firebase unavailable:
```json
{
  "detail": "Firebase service is not available"
}
```

---

### 3. Update Child Profile Picture

Update an existing profile picture (replaces the current one).

**Endpoint**: `PUT /children/{child_id}/profile-picture`

**Authentication**: Firebase ID token in request body

**Path Parameters**:
- `child_id` (string, required): The child's unique identifier

**Request Body**:
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs...",
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

**Fields**:
- `firebase_token` (string, required): Firebase authentication token
- `image_base64` (string, required): Base64 encoded image data

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Profile picture updated successfully",
  "image_url": "https://storage.googleapis.com/storyteller-bucket/users/user123/children/child_abc/profile_image_20251121_083145.jpg",
  "child_id": "child_abc123def456"
}
```

**Note**: This endpoint behaves identically to the POST endpoint - it will create a new image in storage and update the database reference. The previous image remains in storage but is no longer referenced.

---

### 4. Delete Child Profile Picture

Delete a child's profile picture and remove it from storage.

**Endpoint**: `DELETE /children/{child_id}/profile-picture`

**Authentication**: Firebase ID token in request body

**Path Parameters**:
- `child_id` (string, required): The child's unique identifier

**Request Body**:
```json
{
  "firebase_token": "eyJhbGciOiJSUzI1NiIs..."
}
```

**Fields**:
- `firebase_token` (string, required): Firebase authentication token

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Profile picture deleted successfully",
  "child_id": "child_abc123def456"
}
```

**Error Responses**:

**404 Not Found** - No profile picture to delete:
```json
{
  "detail": "Child has no profile picture to delete"
}
```

**Note**: This endpoint will attempt to delete the image from Firebase Storage. If storage deletion fails (e.g., file already deleted), the database reference will still be removed successfully.

---

## Complete Integration Examples

### JavaScript/TypeScript Example

```typescript
// Base configuration
const API_BASE_URL = 'https://api.junekids.xyz';
const firebaseToken = await firebase.auth().currentUser.getIdToken();

// 0. Get profile picture information
async function getProfilePicture(childId: string): Promise<{ imageUrl: string | null, hasPicture: boolean }> {
  const response = await fetch(`${API_BASE_URL}/children/${childId}/profile-picture?firebase_token=${firebaseToken}`, {
    method: 'GET',
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get profile picture');
  }
  
  const data = await response.json();
  return {
    imageUrl: data.image_url,
    hasPicture: data.has_profile_picture
  };
}

// Alternative: Using Authorization header
async function getProfilePictureWithHeader(childId: string): Promise<{ imageUrl: string | null, hasPicture: boolean }> {
  const response = await fetch(`${API_BASE_URL}/children/${childId}/profile-picture`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${firebaseToken}`,
    },
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get profile picture');
  }
  
  const data = await response.json();
  return {
    imageUrl: data.image_url,
    hasPicture: data.has_profile_picture
  };
}

// 1. Upload profile picture from file input
async function uploadProfilePicture(childId: string, file: File): Promise<string> {
  // Convert file to base64
  const base64 = await fileToBase64(file);
  
  const response = await fetch(`${API_BASE_URL}/children/${childId}/profile-picture`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      firebase_token: firebaseToken,
      image_base64: base64
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }
  
  const data = await response.json();
  console.log('Uploaded:', data.image_url);
  return data.image_url;
}

// Helper: Convert File to base64
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result as string;
      // Remove data URI prefix (e.g., "data:image/png;base64,")
      const base64Data = base64.split(',')[1];
      resolve(base64Data);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// 2. Update profile picture
async function updateProfilePicture(childId: string, file: File): Promise<string> {
  const base64 = await fileToBase64(file);
  
  const response = await fetch(`${API_BASE_URL}/children/${childId}/profile-picture`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      firebase_token: firebaseToken,
      image_base64: base64
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Update failed');
  }
  
  const data = await response.json();
  return data.image_url;
}

// 4. Delete profile picture
async function deleteProfilePicture(childId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/children/${childId}/profile-picture`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      firebase_token: firebaseToken
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Delete failed');
  }
  
  console.log('Profile picture deleted successfully');
}

// Usage in a React component
function ChildProfilePicture({ childId }: { childId: string }) {
  const [uploading, setUploading] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Load existing profile picture on mount
  useEffect(() => {
    loadProfilePicture();
  }, [childId]);
  
  const loadProfilePicture = async () => {
    try {
      setLoading(true);
      const { imageUrl, hasPicture } = await getProfilePicture(childId);
      if (hasPicture) {
        setImageUrl(imageUrl);
      }
    } catch (error) {
      console.error('Failed to load profile picture:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
      alert('File size must be less than 10MB');
      return;
    }
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file');
      return;
    }
    
    try {
      setUploading(true);
      const url = await uploadProfilePicture(childId, file);
      setImageUrl(url);
      alert('Profile picture uploaded successfully!');
    } catch (error) {
      console.error('Upload error:', error);
      alert(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };
  
  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this profile picture?')) {
      return;
    }
    
    try {
      await deleteProfilePicture(childId);
      setImageUrl(null);
      alert('Profile picture deleted successfully!');
    } catch (error) {
      console.error('Delete error:', error);
      alert(`Delete failed: ${error.message}`);
    }
  };
  
  return (
    <div>
      {loading && <p>Loading...</p>}
      
      {!loading && imageUrl && (
        <div>
          <img src={imageUrl} alt="Profile" style={{ width: 200, height: 200, borderRadius: '50%' }} />
          <button onClick={handleDelete}>Delete Picture</button>
        </div>
      )}
      
      <input
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        disabled={uploading || loading}
      />
      
      {uploading && <p>Uploading...</p>}
    </div>
  );
}
```

---

### React Native Example

```typescript
import * as ImagePicker from 'expo-image-picker';
import * as FileSystem from 'expo-file-system';

// Upload profile picture from camera/gallery
async function uploadProfilePictureFromDevice(childId: string): Promise<string> {
  // Request permissions
  const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (status !== 'granted') {
    throw new Error('Permission to access camera roll is required');
  }
  
  // Pick image
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    allowsEditing: true,
    aspect: [1, 1],
    quality: 0.8,
  });
  
  if (result.canceled) {
    throw new Error('Image selection cancelled');
  }
  
  // Convert to base64
  const base64 = await FileSystem.readAsStringAsync(result.assets[0].uri, {
    encoding: FileSystem.EncodingType.Base64,
  });
  
  // Upload
  const firebaseToken = await firebase.auth().currentUser.getIdToken();
  
  const response = await fetch(`https://api.junekids.xyz/children/${childId}/profile-picture`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      firebase_token: firebaseToken,
      image_base64: base64,
    }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }
  
  const data = await response.json();
  return data.image_url;
}

// Usage in React Native component
function ChildProfileScreen({ childId }: { childId: string }) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  const handleUpload = async () => {
    try {
      setLoading(true);
      const url = await uploadProfilePictureFromDevice(childId);
      setImageUrl(url);
      Alert.alert('Success', 'Profile picture uploaded!');
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <View>
      {imageUrl && (
        <Image
          source={{ uri: imageUrl }}
          style={{ width: 200, height: 200, borderRadius: 100 }}
        />
      )}
      
      <Button
        title={imageUrl ? "Change Picture" : "Upload Picture"}
        onPress={handleUpload}
        disabled={loading}
      />
    </View>
  );
}
```

---

### Python Example

```python
import base64
import requests
from typing import Optional

API_BASE_URL = "https://api.junekids.xyz"

def get_child_profile_picture(
    firebase_token: str,
    child_id: str
) -> Optional[str]:
    """Get a child's profile picture URL"""
    
    response = requests.get(
        f"{API_BASE_URL}/children/{child_id}/profile-picture",
        params={"firebase_token": firebase_token}
    )
    
    response.raise_for_status()
    data = response.json()
    
    if data['has_profile_picture']:
        print(f"✅ Profile picture URL: {data['image_url']}")
        return data['image_url']
    else:
        print("ℹ️ No profile picture set")
        return None

def upload_child_profile_picture(
    firebase_token: str,
    child_id: str,
    image_path: str
) -> str:
    """Upload a child's profile picture from a local file"""
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # Check file size (10MB limit)
    if len(image_data) > 10 * 1024 * 1024:
        raise ValueError("Image size exceeds 10MB limit")
    
    # Encode to base64
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    # Upload
    response = requests.post(
        f"{API_BASE_URL}/children/{child_id}/profile-picture",
        json={
            "firebase_token": firebase_token,
            "image_base64": image_base64
        }
    )
    
    response.raise_for_status()
    data = response.json()
    
    print(f"✅ Uploaded: {data['image_url']}")
    return data['image_url']

def delete_child_profile_picture(
    firebase_token: str,
    child_id: str
) -> None:
    """Delete a child's profile picture"""
    
    response = requests.delete(
        f"{API_BASE_URL}/children/{child_id}/profile-picture",
        json={
            "firebase_token": firebase_token
        }
    )
    
    response.raise_for_status()
    print("✅ Profile picture deleted successfully")

# Usage
if __name__ == "__main__":
    token = "your_firebase_token"
    child_id = "child_abc123"
    
    # Get existing profile picture
    existing_url = get_child_profile_picture(
        firebase_token=token,
        child_id=child_id
    )
    
    # Upload
    image_url = upload_child_profile_picture(
        firebase_token=token,
        child_id=child_id,
        image_path="/path/to/image.jpg"
    )
    
    # Delete
    delete_child_profile_picture(
        firebase_token=token,
        child_id=child_id
    )
```

---

### Swift/iOS Example

```swift
import UIKit
import FirebaseAuth

class ChildProfilePictureManager {
    let apiBaseURL = "https://api.junekids.xyz"
    
    func getProfilePicture(childId: String) async throws -> String? {
        guard let user = Auth.auth().currentUser else {
            throw NSError(domain: "Auth", code: 401)
        }
        
        let token = try await user.getIDToken()
        
        let url = URL(string: "\(apiBaseURL)/children/\(childId)/profile-picture?firebase_token=\(token)")!
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw NSError(domain: "API", code: 0)
        }
        
        let result = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        let hasPicture = result["has_profile_picture"] as! Bool
        
        return hasPicture ? result["image_url"] as? String : nil
    }
    
    func uploadProfilePicture(childId: String, image: UIImage) async throws -> String {
        // Get Firebase token
        guard let user = Auth.auth().currentUser else {
            throw NSError(domain: "Auth", code: 401, userInfo: [NSLocalizedDescriptionKey: "User not authenticated"])
        }
        
        let token = try await user.getIDToken()
        
        // Compress and convert to JPEG
        guard let imageData = image.jpegData(compressionQuality: 0.8) else {
            throw NSError(domain: "Image", code: 400, userInfo: [NSLocalizedDescriptionKey: "Failed to convert image"])
        }
        
        // Check size limit (10MB)
        let maxSize = 10 * 1024 * 1024
        if imageData.count > maxSize {
            throw NSError(domain: "Image", code: 400, userInfo: [NSLocalizedDescriptionKey: "Image size exceeds 10MB"])
        }
        
        // Encode to base64
        let base64String = imageData.base64EncodedString()
        
        // Upload
        let url = URL(string: "\(apiBaseURL)/children/\(childId)/profile-picture")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "firebase_token": token,
            "image_base64": base64String
        ]
        
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw NSError(domain: "Network", code: 0, userInfo: [NSLocalizedDescriptionKey: "Invalid response"])
        }
        
        if httpResponse.statusCode != 200 {
            let errorDict = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
            let errorMessage = errorDict?["detail"] as? String ?? "Upload failed"
            throw NSError(domain: "API", code: httpResponse.statusCode, userInfo: [NSLocalizedDescriptionKey: errorMessage])
        }
        
        let result = try JSONSerialization.jsonObject(with: data) as! [String: Any]
        return result["image_url"] as! String
    }
    
    func deleteProfilePicture(childId: String) async throws {
        guard let user = Auth.auth().currentUser else {
            throw NSError(domain: "Auth", code: 401)
        }
        
        let token = try await user.getIDToken()
        
        let url = URL(string: "\(apiBaseURL)/children/\(childId)/profile-picture")!
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = ["firebase_token": token]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (_, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw NSError(domain: "API", code: 0, userInfo: [NSLocalizedDescriptionKey: "Delete failed"])
        }
    }
}

// Usage in ViewController
class ChildProfileViewController: UIViewController, UIImagePickerControllerDelegate {
    let profileManager = ChildProfilePictureManager()
    let childId = "child_abc123"
    @IBOutlet weak var profileImageView: UIImageView!
    
    override func viewDidLoad() {
        super.viewDidLoad()
        loadProfilePicture()
    }
    
    func loadProfilePicture() {
        Task {
            do {
                if let imageUrl = try await profileManager.getProfilePicture(childId: childId) {
                    // Load image from URL
                    if let url = URL(string: imageUrl),
                       let data = try? Data(contentsOf: url),
                       let image = UIImage(data: data) {
                        profileImageView.image = image
                    }
                }
            } catch {
                print("Error loading profile picture: \(error.localizedDescription)")
            }
        }
    }
    
    @IBAction func uploadButtonTapped(_ sender: UIButton) {
        let picker = UIImagePickerController()
        picker.delegate = self
        picker.allowsEditing = true
        present(picker, animated: true)
    }
    
    func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
        picker.dismiss(animated: true)
        
        guard let image = info[.editedImage] as? UIImage ?? info[.originalImage] as? UIImage else {
            return
        }
        
        Task {
            do {
                let imageUrl = try await profileManager.uploadProfilePicture(childId: childId, image: image)
                print("Uploaded: \(imageUrl)")
                // Update UI with new image
            } catch {
                print("Error: \(error.localizedDescription)")
            }
        }
    }
}
```

---

## Best Practices

### 1. Image Optimization

**Before uploading**:
- Resize images to reasonable dimensions (512x512 to 1024x1024)
- Compress images to reduce file size
- Convert to JPEG with 80% quality for best balance

```javascript
// Example: Resize and compress image before upload
async function prepareImage(file: File): Promise<string> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const MAX_SIZE = 512;
        
        let width = img.width;
        let height = img.height;
        
        if (width > height) {
          if (width > MAX_SIZE) {
            height *= MAX_SIZE / width;
            width = MAX_SIZE;
          }
        } else {
          if (height > MAX_SIZE) {
            width *= MAX_SIZE / height;
            height = MAX_SIZE;
          }
        }
        
        canvas.width = width;
        canvas.height = height;
        
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);
        
        const base64 = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
        resolve(base64);
      };
      img.src = e.target.result as string;
    };
    reader.readAsDataURL(file);
  });
}
```

### 2. Error Handling

Always handle errors gracefully:

```typescript
try {
  await uploadProfilePicture(childId, file);
} catch (error) {
  if (error.message.includes('10MB')) {
    showError('Image is too large. Please select a smaller image.');
  } else if (error.message.includes('Invalid base64')) {
    showError('Invalid image format. Please try another image.');
  } else if (error.message.includes('not found')) {
    showError('Child profile not found.');
  } else {
    showError('Upload failed. Please try again.');
  }
}
```

### 3. Progress Indication

Show upload progress to users:

```typescript
function UploadButton({ childId }: { childId: string }) {
  const [uploading, setUploading] = useState(false);
  
  return (
    <button disabled={uploading}>
      {uploading ? 'Uploading...' : 'Upload Picture'}
    </button>
  );
}
```

### 4. Image Validation

Validate before upload:

```typescript
function validateImage(file: File): string | null {
  // Check file type
  if (!file.type.startsWith('image/')) {
    return 'Please select an image file';
  }
  
  // Check file size (10MB)
  if (file.size > 10 * 1024 * 1024) {
    return 'Image must be less than 10MB';
  }
  
  // Check minimum dimensions (optional)
  return null; // Valid
}
```

---

## Security Considerations

1. **Authentication**: All endpoints require valid Firebase authentication
2. **Authorization**: Users can only manage profile pictures for their own children
3. **File Size Limits**: 10MB maximum to prevent abuse
4. **Storage Organization**: Images are stored with user/child isolation
5. **URL Privacy**: Image URLs are public but unguessable (random filenames)

---

## Storage Details

**Storage Location**: Firebase Cloud Storage

**Path Structure**:
```
users/{user_id}/children/{child_id}/profile_image_{timestamp}.jpg
```

**Example**:
```
users/CnHUiHOSe0RGDPPev6fAeY4YfXj1/children/child_abc123/profile_image_20251121_083045.jpg
```

**Image Format**: All images are stored as JPEG regardless of upload format

**URL Format**:
```
https://storage.googleapis.com/{bucket}/users/{user_id}/children/{child_id}/profile_image_{timestamp}.jpg
```

---

## Troubleshooting

### Issue: "Firebase service is not available"

**Solution**: Check Firebase configuration and service status

### Issue: "Image size exceeds 10MB limit"

**Solution**: Compress or resize image before upload

### Issue: "Invalid base64 image data"

**Solution**: Ensure proper base64 encoding without data URI prefix

### Issue: "Child profile not found"

**Solution**: Verify child_id exists and belongs to authenticated user

### Issue: Upload succeeds but image doesn't display

**Solution**: Check CORS settings and ensure image URL is accessible

---

## Rate Limits

- **Upload**: No specific rate limit, but subject to Firebase Storage quotas
- **Delete**: No specific rate limit
- **Storage**: Subject to Firebase Storage plan limits

---

## Support

For issues or questions:
- Check error messages in API responses
- Verify Firebase authentication is working
- Ensure image meets size and format requirements
- Contact support with request details and error logs
