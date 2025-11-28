"""
Push Notification Service using Firestore and Expo Push Notifications
"""
from firebase_admin import firestore
from datetime import datetime
from typing import List, Dict, Optional
import asyncio
import httpx


class NotificationService:
    """Service for managing push notifications with Firestore"""
    
    def __init__(self, db: firestore.firestore.Client):
        self.db = db
        self.tokens_collection = "push_tokens"
        self.expo_push_url = "https://exp.host/--/api/v2/push/send"
    
    async def register_device_token(self, user_id: str, device_token: str, platform: str) -> bool:
        """
        Register a device token for push notifications
        
        Args:
            user_id: Firebase user ID
            device_token: Expo/FCM push token
            platform: "ios" or "android"
            
        Returns:
            bool: Success status
        """
        try:
            # Use device_token as document ID to prevent duplicates
            token_ref = self.db.collection(self.tokens_collection).document(device_token)
            
            # Check if token already exists
            token_doc = token_ref.get()
            
            token_data = {
                "user_id": user_id,
                "device_token": device_token,
                "platform": platform,
                "updated_at": firestore.firestore.SERVER_TIMESTAMP
            }
            
            if token_doc.exists:
                # Update existing token
                token_ref.update(token_data)
                print(f"✅ Updated device token for user {user_id}")
            else:
                # Create new token entry
                token_data["created_at"] = firestore.firestore.SERVER_TIMESTAMP
                token_ref.set(token_data)
                print(f"✅ Registered new device token for user {user_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to register device token: {e}")
            return False
    
    async def get_user_tokens(self, user_id: str) -> List[str]:
        """
        Get all device tokens for a specific user
        
        Args:
            user_id: Firebase user ID
            
        Returns:
            List of device tokens
        """
        try:
            tokens_ref = self.db.collection(self.tokens_collection)
            query = tokens_ref.where("user_id", "==", user_id)
            docs = query.stream()
            
            tokens = [doc.to_dict()["device_token"] for doc in docs]
            return tokens
            
        except Exception as e:
            print(f"❌ Failed to get user tokens: {e}")
            return []
    
    async def get_all_tokens(self, platforms: Optional[List[str]] = None) -> List[str]:
        """
        Get all device tokens, optionally filtered by platform
        
        Args:
            platforms: List of platforms to filter by ["ios", "android"]
            
        Returns:
            List of device tokens
        """
        try:
            tokens_ref = self.db.collection(self.tokens_collection)
            
            if platforms:
                # Firestore doesn't support IN queries for arrays directly in Python SDK
                # We'll fetch and filter
                docs = tokens_ref.stream()
                tokens = [
                    doc.to_dict()["device_token"] 
                    for doc in docs 
                    if doc.to_dict().get("platform") in platforms
                ]
            else:
                docs = tokens_ref.stream()
                tokens = [doc.to_dict()["device_token"] for doc in docs]
            
            return tokens
            
        except Exception as e:
            print(f"❌ Failed to get all tokens: {e}")
            return []
    
    async def get_tokens_for_users(self, user_ids: List[str]) -> List[str]:
        """
        Get device tokens for specific users
        
        Args:
            user_ids: List of Firebase user IDs
            
        Returns:
            List of device tokens
        """
        try:
            if not user_ids:
                return []
            
            tokens = []
            # Firestore IN queries are limited to 10 items, so we batch
            batch_size = 10
            for i in range(0, len(user_ids), batch_size):
                batch = user_ids[i:i + batch_size]
                tokens_ref = self.db.collection(self.tokens_collection)
                query = tokens_ref.where("user_id", "in", batch)
                docs = query.stream()
                
                batch_tokens = [doc.to_dict()["device_token"] for doc in docs]
                tokens.extend(batch_tokens)
            
            return tokens
            
        except Exception as e:
            print(f"❌ Failed to get tokens for users: {e}")
            return []
    
    def is_expo_push_token(self, token: str) -> bool:
        """
        Validate if token is a valid Expo push token
        
        Args:
            token: Push token to validate
            
        Returns:
            bool: True if valid Expo token
        """
        if not token:
            return False
        
        # Expo tokens start with ExponentPushToken[
        # FCM tokens are longer alphanumeric strings
        return (
            token.startswith("ExponentPushToken[") or 
            (len(token) > 100 and token.replace("-", "").replace("_", "").replace(":", "").isalnum())
        )
    
    async def send_push_notifications(
        self, 
        tokens: List[str], 
        title: str, 
        body: str, 
        data: Optional[Dict] = None
    ) -> tuple[int, int]:
        """
        Send push notifications to multiple tokens
        
        Args:
            tokens: List of device tokens
            title: Notification title
            body: Notification body
            data: Custom data payload
            
        Returns:
            Tuple of (sent_count, failed_count)
        """
        if not tokens:
            return 0, 0
        
        # Filter valid Expo tokens
        valid_tokens = [token for token in tokens if self.is_expo_push_token(token)]
        
        if not valid_tokens:
            print("⚠️ No valid Expo push tokens found")
            return 0, len(tokens)
        
        # Create messages
        messages = []
        for token in valid_tokens:
            message = {
                "to": token,
                "sound": "default",
                "title": title,
                "body": body,
                "data": data or {},
                "priority": "high",
                "channelId": "default"
            }
            messages.append(message)
        
        # Send in chunks of 100 (Expo recommendation)
        chunk_size = 100
        total_sent = 0
        total_failed = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(0, len(messages), chunk_size):
                chunk = messages[i:i + chunk_size]
                
                try:
                    response = await client.post(
                        self.expo_push_url,
                        json=chunk,
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                            "Accept-Encoding": "gzip, deflate"
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        # Expo returns an array of ticket responses
                        data_array = result.get("data", [])
                        
                        for ticket in data_array:
                            if ticket.get("status") == "ok":
                                total_sent += 1
                            else:
                                total_failed += 1
                                error_msg = ticket.get("message", "Unknown error")
                                print(f"❌ Notification failed: {error_msg}")
                    else:
                        print(f"❌ Expo API error: {response.status_code}")
                        total_failed += len(chunk)
                        
                except Exception as e:
                    print(f"❌ Error sending notification chunk: {e}")
                    total_failed += len(chunk)
        
        return total_sent, total_failed
    
    async def send_to_user(
        self, 
        user_id: str, 
        title: str, 
        body: str, 
        data: Optional[Dict] = None
    ) -> tuple[int, int]:
        """
        Send push notification to all devices of a specific user
        
        Args:
            user_id: Firebase user ID
            title: Notification title
            body: Notification body
            data: Custom data payload
            
        Returns:
            Tuple of (sent_count, failed_count)
        """
        tokens = await self.get_user_tokens(user_id)
        
        if not tokens:
            print(f"⚠️ No devices registered for user {user_id}")
            return 0, 0
        
        return await self.send_push_notifications(tokens, title, body, data)
    
    async def send_to_all(
        self, 
        title: str, 
        body: str, 
        data: Optional[Dict] = None,
        platforms: Optional[List[str]] = None
    ) -> tuple[int, int]:
        """
        Send push notification to all users
        
        Args:
            title: Notification title
            body: Notification body
            data: Custom data payload
            platforms: Filter by platforms ["ios", "android"]
            
        Returns:
            Tuple of (sent_count, failed_count)
        """
        tokens = await self.get_all_tokens(platforms)
        
        if not tokens:
            print("⚠️ No device tokens found")
            return 0, 0
        
        print(f"📤 Sending notification to {len(tokens)} devices")
        return await self.send_push_notifications(tokens, title, body, data)
    
    async def send_to_users(
        self,
        user_ids: List[str],
        title: str,
        body: str,
        data: Optional[Dict] = None
    ) -> tuple[int, int]:
        """
        Send push notification to specific users
        
        Args:
            user_ids: List of Firebase user IDs
            title: Notification title
            body: Notification body
            data: Custom data payload
            
        Returns:
            Tuple of (sent_count, failed_count)
        """
        tokens = await self.get_tokens_for_users(user_ids)
        
        if not tokens:
            print(f"⚠️ No devices registered for specified users")
            return 0, 0
        
        return await self.send_push_notifications(tokens, title, body, data)
    
    async def cleanup_invalid_tokens(self) -> int:
        """
        Remove invalid/expired tokens from Firestore
        
        Returns:
            Number of tokens deleted
        """
        try:
            tokens_ref = self.db.collection(self.tokens_collection)
            docs = tokens_ref.stream()
            
            deleted_count = 0
            batch = self.db.batch()
            batch_count = 0
            
            for doc in docs:
                token_data = doc.to_dict()
                device_token = token_data.get("device_token", "")
                
                if not self.is_expo_push_token(device_token):
                    batch.delete(doc.reference)
                    batch_count += 1
                    deleted_count += 1
                    
                    # Firestore batch limit is 500 operations
                    if batch_count >= 500:
                        batch.commit()
                        batch = self.db.batch()
                        batch_count = 0
            
            # Commit remaining deletions
            if batch_count > 0:
                batch.commit()
            
            print(f"🧹 Cleaned up {deleted_count} invalid tokens")
            return deleted_count
            
        except Exception as e:
            print(f"❌ Failed to cleanup tokens: {e}")
            return 0
