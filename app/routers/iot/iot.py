"""
Unified IoT module

This single file contains:
- Pydantic request/response models for the IoT API
- In-memory rate limiter and token cache
- IoT security utilities (HMAC + JWT)
- Device auth helpers (JWT/HMAC verification)
- Firestore-backed device service
- FastAPI router endpoints

Consolidated from prior files:
  - app/models/iot_api_models.py
  - app/models/iot_device.py (only in-memory caches retained)
  - app/services/iot_security.py
  - app/services/iot_device_service_firestore.py
  - app/middleware/iot_auth.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any
import logging
import base64
import json
import asyncio
import time
from datetime import datetime, timedelta
from asyncio import gather, create_task
from openai import OpenAI
from enum import Enum
from app.utils.async_utils import get_or_create_event_loop

from app.core.config import settings
from app.utils.firebase_init import get_firestore_client
from app.services.storage.storage_service import StorageService
from app.services.ai.cartesia_service import CartesiaService
from app.services.content.media_service import MediaService
from app.dependencies import get_optional_current_user, verify_firebase_token
from pydantic import BaseModel, Field, validator
import hmac
import hashlib
import secrets
import jwt
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/iot", tags=["IoT Device Management"])


# ============================
# Pydantic models and Enums
# ============================

class DeviceStatus(str, Enum):
    UNCLAIMED = "unclaimed"
    CLAIMED = "claimed"
    SUSPENDED = "suspended"
    OFFLINE = "offline"


class DeviceType(str, Enum):
    STORYTELLER = "storyteller"
    SENSOR = "sensor"
    DISPLAY = "display"
    CONTROLLER = "controller"


class ClaimTokenRequest(BaseModel):
    device_type: Optional[DeviceType] = None
    expires_in: Optional[int] = Field(default=300, ge=60, le=3600)
    firebase_token: Optional[str] = None


class ClaimDeviceRequest(BaseModel):
    claim_token: str = Field(..., min_length=16)
    device_name: Optional[str] = Field(None, max_length=100)


class HeartbeatRequest(BaseModel):
    local_ip: Optional[str] = Field(None, pattern=r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')
    bssid: Optional[str] = Field(None, pattern=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    public_ip: Optional[str] = None
    rssi: Optional[int] = Field(None, ge=-100, le=0)
    firmware_version: Optional[str] = Field(None, max_length=50)

    @validator('local_ip')
    def validate_local_ip(cls, v):
        if v and not any(v.startswith(prefix) for prefix in ['192.168.', '10.', '172.']):
            raise ValueError('Must be a private IP address')
        return v


class DeviceCommandRequest(BaseModel):
    command_type: str = Field(..., min_length=1, max_length=50)
    command_payload: Optional[Dict[str, Any]] = None

    @validator('command_type')
    def validate_command_type(cls, v):
        allowed_commands = [
            'play_story', 'stop_story', 'set_volume', 'set_brightness',
            'reboot', 'update_firmware', 'get_status', 'factory_reset'
        ]
        if v not in allowed_commands:
            raise ValueError(f'Command type must be one of: {", ".join(allowed_commands)}')
        return v


class LocalControlTokenRequest(BaseModel):
    device_id: str


class CreateDeviceRequest(BaseModel):
    device_secret: str = Field(..., min_length=32)
    device_type: DeviceType = DeviceType.STORYTELLER
    firmware_version: Optional[str] = Field(None, max_length=50)


class UpdateDeviceRequest(BaseModel):
    device_name: Optional[str] = Field(None, max_length=100)
    status: Optional[DeviceStatus] = None


class ClaimTokenResponse(BaseModel):
    claim_token: str
    expires_in: int
    expires_at: str
    device_type: Optional[str] = None


class ClaimDeviceResponse(BaseModel):
    status: str
    user_id: str
    device_id: str
    device_name: str
    device_type: str


class DeviceSessionResponse(BaseModel):
    device_jwt: str
    expires_in: int
    device_id: str


class HeartbeatResponse(BaseModel):
    status: str
    timestamp: str


class DeviceCommandResponse(BaseModel):
    command_id: str
    status: str
    command_type: str
    sent_at: str


class LocalControlTokenResponse(BaseModel):
    jwt: str
    expires_in: int
    device_id: str


class DevicePresenceInfo(BaseModel):
    last_local_ip: Optional[str] = None
    last_bssid: Optional[str] = None
    last_rssi: Optional[int] = None
    last_seen_at: Optional[datetime] = None


class DeviceInfo(BaseModel):
    device_id: str
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    status: str
    firmware_version: Optional[str] = None
    owner_user_id: Optional[str] = None
    claimed_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    presence: Optional[DevicePresenceInfo] = None


class DeviceListResponse(BaseModel):
    devices: List[DeviceInfo]
    total_count: int
    status_filter: Optional[str] = None


class DeviceStatsResponse(BaseModel):
    total_devices: int
    status_breakdown: Dict[str, int]
    online_devices: int
    commands_sent_today: int
    last_updated: str


class IntroAudioRequest(BaseModel):
    device_name: Optional[str] = Field(None, max_length=100)
    preferred_voice: Optional[str] = Field(None, description="Voice preference (male/female/custom)")
    include_story_suggestions: bool = Field(True, description="Whether to include recent story suggestions")
    max_stories: int = Field(5, ge=1, le=5, description="Maximum number of story suggestions (fixed at 5)")


class StoryPreview(BaseModel):
    story_id: str
    title: str
    description: Optional[str] = None
    created_at: datetime
    thumbnail_url: Optional[str] = None
    intro_audio_url: Optional[str] = Field(None, description="URL to intro audio file")


class IntroAudioResponse(BaseModel):
    audio_files: List[str]
    story_suggestions: List[StoryPreview] = Field(default_factory=list)
    total_duration_seconds: float
    voice_used: str
    character_name: str = Field(default="June")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IntroAudioFilesResponse(BaseModel):
    audio_file_urls: List[str]
    story_suggestions: List[StoryPreview] = Field(default_factory=list)
    total_duration_seconds: float
    voice_used: str
    character_name: str = Field(default="June")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime


class HealthCheckResponse(BaseModel):
    status: str
    database: Dict[str, Any]
    in_memory_stores: Dict[str, Any]
    device_stats: Dict[str, Any]
    timestamp: str


# ============================
# In-memory stores (rate limit + token cache)
# ============================

class InMemoryRateLimit:
    def __init__(self):
        self._timestamps: Dict[str, List[float]] = {}

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        timestamps = self._timestamps.get(key, [])
        timestamps = [ts for ts in timestamps if now - ts < window_seconds]
        if len(timestamps) < limit:
            timestamps.append(now)
            self._timestamps[key] = timestamps
            return True
        self._timestamps[key] = timestamps
        return False

    def cleanup_old_entries(self, max_age_seconds: int = 3600):
        now = time.time()
        for key in list(self._timestamps.keys()):
            ts = [t for t in self._timestamps[key] if now - t < max_age_seconds]
            if ts:
                self._timestamps[key] = ts
            else:
                del self._timestamps[key]


rate_limiter = InMemoryRateLimit()


class InMemoryTokenCache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def set(self, key: str, value: str, ttl_seconds: int):
        expires_at = time.time() + ttl_seconds
        self._cache[key] = {"value": value, "expires_at": expires_at}

    def get(self, key: str) -> Optional[str]:
        entry = self._cache.get(key)
        if not entry:
            return None
        if time.time() >= entry["expires_at"]:
            del self._cache[key]
            return None
        return entry["value"]

    def delete(self, key: str):
        self._cache.pop(key, None)

    def cleanup_expired(self):
        now = time.time()
        for key in list(self._cache.keys()):
            if now >= self._cache[key]["expires_at"]:
                del self._cache[key]


token_cache = InMemoryTokenCache()


# ============================
# Security utilities (HMAC + JWT)
# ============================

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
except ImportError:
    PasswordHasher = None
    class VerifyMismatchError(Exception):
        pass


class IoTSecurity:
    def __init__(self):
        if PasswordHasher is None:
            raise RuntimeError("argon2-cffi is required for device secret hashing")
        self._ph = PasswordHasher()
        self.device_private_key: Optional[str] = None
        self.device_public_key: Optional[str] = None
        self._load_keys()

    def _load_keys(self):
        try:
            if Path(settings.device_jwt_private_key_path).exists():
                self.device_private_key = Path(settings.device_jwt_private_key_path).read_text()
            if Path(settings.device_jwt_public_key_path).exists():
                self.device_public_key = Path(settings.device_jwt_public_key_path).read_text()
            if not self.device_private_key or not self.device_public_key:
                self._generate_dev_keys()
        except Exception:
            self._generate_dev_keys()

    def _generate_dev_keys(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.device_private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        public_key = private_key.public_key()
        self.device_public_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
        Path("keys").mkdir(exist_ok=True)
        Path(settings.device_jwt_private_key_path).write_text(self.device_private_key)
        Path(settings.device_jwt_public_key_path).write_text(self.device_public_key)

    def hash_device_secret(self, secret: str) -> bytes:
        return self._ph.hash(secret).encode("utf-8")

    def verify_device_secret(self, secret: str, hashed: bytes) -> bool:
        try:
            self._ph.verify(hashed.decode("utf-8"), secret)
            return True
        except VerifyMismatchError:
            return False

    def verify_hmac_signature(
        self,
        secret: bytes,
        method: str,
        path: str,
        body: bytes,
        timestamp: int,
        signature: str,
        tolerance_seconds: Optional[int] = None,
    ) -> bool:
        if tolerance_seconds is None:
            tolerance_seconds = settings.hmac_tolerance_seconds
        now = int(time.time())
        if abs(now - timestamp) > tolerance_seconds:
            raise HTTPException(status_code=401, detail="timestamp_skew")
        message = f"{method.upper()}|{path}|".encode() + body + f"|{timestamp}".encode()
        expected_signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_signature, signature):
            raise HTTPException(status_code=401, detail="invalid_signature")
        return True

    def mint_device_jwt(self, device_id: str, ttl_seconds: Optional[int] = None, audience: str = "device-api") -> str:
        if ttl_seconds is None:
            ttl_seconds = settings.device_jwt_ttl_seconds
        now_ts = int(time.time())
        payload = {
            "sub": device_id,
            "aud": audience,
            "iat": now_ts,
            "exp": now_ts + ttl_seconds,
            "iss": "storyteller-iot",
        }
        return jwt.encode(payload, self.device_private_key, algorithm="RS256")

    def verify_device_jwt(self, token: str, audience: str = "device-api") -> Dict[str, Any]:
        try:
            return jwt.decode(token, self.device_public_key, algorithms=["RS256"], audience=audience)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="token_expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"invalid_token: {str(e)}")

    def generate_claim_token(self, user_id: str, device_type: Optional[str] = None) -> str:
        token = secrets.token_urlsafe(32)
        token_cache.set(f"claim_token:{token}", f"{user_id}:{device_type or 'any'}", settings.claim_token_ttl_seconds)
        return token

    def verify_claim_token(self, token: str) -> tuple[str, Optional[str]]:
        cache_value = token_cache.get(f"claim_token:{token}")
        if not cache_value:
            raise HTTPException(status_code=400, detail="invalid_or_expired_token")
        token_cache.delete(f"claim_token:{token}")
        user_id, device_type = cache_value.split(":", 1)
        return user_id, (None if device_type == "any" else device_type)

    def generate_local_control_token(self, device_id: str) -> str:
        return self.mint_device_jwt(device_id, ttl_seconds=settings.local_token_ttl_seconds, audience="device-local")

    def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        return rate_limiter.is_allowed(key, limit, window_seconds)

    def hash_public_ip(self, ip: str) -> str:
        return hashlib.sha256(f"{ip}:{settings.device_secret_key}".encode()).hexdigest()


iot_security = IoTSecurity()


# ============================
# Auth helpers (JWT/HMAC)
# ============================

device_bearer = HTTPBearer(auto_error=False)


class DeviceAuthInfo:
    def __init__(self, device_id: str, auth_method: str, device: Optional[Dict[str, Any]] = None):
        self.device_id = device_id
        self.auth_method = auth_method
        self.device = device


async def _get_device_from_firestore(device_id: str) -> Optional[Dict[str, Any]]:
    try:
        firestore_client = get_firestore_client()
        doc = firestore_client.collection('devices').document(device_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"Error getting device from Firestore: {e}")
        return None


async def verify_device_hmac(request: Request) -> DeviceAuthInfo:
    device_id = request.headers.get("X-Device-Id") or request.headers.get("X-Device-ID")
    timestamp = request.headers.get("X-Timestamp") or request.headers.get("X-TIMESTAMP")
    signature = request.headers.get("X-Signature") or request.headers.get("X-SIGNATURE")
    if not all([device_id, signature]):
        raise HTTPException(status_code=401, detail="missing_headers")
    if timestamp:
        try:
            timestamp_int = int(timestamp)
        except ValueError:
            raise HTTPException(status_code=401, detail="invalid_timestamp")
    else:
        timestamp_int = int(time.time())
    device = await _get_device_from_firestore(device_id)
    if not device:
        raise HTTPException(status_code=401, detail="device_not_found")
    if not device.get("device_secret_raw"):
        raise HTTPException(status_code=401, detail="device_secret_not_available")
    body = await request.body()
    iot_security.verify_hmac_signature(
        secret=device["device_secret_raw"].encode(),
        method=request.method,
        path=request.url.path,
        body=body,
        timestamp=timestamp_int,
        signature=signature,
    )
    if not iot_security.check_rate_limit(f"device_hmac:{device_id}", limit=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="rate_limit_exceeded")
    return DeviceAuthInfo(device_id=device_id, auth_method="hmac", device=device)


async def verify_device_jwt(credentials: Optional[HTTPAuthorizationCredentials] = Depends(device_bearer)) -> DeviceAuthInfo:
    if not credentials:
        raise HTTPException(status_code=401, detail="missing_jwt_token")
    payload = iot_security.verify_device_jwt(credentials.credentials)
    device_id = payload.get("sub")
    if not device_id:
        raise HTTPException(status_code=401, detail="invalid_jwt_payload")
    device = await _get_device_from_firestore(device_id)
    if not device:
        raise HTTPException(status_code=401, detail="device_not_found")
    if device.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="device_suspended")
    if not iot_security.check_rate_limit(f"device_jwt:{device_id}", limit=120, window_seconds=60):
        raise HTTPException(status_code=429, detail="rate_limit_exceeded")
    return DeviceAuthInfo(device_id=device_id, auth_method="jwt", device=device)


async def verify_device_auth_flexible(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(device_bearer)) -> DeviceAuthInfo:
    if credentials:
        try:
            return await verify_device_jwt(credentials)
        except HTTPException:
            pass
    return await verify_device_hmac(request)


async def require_device_auth(auth_info: DeviceAuthInfo = Depends(verify_device_auth_flexible)) -> DeviceAuthInfo:
    return auth_info


async def require_device_hmac(auth_info: DeviceAuthInfo = Depends(verify_device_hmac)) -> DeviceAuthInfo:
    return auth_info


async def require_device_jwt(auth_info: DeviceAuthInfo = Depends(verify_device_jwt)) -> DeviceAuthInfo:
    return auth_info


async def require_claimed_device(auth_info: DeviceAuthInfo = Depends(require_device_auth)) -> DeviceAuthInfo:
    if not auth_info.device or auth_info.device.get("status") != "claimed":
        raise HTTPException(status_code=403, detail="device_not_claimed")
    return auth_info


async def get_hmac_auth_device(auth_info: DeviceAuthInfo = Depends(require_device_hmac)) -> str:
    return auth_info.device_id


async def get_authenticated_device(auth_info: DeviceAuthInfo = Depends(require_device_auth)) -> str:
    return auth_info.device_id


# ============================
# Firestore service
# ============================


def firebase_user_id_to_uuid(firebase_user_id: str) -> str:
    return firebase_user_id


class IoTDeviceServiceFirestore:
    def __init__(self):
        self.client = get_firestore_client()
        if self.client is None:
            raise RuntimeError("Firestore client not available")

    async def create_device(self, device_secret: str, device_type: str = "storyteller", firmware_version: Optional[str] = None) -> Dict[str, Any]:
        device_id = secrets.token_urlsafe(16)
        now = datetime.utcnow().isoformat()
        secret_hash = iot_security.hash_device_secret(device_secret)
        device = {
            "device_id": device_id,
            "device_secret_hash": secret_hash.decode('utf-8') if isinstance(secret_hash, bytes) else str(secret_hash),
            "device_secret_raw": device_secret,
            "device_type": device_type,
            "firmware_version": firmware_version,
            "status": "unclaimed",
            "owner_user_id": None,
            "claimed_at": None,
            "created_at": now,
            "last_seen_at": None,
            "device_name": None,
        }
        self.client.collection('devices').document(device_id).set(device)
        logger.info(f"✅ Created device (Firestore) {device_id}")
        return device

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        doc = self.client.collection('devices').document(device_id).get()
        return doc.to_dict() if doc.exists else None

    async def generate_claim_token(self, user_id: str, device_type: Optional[str] = None, ttl_seconds: Optional[int] = None) -> Dict[str, Any]:
        if ttl_seconds is None:
            ttl_seconds = settings.claim_token_ttl_seconds
        if not iot_security.check_rate_limit(f"claim_token:{user_id}", limit=5, window_seconds=300):
            raise ValueError("Rate limit exceeded for claim token generation")
        token = iot_security.generate_claim_token(user_id, device_type)
        expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
        doc = {
            "token": token,
            "user_id": firebase_user_id_to_uuid(user_id),
            "device_type": device_type,
            "expires_at": expires_at,
            "used_at": None,
            "used_by_device": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        self.client.collection('claim_tokens').document(token).set(doc)
        logger.info(f"✅ Stored claim token in Firestore for user {user_id}")
        return {"claim_token": token, "expires_in": ttl_seconds, "expires_at": expires_at, "device_type": device_type}

    async def claim_device(self, device_id: str, claim_token: str, device_name: Optional[str] = None) -> Dict[str, Any]:
        try:
            user_id, allowed_device_type = iot_security.verify_claim_token(claim_token)
            logger.info("Verified claim token in-memory cache")
        except Exception:
            token_doc = self.client.collection('claim_tokens').document(claim_token).get()
            if not token_doc.exists:
                raise ValueError("Invalid or expired claim token")
            token_data = token_doc.to_dict()
            if token_data.get('used_at'):
                raise ValueError("Claim token already used")
            if token_data.get('expires_at') and datetime.fromisoformat(token_data['expires_at']) < datetime.utcnow():
                raise ValueError("Claim token expired")
            user_id = token_data.get('user_id')
            allowed_device_type = token_data.get('device_type')

        device_ref = self.client.collection('devices').document(device_id)
        device_doc = device_ref.get()
        if not device_doc.exists:
            raise ValueError("Device not found")
        device = device_doc.to_dict()
        if device.get('status') == 'claimed':
            raise ValueError("Device already claimed")
        if allowed_device_type and device.get('device_type') != allowed_device_type:
            raise ValueError("Device type mismatch")
        device['owner_user_id'] = user_id
        device['status'] = 'claimed'
        device['claimed_at'] = datetime.utcnow().isoformat()
        device['device_name'] = device_name or device.get('device_name') or f"{device.get('device_type')}-{device_id[:8]}"
        device_ref.set(device)
        self.client.collection('claim_tokens').document(claim_token).update({
            'used_at': datetime.utcnow().isoformat(),
            'used_by_device': device_id,
        })
        logger.info(f"✅ Device {device_id} claimed by user {user_id} (Firestore)")
        return {
            'status': 'claimed',
            'user_id': user_id,
            'device_id': device_id,
            'device_name': device['device_name'],
            'device_type': device['device_type'],
        }

    async def generate_device_session_token(self, device_id: str, ttl_seconds: Optional[int] = None) -> Dict[str, Any]:
        if ttl_seconds is None:
            ttl_seconds = settings.device_jwt_ttl_seconds
        device = await self.get_device(device_id)
        if not device:
            raise ValueError("Device not found")
        if device.get('status') == 'suspended':
            raise ValueError("Device suspended")
        token = iot_security.mint_device_jwt(device_id, ttl_seconds=ttl_seconds)
        return {"device_jwt": token, "expires_in": ttl_seconds, "device_id": device_id}

    async def update_device_heartbeat(self, device_id: str, local_ip: Optional[str] = None, bssid: Optional[str] = None, public_ip: Optional[str] = None, rssi: Optional[int] = None, firmware_version: Optional[str] = None) -> Dict[str, Any]:
        device_ref = self.client.collection('devices').document(device_id)
        device_doc = device_ref.get()
        if not device_doc.exists:
            raise ValueError("Device not found")
        now = datetime.utcnow().isoformat()
        updates = {'last_seen_at': now}
        if firmware_version:
            updates['firmware_version'] = firmware_version
        device_ref.update(updates)
        presence_ref = device_ref.collection('presence').document('latest')
        presence_data = {
            'last_local_ip': local_ip,
            'last_bssid': bssid,
            'last_public_ip_hash': iot_security.hash_public_ip(public_ip) if public_ip else None,
            'last_rssi': rssi,
            'last_seen_at': now,
        }
        presence_ref.set(presence_data)
        logger.debug(f"📡 Updated heartbeat for device {device_id} (Firestore)")
        return {"status": "ok", "timestamp": now}

    async def get_user_devices(self, user_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.client.collection('devices').where('owner_user_id', '==', user_id)
        if status_filter:
            query = query.where('status', '==', status_filter)
        docs = query.stream()
        devices = []
        for doc in docs:
            device_data = doc.to_dict()
            presence_doc = doc.reference.collection('presence').document('latest').get()
            if presence_doc.exists:
                device_data['presence'] = presence_doc.to_dict()
            devices.append(device_data)
        logger.info(f"📱 Found {len(devices)} devices for user {user_id}")
        return devices

    async def get_device_stats(self) -> Dict[str, Any]:
        total_devices = 0
        claimed_devices = 0
        active_devices = 0
        five_min_ago = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
        for doc in self.client.collection('devices').stream():
            total_devices += 1
            device = doc.to_dict()
            if device.get('status') == 'claimed':
                claimed_devices += 1
            if device.get('last_seen_at') and device['last_seen_at'] > five_min_ago:
                active_devices += 1
        return {
            'total_devices': total_devices,
            'claimed_devices': claimed_devices,
            'unclaimed_devices': total_devices - claimed_devices,
            'active_devices': active_devices,
            'timestamp': datetime.utcnow().isoformat(),
        }

    async def is_device_active(self, device_id: str, threshold_minutes: int = 5) -> bool:
        device = await self.get_device(device_id)
        if not device or not device.get('last_seen_at'):
            return False
        last_seen = datetime.fromisoformat(device['last_seen_at'])
        threshold = datetime.utcnow() - timedelta(minutes=threshold_minutes)
        return last_seen > threshold

    async def get_device_with_relationships(self, device_id: str) -> Optional[Dict[str, Any]]:
        device = await self.get_device(device_id)
        if not device:
            return None
        device_ref = self.client.collection('devices').document(device_id)
        presence_doc = device_ref.collection('presence').document('latest').get()
        if presence_doc.exists:
            device['presence'] = presence_doc.to_dict()
        device['is_active'] = await self.is_device_active(device_id)
        if device.get('status') == 'claimed':
            claim_tokens = self.client.collection('claim_tokens').where('used_by_device', '==', device_id).limit(1).stream()
            for token_doc in claim_tokens:
                device['claim_info'] = token_doc.to_dict()
                break
        return device

    async def create_test_claim_token(self, user_id: str, device_type: str = "storyteller", ttl_seconds: int = 3600) -> Dict[str, Any]:
        return await self.generate_claim_token(user_id, device_type=device_type, ttl_seconds=ttl_seconds)

logger = logging.getLogger(__name__)


# Helper: safely read fields from a device/result that may be a dict or an object
def _field(obj, key, default=None):
    """Return attribute or dict key for obj."""
    try:
        if hasattr(obj, key):
            return getattr(obj, key)
    except Exception:
        pass
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
    except Exception:
        pass
    return default

# Initialize IoT service (will be dependency-injected)
async def get_iot_service() -> IoTDeviceServiceFirestore:
    # Prefer Firestore-backed service for device data storage
    return IoTDeviceServiceFirestore()

# Additional service dependencies for intro audio
def get_openai_client():
    return OpenAI(api_key=settings.openai_api_key)

def get_storage_service():
    return StorageService()

def get_cartesia_service():
    return CartesiaService()

def get_media_service(openai_client: OpenAI = Depends(get_openai_client)):
    return MediaService(openai_client)

@router.post("/devices/create",
             response_model=DeviceInfo,
             summary="Create new device",
             description="Create a new device in the system - requires device secret")
async def create_device(
    request: CreateDeviceRequest,
    iot_service: IoTDeviceServiceFirestore = Depends(get_iot_service)
):
    """Create a new device with provided secret"""
    try:
        device = await iot_service.create_device(
            device_secret=request.device_secret,
            device_type=request.device_type.value,
            firmware_version=request.firmware_version
        )
        
        # Firestore service returns a dict, not an object
        return DeviceInfo(
            device_id=str(_field(device, "device_id")),
            device_name=_field(device, "device_name"),
            device_type=_field(device, "device_type"),
            status=_field(device, "status"),
            firmware_version=_field(device, "firmware_version"),
            owner_user_id=str(_field(device, "owner_user_id")) if _field(device, "owner_user_id") else None,
            claimed_at=_field(device, "claimed_at"),
            last_seen_at=_field(device, "last_seen_at"),
            created_at=_field(device, "created_at"),
            presence=None
        )
        
    except Exception as e:
        logger.error(f"Error creating device: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create device"
        )

@router.post("/devices/claim-token", 
             response_model=ClaimTokenResponse,
             summary="Generate device claim token",
             description="Creates a temporary token for device claiming by authenticated users")
async def create_claim_token(
    request: ClaimTokenRequest,
    # If client includes firebase_token in body we will verify it here.
    # If not present, we allow an optional header-based user via get_optional_current_user.
    current_user=Depends(get_optional_current_user),
    iot_service: IoTDeviceServiceFirestore = Depends(get_iot_service)
):
    """Generate a claim token for device onboarding"""
    try:
        logger.info(
            "🔍 /iot/devices/claim-token request",
            extra={
                "has_body_token": bool(request.firebase_token),
                "has_header_user": bool(current_user),
                "device_type": request.device_type.value if request.device_type else None
            }
        )
        # Allow client to pass firebase_token in body (mobile client flows may do this)
        if request.firebase_token:
            # verify_firebase_token returns uid string
            user_id = await verify_firebase_token(request.firebase_token)
        else:
            # current_user is a User object provided by header dependency
            if not current_user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Firebase credentials")
            user_id = current_user.uid

        logger.info("✅ /iot/devices/claim-token authenticated user", extra={"user_id": user_id})

        result = await iot_service.generate_claim_token(
            user_id=user_id,
            device_type=request.device_type.value if request.device_type else None
        )

        logger.info("✅ /iot/devices/claim-token generated token", extra={"user_id": user_id})
        
        return ClaimTokenResponse(
            claim_token=result["claim_token"],
            expires_in=result["expires_in"],
            expires_at=result["expires_at"],
            device_type=request.device_type.value if request.device_type else None
        )
        
    except HTTPException as http_error:
        logger.warning("⚠️ /iot/devices/claim-token HTTPException", exc_info=http_error)
        raise
    except Exception as e:
        logger.error(f"Error creating claim token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create claim token"
        )

@router.post("/devices/claim",
             response_model=ClaimDeviceResponse,
             summary="Claim device with token",
             description="Device uses claim token to bind to user account")
async def claim_device(
    request: ClaimDeviceRequest,
    device_id: str = Depends(get_hmac_auth_device),  # HMAC authentication required
    iot_service: IoTDeviceServiceFirestore = Depends(get_iot_service)
):
    """Claim a device using a valid claim token"""
    try:
        result = await iot_service.claim_device(
            device_id=device_id,
            claim_token=request.claim_token,
            device_name=request.device_name
        )
        
        return ClaimDeviceResponse(
            status=_field(result, "status"),
            user_id=_field(result, "user_id"),
            device_id=_field(result, "device_id"),
            device_name=_field(result, "device_name"),
            device_type=_field(result, "device_type")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error claiming device {device_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to claim device"
        )

@router.post("/devices/session",
             response_model=DeviceSessionResponse,
             summary="Get device session token",
             description="Generate JWT for authenticated device sessions")
async def get_device_session(
    device_id: str = Depends(get_hmac_auth_device),
    iot_service: IoTDeviceServiceFirestore = Depends(get_iot_service)
):
    """Generate a session JWT for device"""
    try:
        result = await iot_service.generate_device_session_token(device_id=device_id)

        return DeviceSessionResponse(
            device_jwt=result["device_jwt"],
            expires_in=result["expires_in"],
            device_id=device_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating session for device {device_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate session token"
        )

@router.post("/devices/heartbeat",
             response_model=HeartbeatResponse,
             summary="Send device heartbeat",
             description="Update device presence and status information")
async def device_heartbeat(
    request: HeartbeatRequest,
    auth_info = Depends(require_device_jwt),
    iot_service: IoTDeviceServiceFirestore = Depends(get_iot_service)
):
    """Process device heartbeat and update presence"""
    try:
        device_id = auth_info.device_id
        
        # Update device heartbeat in Firestore
        result = await iot_service.update_device_heartbeat(
            device_id=device_id,
            local_ip=request.local_ip,
            bssid=request.bssid,
            public_ip=None,
            rssi=request.rssi,
            firmware_version=request.firmware_version
        )
        
        return HeartbeatResponse(
            status=result["status"],
            timestamp=result["timestamp"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating heartbeat for device {device_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update heartbeat"
        )

@router.post("/devices/intro-audio",
             response_model=IntroAudioResponse,
             summary="Generate personalized intro audio (optimized)",
             description="Generate personalized intro audio with story suggestions for device wake-up - parallel processing")
async def generate_intro_audio_optimized(
    request: IntroAudioRequest,
    auth_info = Depends(require_device_jwt),
    iot_service: IoTDeviceServiceFirestore = Depends(get_iot_service),
    storage_service: StorageService = Depends(get_storage_service),
    cartesia_service: CartesiaService = Depends(get_cartesia_service),
    media_service: MediaService = Depends(get_media_service),
    openai_client: OpenAI = Depends(get_openai_client)
):
    """Generate personalized intro audio with parallel processing for reduced latency"""
    start_time = time.time()
    
    try:
        # Debug logging for auth_info
        logger.info(f"🔍 Auth info received: {auth_info}")
        logger.info(f"🔍 Auth info type: {type(auth_info)}")
        logger.info(f"🔍 Has device_id attr: {hasattr(auth_info, 'device_id')}")
        
        device_id = auth_info.device_id
        logger.info(f"🔍 Extracted device_id: {device_id} (type: {type(device_id)})")
        
        if not device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Device ID not found in authentication"
            )
        
        character_name = "June"  # Default character name
        
        # OPTIMIZATION 1: Parallel data fetching
        device_task = create_task(get_device_info(iot_service, device_id))
        story_task = create_task(get_story_suggestions(storage_service, request, device_id))

        # Wait for both data fetching tasks
        device_info, story_suggestions = await gather(device_task, story_task)
        
        data_fetch_time = time.time() - start_time
        logger.info(f"Data fetching completed in {data_fetch_time:.2f}s")
        
        # OPTIMIZATION 2: Parallel script generation with fallback
        script_start = time.time()
        scripts_task = create_task(generate_conversational_intro_scripts_fast(
            openai_client, character_name, request.device_name or "your storyteller", story_suggestions
        ))
        
        # While scripts are generating, prepare fallback scripts immediately
        fallback_scripts = get_fallback_scripts(character_name, story_suggestions)
        
        try:
            # Wait for OpenAI with timeout
            scripts = await asyncio.wait_for(scripts_task, timeout=3.0)
        except asyncio.TimeoutError:
            logger.warning("OpenAI script generation timed out, using fallback scripts")
            scripts = fallback_scripts
        except Exception as e:
            logger.warning(f"OpenAI script generation failed: {e}, using fallback scripts")
            scripts = fallback_scripts
        
        script_time = time.time() - script_start
        logger.info(f"Script generation completed in {script_time:.2f}s")
        
        # OPTIMIZATION 3: Parallel audio generation and upload to Firebase
        audio_start = time.time()
        audio_tasks = []
        
        # Create all audio generation and upload tasks simultaneously
        for i, script in enumerate(scripts):
            task = create_task(generate_and_upload_audio_file(
                script, i, device_id, cartesia_service, media_service, storage_service, device_info
            ))
            audio_tasks.append(task)
        
        # Process audio files as they complete (streaming approach)
        audio_results = []
        completed_tasks = []
        
        # Wait for all audio generation and upload with progress tracking
        for completed_task in asyncio.as_completed(audio_tasks):
            try:
                result = await completed_task
                audio_results.append(result)
                completed_tasks.append(completed_task)
                
                # Log progress
                progress = len(completed_tasks) / len(audio_tasks) * 100
                logger.info(f"Audio generation and upload progress: {progress:.0f}% ({len(completed_tasks)}/{len(audio_tasks)})")
                
            except Exception as e:
                logger.error(f"Audio generation/upload task failed: {e}")
                # Add fallback empty result
                audio_results.append({
                    'index': len(audio_results),
                    'file_url': '',
                    'voice_used': 'fallback',
                    'duration': 0.0
                })
        
        # Sort results by original order (since as_completed returns in completion order)
        audio_results.sort(key=lambda x: x.get('index', 0))
        
        audio_time = time.time() - audio_start
        logger.info(f"Audio generation and upload completed in {audio_time:.2f}s")
        
        # OPTIMIZATION 4: Efficient response preparation - link audio URLs to story suggestions
        all_audio_files = [result['file_url'] for result in audio_results]
        voice_used = audio_results[0]['voice_used'] if audio_results else 'unknown'
        total_duration = sum(result.get('duration', 0.0) for result in audio_results)
        
        # Link each audio URL to its corresponding story suggestion
        for i, story in enumerate(story_suggestions):
            if i < len(all_audio_files):
                story.intro_audio_url = all_audio_files[i]
        
        total_time = time.time() - start_time
        
        logger.info(f"🚀 OPTIMIZED INTRO AUDIO GENERATION COMPLETED:")
        logger.info(f"📊 Timing Breakdown:")
        logger.info(f"   📥 Data Fetching: {data_fetch_time:.2f}s")
        logger.info(f"   📝 Script Generation: {script_time:.2f}s") 
        logger.info(f"   🎵 Audio Generation: {audio_time:.2f}s")
        logger.info(f"   ⚡ Total Time: {total_time:.2f}s")
        logger.info(f"📱 Device ID: {device_id}")
        logger.info(f"🗣️  Character: {character_name}")
        logger.info(f"🎭 Voice Used: {voice_used}")
        logger.info(f"⏱️  Total Duration: {total_duration:.1f}s")
        
        response = IntroAudioResponse(
            audio_files=all_audio_files,
            story_suggestions=story_suggestions,
            total_duration_seconds=total_duration,
            voice_used=voice_used,
            character_name=character_name,
            timestamp=datetime.utcnow()
        )
        
        # Log the response as JSON
        try:
            import json
            response_dict = {
                "audio_files": response.audio_files,
                "story_suggestions": [
                    {
                        "story_id": s.story_id,
                        "title": s.title,
                        "intro_audio_url": s.intro_audio_url if hasattr(s, 'intro_audio_url') else None
                    } for s in response.story_suggestions
                ],
                "total_duration_seconds": response.total_duration_seconds,
                "voice_used": response.voice_used,
                "character_name": response.character_name,
                "timestamp": str(response.timestamp)
            }
            response_json = json.dumps(response_dict, indent=2)
            print(f"\n{'='*80}")
            print(f"RESPONSE SENT TO DEVICE {device_id}:")
            print(response_json)
            print(f"{'='*80}\n")
            logger.info(f"RESPONSE SENT: {response_json}")
        except Exception as e:
            print(f"ERROR logging response: {e}")
            logger.error(f"ERROR logging response: {e}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Error generating intro audio for device {device_id} after {total_time:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate intro audio"
        )

@router.post("/devices/intro-audio-files",
             response_model=IntroAudioFilesResponse,
             summary="Generate intro audio as downloadable WAV files",
             description="Generate personalized intro audio saved as WAV files with download URLs")
async def generate_intro_audio_files(
    request: IntroAudioRequest,
    auth_info = Depends(require_device_jwt),
    iot_service: IoTDeviceServiceFirestore = Depends(get_iot_service),
    storage_service: StorageService = Depends(get_storage_service),
    cartesia_service: CartesiaService = Depends(get_cartesia_service),
    media_service: MediaService = Depends(get_media_service),
    openai_client: OpenAI = Depends(get_openai_client)
):
    """Generate personalized intro audio saved as WAV files with download URLs"""
    start_time = time.time()
    
    try:
        device_id = auth_info.device_id
        character_name = "June"  # Default character name
        
        # OPTIMIZATION 1: Parallel data fetching
        device_task = create_task(get_device_info_for_intro_audio(iot_service, device_id))
        story_task = create_task(get_story_suggestions(storage_service, request, device_id))

        # Wait for both data fetching tasks
        device_info, story_suggestions = await gather(device_task, story_task)

        data_fetch_time = time.time() - start_time
        logger.info(f"Data fetching completed in {data_fetch_time:.2f}s")

        # OPTIMIZATION 2: Parallel script generation with fallback
        script_start = time.time()
        scripts_task = create_task(generate_conversational_intro_scripts_fast(
            openai_client, character_name, request.device_name or "your storyteller", story_suggestions
        ))

        # While scripts are generating, prepare fallback scripts immediately
        fallback_scripts = get_fallback_scripts(character_name, story_suggestions)

        try:
            # Wait for OpenAI with timeout
            scripts = await asyncio.wait_for(scripts_task, timeout=3.0)
        except asyncio.TimeoutError:
            logger.warning("OpenAI script generation timed out, using fallback scripts")
            scripts = fallback_scripts
        except Exception as e:
            logger.warning(f"OpenAI script generation failed: {e}, using fallback scripts")
            scripts = fallback_scripts

        script_time = time.time() - script_start
        logger.info(f"Script generation completed in {script_time:.2f}s")

        # OPTIMIZATION 3: Parallel audio generation and file upload
        audio_start = time.time()
        audio_tasks = []

        # Create all audio generation and upload tasks simultaneously
        for i, script in enumerate(scripts):
            task = create_task(generate_and_upload_audio_file(
                script, i, device_id, cartesia_service, media_service, storage_service, device_info
            ))
            audio_tasks.append(task)

        # Process audio files as they complete
        audio_results = []
        completed_tasks = []

        # Wait for all audio generation and upload with progress tracking
        for completed_task in asyncio.as_completed(audio_tasks):
            try:
                result = await completed_task
                audio_results.append(result)
                completed_tasks.append(completed_task)

                # Log progress
                progress = len(completed_tasks) / len(audio_tasks) * 100
                logger.info(f"Audio generation and upload progress: {progress:.0f}% ({len(completed_tasks)}/{len(audio_tasks)})")

            except Exception as e:
                logger.error(f"Audio generation/upload task failed: {e}")
                # Add fallback empty result
                audio_results.append({
                    'index': len(audio_results),
                    'file_url': '',
                    'voice_used': 'error',
                    'duration': 0.0
                })

        # Sort results by original order
        audio_results.sort(key=lambda x: x.get('index', 0))

        audio_time = time.time() - audio_start
        logger.info(f"Audio generation and upload completed in {audio_time:.2f}s")

        # OPTIMIZATION 4: Prepare response with file URLs - link to story suggestions
        audio_file_urls = [result['file_url'] for result in audio_results if result['file_url']]
        voice_used = audio_results[0]['voice_used'] if audio_results else 'unknown'
        total_duration = sum(result.get('duration', 0.0) for result in audio_results)
        
        # Link each audio URL to its corresponding story suggestion
        for i, story in enumerate(story_suggestions):
            if i < len(audio_file_urls):
                story.intro_audio_url = audio_file_urls[i]

        # Set expiration time (24 hours from now)
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(hours=24)

        total_time = time.time() - start_time

        logger.info(f"🚀 INTRO AUDIO FILES GENERATION COMPLETED:")
        logger.info(f"📊 Timing Breakdown:")
        logger.info(f"   📥 Data Fetching: {data_fetch_time:.2f}s")
        logger.info(f"   📝 Script Generation: {script_time:.2f}s") 
        logger.info(f"   🎵 Audio Generation + Upload: {audio_time:.2f}s")
        logger.info(f"   ⚡ Total Time: {total_time:.2f}s")
        logger.info(f"📱 Device ID: {device_id}")
        logger.info(f"🗣️  Character: {character_name}")
        logger.info(f"🎭 Voice Used: {voice_used}")
        logger.info(f"⏱️  Total Duration: {total_duration:.1f}s")
        logger.info(f"📁 Generated {len(audio_file_urls)} WAV files")

        return IntroAudioFilesResponse(
            audio_file_urls=audio_file_urls,
            story_suggestions=story_suggestions,
            total_duration_seconds=total_duration,
            voice_used=voice_used,
            character_name=character_name,
            timestamp=datetime.utcnow(),
            expires_at=expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Error generating intro audio files for device {device_id} after {total_time:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate intro audio files"
        )

async def get_device_info(iot_service: IoTDeviceServiceFirestore, device_id: str):
    """Async helper to get device information"""
    try:
        # Basic validation - just check device_id is not empty
        if not device_id or not isinstance(device_id, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid device ID format"
            )
        
        device_info = await iot_service.get_device(device_id)
        if not device_info or not device_info.get('owner_user_id'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found or not claimed"
            )
        return device_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device info: {str(e)}")
        raise

async def get_device_info_for_intro_audio(iot_service: IoTDeviceServiceFirestore, device_id: str):
    """Async helper to get device information for intro audio (allows unclaimed devices for testing)"""
    try:
        # Basic validation - just check device_id is not empty
        if not device_id or not isinstance(device_id, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid device ID format"
            )
        
        device_info = await iot_service.get_device(device_id)
        if not device_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )
        # Allow both claimed and unclaimed devices for intro audio testing
        return device_info
    except ValueError as e:
        logger.error(f"Invalid device ID format: {device_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device ID format"
        )
    except Exception as e:
        logger.error(f"Error getting device info: {str(e)}")
        raise

async def get_story_suggestions(storage_service: StorageService, request: IntroAudioRequest, device_id: str) -> List[StoryPreview]:
    """Async helper to get story suggestions - fetches latest 5 stories for the device owner"""
    story_suggestions = []
    
    # ALWAYS try to fetch user stories (ignore include_story_suggestions flag)
    try:
        # Get device info to retrieve owner_user_id
        db = get_firestore_client()
        
        logger.info(f"🔍 Fetching device document for device_id: {device_id}")
        device_doc = db.collection('devices').document(device_id).get()
        
        if device_doc.exists:
            device_data = device_doc.to_dict()
            owner_user_id = device_data.get('owner_user_id')
            
            logger.info(f"🔍 Device found. owner_user_id: {owner_user_id}")
            
            if owner_user_id:
                logger.info(f"📚 Fetching latest 5 stories for user {owner_user_id}")
                
                # Step 1: Get user's story_ids array
                user_ref = db.collection('users').document(owner_user_id)
                user_doc = user_ref.get()
                
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    story_ids = user_data.get('story_ids', [])
                    
                    logger.info(f"📋 User has {len(story_ids)} total stories in story_ids array")
                    
                    if story_ids:
                        # Get the latest 5 story IDs (reverse order - newest first)
                        latest_story_ids = list(reversed(story_ids))[:5]
                        logger.info(f"🎯 Fetching details for latest 5 story IDs: {latest_story_ids}")
                        
                        # Step 2: Fetch story details from top-level 'stories' collection
                        stories_ref = db.collection('stories')
                        
                        story_count = 0
                        for story_id in latest_story_ids:
                            try:
                                story_doc = stories_ref.document(story_id).get()
                                
                                if story_doc.exists:
                                    story_data = story_doc.to_dict()
                                    story_count += 1
                                    
                                    # Extract story information with metadata
                                    user_prompt = story_data.get('user_prompt', '')
                                    metadata = story_data.get('metadata', {})
                                    
                                    # Build description from available data
                                    description_parts = []
                                    if user_prompt:
                                        description_parts.append(user_prompt[:150])
                                    if metadata:
                                        if metadata.get('character_name'):
                                            description_parts.append(f"Character: {metadata.get('character_name')}")
                                        if metadata.get('theme'):
                                            description_parts.append(f"Theme: {metadata.get('theme')}")
                                    
                                    description = '. '.join(description_parts) if description_parts else 'A wonderful story'
                                    
                                    story_preview = StoryPreview(
                                        story_id=story_doc.id,
                                        title=story_data.get('title', 'Untitled Story'),
                                        description=description[:250],
                                        created_at=story_data.get('created_at', datetime.utcnow()),
                                        thumbnail_url=story_data.get('thumbnail_url')
                                    )
                                    story_suggestions.append(story_preview)
                                    logger.info(f"  ✅ Story {story_count}: {story_doc.id} - {story_data.get('title', 'Untitled')}")
                                else:
                                    logger.warning(f"  ⚠️ Story {story_id} not found in stories collection")
                            except Exception as e:
                                logger.error(f"  ❌ Error fetching story {story_id}: {e}")
                        
                        logger.info(f"📊 Successfully fetched {len(story_suggestions)} user stories")
                    else:
                        logger.info(f"📭 User has no stories in story_ids array")
                else:
                    logger.warning(f"⚠️ User document {owner_user_id} not found in Firestore")
            else:
                logger.warning(f"⚠️ Device {device_id} exists but has no owner_user_id")
        else:
            logger.warning(f"⚠️ Device {device_id} not found in Firestore")
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch user stories: {str(e)}", exc_info=True)
    
    # If we have fewer than 5 stories, fill with defaults
    if len(story_suggestions) < 5:
        logger.warning(f"⚠️ Only {len(story_suggestions)} user stories found, filling with {5 - len(story_suggestions)} default stories")
        
        default_stories_data = [
            {"title": "The Magic Forest Adventure", "description": "A tale of wonder in an enchanted forest"},
            {"title": "The Brave Little Mouse", "description": "A small mouse with a big heart"},
            {"title": "The Dancing Clouds", "description": "When clouds come alive in the sky"},
            {"title": "The Secret Garden", "description": "A hidden garden full of surprises"},
            {"title": "The Friendly Dragon", "description": "A dragon who just wants to make friends"}
        ]
        
        # Add defaults to fill up to 5
        for i in range(len(story_suggestions), 5):
            story_data = default_stories_data[i] if i < len(default_stories_data) else default_stories_data[0]
            story_preview = StoryPreview(
                story_id=f"default_{i + 1}",
                title=story_data["title"],
                description=story_data["description"],
                created_at=datetime.utcnow(),
                thumbnail_url=None
            )
            story_suggestions.append(story_preview)
            logger.info(f"  📝 Added default story: default_{i + 1} - {story_data['title']}")
    
    logger.info(f"📋 Returning {len(story_suggestions)} total stories ({len([s for s in story_suggestions if not s.story_id.startswith('default')])} user + {len([s for s in story_suggestions if s.story_id.startswith('default')])} default)")
    return story_suggestions[:5]  # Always return exactly 5

def get_default_stories(count: int) -> List[StoryPreview]:
    """Get default story suggestions"""
    default_stories = [
        {"title": "The Magic Forest Adventure", "description": "A tale of wonder in an enchanted forest"},
        {"title": "The Brave Little Mouse", "description": "A small mouse with a big heart"},
        {"title": "The Dancing Clouds", "description": "When clouds come alive in the sky"},
        {"title": "The Secret Garden", "description": "A hidden garden full of surprises"},
        {"title": "The Friendly Dragon", "description": "A dragon who just wants to make friends"}
    ]
    
    stories = []
    for i in range(min(count, len(default_stories))):
        story = default_stories[i]
        stories.append(StoryPreview(
            story_id=f"default_{i + 1}",
            title=story["title"],
            description=story["description"],
            created_at=datetime.utcnow(),
            thumbnail_url=None
        ))
    
    return stories

def get_fallback_scripts(character_name: str, story_suggestions: List[StoryPreview]) -> List[str]:
    """Get immediate fallback scripts without API call"""
    stories = story_suggestions[:5]
    
    scripts = []
    
    # First script: Initial greeting
    scripts.append(
        f"Hi! I am {character_name}! I would like to tell you a story. How about a story about {stories[0].title}?"
    )
    
    # Scripts 2-5: Rejection responses
    for i in range(1, 5):
        if i < len(stories):
            scripts.append(
                f"Oh, you didn't like that one? How about a story about {stories[i].title}?"
            )
        else:
            scripts.append(
                f"How about this one instead? It's a wonderful story!"
            )
    
    return scripts

async def generate_conversational_intro_scripts_fast(
    openai_client: OpenAI,
    character_name: str,
    device_name: str,
    story_suggestions: List[StoryPreview]
) -> List[str]:
    """Optimized script generation for June character with story-specific intros using metadata"""
    
    stories = story_suggestions[:5]
    
    # Build story details with metadata for better context
    story_details = []
    for i, story in enumerate(stories, 1):
        detail = f'Story {i}: "{story.title}"'
        if story.description and story.description.strip():
            detail += f' - {story.description}'
        story_details.append(detail)
    
    stories_text = '\n'.join(story_details)
    
    # Create specific prompt for June character with story metadata
    prompt = f"""Create 5 short intro audio scripts for {character_name}, who greets children and suggests stories.

{stories_text}

Requirements:
- Script 1: "{character_name} introduces herself and suggests the first story based on its title and description"
  Format: "Hi! I am {character_name}! I would like to tell you a story. How about [brief exciting description of Story 1]?"
  
- Scripts 2-5: After child rejects previous story, suggest the next one with enthusiasm
  Format: "Oh, you didn't like that one? How about [brief exciting description of Story N]?"

Make each description engaging and child-friendly. Keep each script under 15 seconds when spoken.
Return ONLY a JSON array of 5 strings, no other text."""

    try:
        # Use faster model and optimized parameters
        loop = get_or_create_event_loop()
        
        def generate_scripts():
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Faster than GPT-4
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,  # Lower for consistency and speed
                max_tokens=400    # Reduced token limit
            )
            return response.choices[0].message.content.strip()
        
        content = await loop.run_in_executor(None, generate_scripts)
        
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        
        scripts = json.loads(content)
        
        # Ensure exactly 5 scripts
        if len(scripts) != 5:
            raise ValueError(f"Expected 5 scripts, got {len(scripts)}")
        
        return scripts
        
    except Exception as e:
        logger.error(f"Fast script generation failed: {str(e)}")
        # Return fallback scripts
        return get_fallback_scripts(character_name, story_suggestions)

async def generate_single_audio_optimized(
    script: str, 
    index: int, 
    cartesia_service: CartesiaService, 
    media_service: MediaService,
    device_info: dict
) -> Dict[str, Any]:
    """Generate a single audio file - ALWAYS uses Cartesia default voice (no custom clones)"""
    try:
        start_time = time.time()
        
        # ALWAYS use Cartesia default voice for intro audio
        # (Custom voice clones are only for full stories)
        try:
            default_voice_id = cartesia_service.default_voice_id
            audio_data = await cartesia_service.generate_speech_cartesia(
                text=script,
                voice_id=default_voice_id
            )
            voice_used = "cartesia_default"
            logger.info(f"✅ Intro audio {index+1} generated with Cartesia default voice")
            
        except Exception as e:
            logger.warning(f"Cartesia failed for audio {index+1}, using OpenAI: {str(e)}")
            # Fallback to OpenAI TTS
            audio_data = await media_service.generate_audio_openai(
                text=script,
                scene_number=index+1,
                isfemale=True
            )
            voice_used = "openai_sage"
        
        # Convert to Opus format (same as story audio)
        try:
            from app.utils.audio_processor import AudioProcessor
            processed_audio, content_type, _ = AudioProcessor.process_for_web_delivery(
                audio_data, source_format="auto"
            )
            logger.info(f"🎵 Intro audio {index+1} converted to {content_type}")
            audio_data = processed_audio
        except Exception as e:
            logger.warning(f"Audio processing failed for intro {index+1}, using original format: {str(e)}")
        
        # Convert to base64 efficiently
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Estimate duration (rough: 150 words per minute)
        duration = len(script) / 5 / 150 * 60  # chars to words to minutes to seconds
        
        generation_time = time.time() - start_time
        logger.debug(f"Audio {index+1} generated in {generation_time:.2f}s")
        
        return {
            'index': index,
            'audio_b64': audio_b64,
            'voice_used': voice_used,
            'duration': duration
        }
        
    except Exception as e:
        logger.error(f"Failed to generate audio {index+1}: {str(e)}")
        return {
            'index': index,
            'audio_b64': '',
            'voice_used': 'error',
            'duration': 0.0
        }

async def generate_and_upload_audio_file(
    script: str,
    index: int,
    device_id: str,
    cartesia_service: CartesiaService,
    media_service: MediaService,
    storage_service: StorageService,
    device_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate audio and upload as OGG file, return download URL - uses custom voice clone if available"""
    try:
        start_time = time.time()
        
        # Check if device has owner and if owner has custom voice clone
        custom_voice_id = None
        owner_user_id = None
        
        if device_info and 'owner_user_id' in device_info:
            owner_user_id = device_info.get('owner_user_id')
            
            if owner_user_id:
                try:
                    # Check if user has custom voice clone
                    db = get_firestore_client()
                    user_doc = db.collection('users').document(owner_user_id).get()
                    
                    if user_doc.exists:
                        user_data = user_doc.to_dict()
                        # Note: 'elevenlabs_voice_id' kept for backward compatibility with existing data
                        # Cartesia now handles all voice cloning but field name preserved
                        custom_voice_id = user_data.get('elevenlabs_voice_id')
                        
                        if custom_voice_id:
                            logger.info(f"🎤 Found custom voice clone for user {owner_user_id}: {custom_voice_id}")
                        else:
                            logger.info(f"🎤 No custom voice clone for user {owner_user_id}, using default")
                            
                except Exception as e:
                    logger.warning(f"Failed to check for custom voice clone: {str(e)}")
        
        # Try Cartesia first (usually faster)
        try:
            # Use custom voice if available, otherwise default
            voice_id = custom_voice_id if custom_voice_id else cartesia_service.default_voice_id
            voice_type = "custom" if custom_voice_id else "default"
            
            logger.info(f"🎤 Generating intro audio {index+1} with Cartesia {voice_type} voice")
            
            audio_data = await cartesia_service.generate_speech_cartesia(
                text=script,
                voice_id=voice_id
            )
            voice_used = f"cartesia_{voice_type}"
            logger.info(f"✅ Intro audio {index+1} generated with Cartesia {voice_type} voice")
            
        except Exception as e:
            logger.warning(f"Cartesia failed for audio {index+1}, using OpenAI: {str(e)}")
            # Fallback to OpenAI TTS
            audio_data = await media_service.generate_audio_openai(
                text=script,
                scene_number=index+1,
                isfemale=True
            )
            voice_used = "openai_sage"
        
        # Convert to Opus format (same as story audio)
        file_extension = "opus"
        content_type = "audio/ogg"
        try:
            from app.utils.audio_processor import AudioProcessor
            from app.utils.opus_encoder import OpusEncoder
            
            processed_audio, content_type, content_hash = AudioProcessor.process_for_web_delivery(
                audio_data, source_format="auto"
            )
            
            # Create versioned filename with content hash
            base_filename = f"intro_{index+1}"
            logger.info(f"Content type returned: '{content_type}'")
            
            if content_type in ["audio/ogg", "audio/opus"]:
                versioned_filename = OpusEncoder.create_versioned_filename(base_filename, content_hash, "opus")
                file_extension = "opus"
                logger.info(f"Using OPUS extension: {versioned_filename}")
            else:
                # Fallback format
                file_extension = "mp3"
                versioned_filename = f"{base_filename}-{content_hash}.{file_extension}"
                logger.warning(f"Using MP3 fallback (content_type was: '{content_type}')")
            
            logger.info(f"Intro audio {index+1} converted to {content_type} -> {versioned_filename}")
            audio_data = processed_audio
            
        except Exception as e:
            logger.warning(f"Audio processing failed for intro {index+1}, using original format: {str(e)}")
            # Use timestamp-based filename if processing fails
            import time as time_module
            timestamp = int(time_module.time())
            versioned_filename = f"intro_{index+1}_{timestamp}.mp3"
            file_extension = "mp3"
            content_type = "audio/mpeg"
        
        # Upload to storage with unique filename in intro-audios directory
        filename = f"intro-audios/{device_id}/{versioned_filename}"
        
        # Upload to Firebase Storage
        try:
            file_url = await storage_service.upload_audio_file(
                audio_data=audio_data,
                filename=filename,
                content_type=content_type
            )
        except Exception as upload_error:
            logger.error(f"Failed to upload audio file {index+1}: {upload_error}")
            # Return local fallback or empty URL
            file_url = ""
        
        # Estimate duration (rough: 150 words per minute)
        duration = len(script) / 5 / 150 * 60  # chars to words to minutes to seconds
        
        generation_time = time.time() - start_time
        logger.debug(f"Audio {index+1} generated and uploaded in {generation_time:.2f}s")
        
        return {
            'index': index,
            'file_url': file_url,
            'voice_used': voice_used,
            'duration': duration
        }
        
    except Exception as e:
        logger.error(f"Failed to generate and upload audio {index+1}: {str(e)}")
        return {
            'index': index,
            'file_url': '',
            'voice_used': 'error',
            'duration': 0.0
        }


@router.get("/health",
            response_model=HealthCheckResponse,
            summary="IoT system health check",
            description="Check health of IoT system components")
async def health_check(
    iot_service: IoTDeviceServiceFirestore = Depends(get_iot_service)
):
    """Health check for IoT system"""
    try:
        # Check Firestore connectivity
        try:
            client = iot_service.client
            # Firestore simple call
            client.collections()
            db_health = {"connected": True}
        except Exception as e:
            logger.warning(f"Firestore health check failed: {e}")
            db_health = {"connected": False}
        
        # Check in-memory stores
        memory_health = {
            "rate_limiter": "healthy",
            "token_cache": "healthy"
        }
        
        # Get basic stats if database is healthy
        stats = {
            "uptime": "unknown",
            "active_devices": 0
        }
        
        if db_health.get("connected", False):
            try:
                # Optionally implement get_device_stats on Firestore service
                if hasattr(iot_service, 'get_device_stats'):
                    device_stats = await iot_service.get_device_stats()
                    stats.update(device_stats)
            except Exception as e:
                logger.warning(f"Failed to get device stats: {str(e)}")
        
        return HealthCheckResponse(
            status="healthy" if db_health.get("connected", False) else "unhealthy",
            database=db_health,
            in_memory_stores=memory_health,
            device_stats=stats,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="IoT system health check failed"
        )
