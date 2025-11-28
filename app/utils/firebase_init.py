# ===== app/utils/firebase_init.py - FIXED VERSION =====
import firebase_admin
from firebase_admin import credentials, storage, firestore
from app.config import settings

# Global Firebase clients (initialized lazily)
_firestore_client = None
_storage_bucket = None
_firebase_initialized = False

def initialize_firebase():
    """Initialize Firebase Admin SDK with proper bucket configuration"""
    global _firebase_initialized
    
    if _firebase_initialized:
        return True
        
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(settings.firebase_credentials_path)
            
            # Use bucket name exactly as specified in .env file
            bucket_name = settings.firebase_storage_bucket
            
            # Only remove gs:// prefix if present (keep everything else as-is)
            if bucket_name.startswith('gs://'):
                bucket_name = bucket_name.replace('gs://', '')
            
            # ❌ REMOVED: Don't change .firebasestorage.app to .appspot.com
            # This was breaking the working bucket name!
            
            print(f"🔧 Initializing Firebase with bucket: {bucket_name}")
            
            firebase_admin.initialize_app(cred, {
                'storageBucket': bucket_name
            })
            _firebase_initialized = True
            print("✅ Firebase initialized successfully")
            return True
        except Exception as e:
            print(f"⚠️ Firebase initialization failed: {str(e)}")
            print("📝 Note: Some features requiring Firebase will not work")
            return False
    else:
        _firebase_initialized = True
        return True

def get_firestore_client():
    """Get Firestore client (with proper initialization check)"""
    global _firestore_client
    
    if not _firebase_initialized:
        if not initialize_firebase():
            return None
    
    if _firestore_client is None:
        try:
            _firestore_client = firestore.client()
        except ValueError as e:
            print(f"⚠️ Firestore client creation failed: {str(e)}")
            return None
        except Exception as e:
            print(f"⚠️ Unexpected error creating Firestore client: {str(e)}")
            return None
    return _firestore_client

def get_storage_bucket():
    """Get Firebase Storage bucket (with proper initialization check)"""
    global _storage_bucket
    
    if not _firebase_initialized:
        if not initialize_firebase():
            return None
    
    if _storage_bucket is None:
        try:
            _storage_bucket = storage.bucket()
            print(f"✅ Storage bucket connected: {_storage_bucket.name}")
        except ValueError as e:
            print(f"⚠️ Storage bucket creation failed: {str(e)}")
            print(f"💡 Check FIREBASE_STORAGE_BUCKET in .env file")
            return None
        except Exception as e:
            print(f"⚠️ Unexpected error creating storage bucket: {str(e)}")
            return None
    return _storage_bucket

def is_firebase_available() -> bool:
    """Check if Firebase is available and initialized"""
    return _firebase_initialized and len(firebase_admin._apps) > 0

def reset_firebase_clients():
    """Reset Firebase clients (useful for testing)"""
    global _firestore_client, _storage_bucket
    _firestore_client = None
    _storage_bucket = None

def test_storage_connection():
    """Test Firebase Storage connection"""
    try:
        bucket = get_storage_bucket()
        if bucket:
            print(f"✅ Storage test successful: {bucket.name}")
            return True
        else:
            print("❌ Storage test failed: No bucket available")
            return False
    except Exception as e:
        print(f"❌ Storage test failed: {str(e)}")
        return False