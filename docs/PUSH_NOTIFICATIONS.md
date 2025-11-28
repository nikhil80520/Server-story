# Push Notifications API Documentation

## Overview
This API provides push notification functionality using Firestore for token storage and Expo Push Notifications for delivery. All data is stored in Firestore - no additional database required.

## Firestore Collection Structure

### Collection: `push_tokens`
```
push_tokens/{device_token}/
  ├── user_id: string          # Firebase user ID
  ├── device_token: string     # Expo/FCM push token (also used as document ID)
  ├── platform: string         # "ios" or "android"
  ├── created_at: timestamp
  └── updated_at: timestamp
```

**Note**: Document ID is the `device_token` itself to prevent duplicates automatically.

---

## API Endpoints

### 1. Register Device Token

**POST** `/api/notifications/register`

Register a device token for push notifications (authenticated users only).

**Headers:**
```
Authorization: Bearer {firebase_id_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "user_id": "firebase-uid-here",
  "device_token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
  "platform": "ios"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Device token registered successfully"
}
```

**Security:**
- ✅ User can only register tokens for themselves
- ✅ Validated platform (must be "ios" or "android")
- ✅ Automatic upsert (updates if exists, creates if new)

---

### 2. Send Mass Notifications

**POST** `/api/notifications/send-mass`

Send push notifications to all users or filtered groups (ADMIN ONLY).

**Headers:**
```
Authorization: Bearer {admin_firebase_id_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "New Story Available! 📖",
  "body": "Check out 'The Magic Garden' - a new adventure awaits!",
  "data": {
    "type": "new_story",
    "story_id": "story_123",
    "action": "open_story"
  },
  "filter": {
    "all_users": true,
    "user_ids": [],
    "platforms": ["ios", "android"]
  }
}
```

**Filter Options:**
- `all_users: true` - Send to all registered devices
- `user_ids: ["uid1", "uid2"]` - Send to specific users only
- `platforms: ["ios", "android"]` - Filter by platform (optional)

**Response:**
```json
{
  "success": true,
  "sent": 1250,
  "failed": 3,
  "message": "Notifications sent: 1250 successful, 3 failed"
}
```

**Security:**
- 🔒 **ADMIN ONLY** - Requires admin role in Firestore users collection
- 🔒 Checks `is_admin: true` or `role: "admin"` in user document

---

### 3. Send Individual Notification

**POST** `/api/notifications/send`

Send push notification to a specific user (authenticated users).

**Headers:**
```
Authorization: Bearer {firebase_id_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "user_id": "firebase-uid-here",
  "title": "Someone shared a story with you! 🎁",
  "body": "John Doe shared 'The Magic Forest' with you",
  "data": {
    "type": "story_shared",
    "story_id": "story_456",
    "shared_by": "user_789"
  }
}
```

**Response:**
```json
{
  "success": true,
  "sent": 2,
  "failed": 0,
  "message": "Notification sent to 2 device(s)"
}
```

**Features:**
- 📱 Sends to ALL devices registered for the user (phone + tablet)
- ✅ Returns count of successful and failed deliveries

---

### 4. Clean Up Invalid Tokens

**DELETE** `/api/notifications/cleanup`

Remove invalid/expired tokens from Firestore (ADMIN ONLY).

**Headers:**
```
Authorization: Bearer {admin_firebase_id_token}
```

**Response:**
```json
{
  "success": true,
  "deleted": 15,
  "message": "Cleaned up 15 invalid tokens"
}
```

**Recommended Usage:**
- Run as a weekly cron job
- Removes tokens that are no longer valid Expo format
- Keeps database clean and reduces costs

---

### 5. Test Token Validity (Debug)

**GET** `/api/notifications/test-token/{token}`

Test if a token is valid (for debugging purposes).

**Example:**
```
GET /api/notifications/test-token/ExponentPushToken[xxxxxxxxxx]
```

**Response:**
```json
{
  "token": "ExponentPushToken[xxxxxxxxxx]",
  "is_valid": true,
  "token_type": "expo"
}
```

---

## Data Payload Structure

The `data` field in notifications allows you to pass custom information that the app can use for navigation and actions.

### Standard Notification Types

```typescript
type NotificationType = 
  | "new_story"       // New story published
  | "story_shared"    // Someone shared a story
  | "comment"         // New comment on story
  | "promotion"       // Marketing/promotional message
  | "system"          // System notifications
```

### Example Payloads

**New Story:**
```json
{
  "type": "new_story",
  "story_id": "story_123",
  "action": "open_story",
  "title": "The Magic Forest"
}
```

**Story Shared:**
```json
{
  "type": "story_shared",
  "story_id": "story_456",
  "action": "open_story",
  "shared_by": "user_789",
  "shared_by_name": "John Doe"
}
```

**Promotion:**
```json
{
  "type": "promotion",
  "action": "open_url",
  "url": "https://yourapp.com/promo",
  "promo_code": "SAVE20"
}
```

---

## Admin Setup

To grant admin access to a user, update their Firestore document:

```javascript
// In Firestore Console or via Admin SDK
db.collection('users').doc(userId).update({
  is_admin: true
  // OR
  role: 'admin'
});
```

---

## Testing Notifications

### Method 1: Using curl

**Register a token:**
```bash
curl -X POST http://localhost:8000/api/notifications/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -d '{
    "user_id": "your-user-id",
    "device_token": "ExponentPushToken[xxxxxx]",
    "platform": "ios"
  }'
```

**Send mass notification (admin):**
```bash
curl -X POST http://localhost:8000/api/notifications/send-mass \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "title": "Test Notification",
    "body": "This is a test",
    "data": {
      "type": "test"
    },
    "filter": {
      "all_users": true,
      "platforms": ["ios", "android"]
    }
  }'
```

**Send to specific user:**
```bash
curl -X POST http://localhost:8000/api/notifications/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -d '{
    "user_id": "target-user-id",
    "title": "Personal Test",
    "body": "This is for you!",
    "data": {
      "type": "test",
      "story_id": "123"
    }
  }'
```

### Method 2: Using Expo Push Tool

1. Get a device token from your app logs
2. Go to https://expo.dev/notifications
3. Paste your token and test message
4. Send test notification

---

## Frontend Integration

The notification service in your app automatically handles token registration. You just need to configure the API endpoint:

```typescript
// In services/notificationService.ts
async sendTokenToServer(userId: string, token: NotificationToken): Promise<void> {
  try {
    const idToken = await getFirebaseIdToken(); // Get from auth
    
    const response = await fetch('https://your-api.com/api/notifications/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`,
      },
      body: JSON.stringify({
        user_id: userId,
        device_token: token.token,
        platform: token.type === 'fcm' ? 'android' : 'ios',
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to register token');
    }
  } catch (error) {
    console.error('Error sending token to server:', error);
  }
}
```

---

## Best Practices

### Security
- ✅ All endpoints require authentication
- ✅ Admin endpoints check for admin role in Firestore
- ✅ Rate limiting recommended on registration endpoint
- ✅ Users can only register tokens for themselves

### Performance
- 📦 Notifications sent in batches of 100 (Expo recommendation)
- 🔄 Automatic retry logic for failed chunks
- 📊 Returns detailed success/failure counts
- 🗑️ Regular cleanup removes invalid tokens

### Data Management
- 💾 All data stored in Firestore (no extra database)
- 🔑 Device token used as document ID (prevents duplicates)
- ⏰ Automatic timestamps (created_at, updated_at)
- 📱 Supports multiple devices per user

### Monitoring
- 📈 Log all notification results
- 🔍 Track delivery rates
- ⚠️ Monitor failed notifications
- 🧹 Run cleanup weekly via cron

---

## Error Handling

**Common Errors:**

| Status | Error | Solution |
|--------|-------|----------|
| 400 | Missing required fields | Check request body has user_id, device_token, platform |
| 403 | Admin access required | User needs is_admin=true in Firestore |
| 403 | Cannot register for another user | user_id must match authenticated user |
| 500 | Failed to register device token | Check Firestore permissions |
| 500 | Failed to send notifications | Check Expo service status |

---

## Implementation Notes

- ✅ **No additional database** - Uses existing Firestore
- ✅ **No external dependencies** - Only httpx (already in requirements.txt)
- ✅ **Expo Push Notifications** - Free for reasonable volumes
- ✅ **Automatic deduplication** - Token as document ID
- ✅ **Multi-device support** - Users can have multiple devices
- ✅ **Platform filtering** - Target iOS or Android specifically
- ✅ **Async/await** - Non-blocking notification delivery

---

## Rate Limits

**Expo Push Notification Service:**
- Free tier: Plenty for most apps
- No hard limit on free tier for now
- Recommended: Batch notifications to 100 per request
- Recommended: Don't send too frequently (respect user preferences)

**Firestore:**
- No additional collections needed
- Reads: Token lookups (minimal)
- Writes: Token registration (once per device per session)

---

## Future Enhancements

**Possible additions:**
- 🔔 User notification preferences (opt-in/opt-out by type)
- 📅 Scheduled notifications (send at specific time)
- 🎯 Advanced targeting (by subscription tier, age group)
- 📊 Analytics (delivery rates, open rates)
- 🔕 Quiet hours (don't send at night)
- 🌍 Localization (notification language based on user preference)

---

## Support

For issues or questions:
- Check logs for detailed error messages
- Test tokens at https://expo.dev/notifications
- Verify admin status in Firestore
- Check Firebase authentication is working

**Common debugging steps:**
1. Verify token format (should start with `ExponentPushToken[`)
2. Check user authentication is working
3. Verify admin has `is_admin: true` in Firestore
4. Test with Expo's notification tool first
5. Check server logs for detailed error messages
