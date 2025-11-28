"""
NTP/SNTP Time Synchronization Endpoint
Provides time synchronization compatible with NTP protocol format
"""
from fastapi import APIRouter, Response
from datetime import datetime, timezone
import struct
import time

router = APIRouter(
    prefix="/ntp",
    tags=["time"],
)

# NTP constants
NTP_EPOCH = 2208988800  # Seconds between 1900-01-01 and 1970-01-01
NTP_VERSION = 3
NTP_MODE_SERVER = 4


def system_to_ntp_time(timestamp):
    """Convert Unix timestamp to NTP timestamp (seconds since 1900-01-01)"""
    return int(timestamp) + NTP_EPOCH


def get_ntp_timestamp():
    """Get current time as NTP timestamp"""
    return system_to_ntp_time(time.time())


@router.get("/time")
async def get_ntp_time_json():
    """
    Get current server time in NTP-compatible JSON format
    
    Response format matches Google's NTP server behavior:
    - Returns current UTC time
    - Provides both Unix and NTP timestamps
    - Includes precision and stratum information
    
    Example response:
    {
        "utc": "2025-10-25T10:30:45.123456Z",
        "unix_timestamp": 1729853445.123456,
        "ntp_timestamp": 3938842245,
        "stratum": 1,
        "precision": -20,
        "root_delay": 0.0,
        "root_dispersion": 0.0
    }
    """
    now = datetime.now(timezone.utc)
    unix_time = now.timestamp()
    ntp_time = system_to_ntp_time(unix_time)
    
    return {
        "utc": now.isoformat(),
        "unix_timestamp": unix_time,
        "ntp_timestamp": ntp_time,
        "stratum": 1,  # Primary time source (mimics Google's NTP)
        "precision": -20,  # ~1 microsecond precision
        "root_delay": 0.0,
        "root_dispersion": 0.0,
        "leap_indicator": 0,  # No leap second warning
        "version": NTP_VERSION,
        "mode": NTP_MODE_SERVER
    }


@router.get("/time/binary")
async def get_ntp_time_binary():
    """
    Get current server time in NTP binary packet format (48 bytes)
    
    This endpoint returns a binary NTP packet similar to what Google's NTP server returns.
    The packet follows RFC 5905 NTP v4 specification.
    
    Packet structure (48 bytes):
    - Bytes 0-3: LI (2 bits), VN (3 bits), Mode (3 bits), Stratum, Poll, Precision
    - Bytes 4-7: Root Delay
    - Bytes 8-11: Root Dispersion
    - Bytes 12-15: Reference ID
    - Bytes 16-23: Reference Timestamp
    - Bytes 24-31: Origin Timestamp
    - Bytes 32-39: Receive Timestamp
    - Bytes 40-47: Transmit Timestamp
    
    Usage:
    curl -X GET http://your-server/ntp/time/binary --output ntp.bin
    """
    now = time.time()
    ntp_timestamp = system_to_ntp_time(now)
    
    # NTP packet format (48 bytes)
    # Byte 0: LI (2 bits) = 0, VN (3 bits) = 3, Mode (3 bits) = 4
    li_vn_mode = (0 << 6) | (NTP_VERSION << 3) | NTP_MODE_SERVER
    
    # Build NTP packet
    packet = struct.pack(
        '!BBBbIIIQQQQ',
        li_vn_mode,      # LI, VN, Mode
        1,               # Stratum (1 = primary reference)
        0,               # Poll interval
        -20,             # Precision (~1 microsecond)
        0,               # Root delay
        0,               # Root dispersion
        0x474f4f47,      # Reference ID ('GOOG' in hex, mimicking Google)
        ntp_timestamp << 32,  # Reference timestamp (high 32 bits seconds, low 32 bits fraction)
        0,               # Origin timestamp
        ntp_timestamp << 32,  # Receive timestamp
        ntp_timestamp << 32   # Transmit timestamp
    )
    
    return Response(content=packet, media_type="application/octet-stream")


@router.get("/time/rfc3339")
async def get_time_rfc3339():
    """
    Get current server time in RFC3339 format (ISO 8601)
    
    This is a simple endpoint that returns just the current UTC time
    in a standard format, useful for simple time synchronization.
    
    Example response:
    {
        "time": "2025-10-25T10:30:45.123456Z"
    }
    """
    now = datetime.now(timezone.utc)
    return {
        "time": now.isoformat(),
        "format": "RFC3339"
    }


@router.get("/health")
async def ntp_health():
    """
    Health check endpoint for NTP service
    Returns current time and server status
    """
    return {
        "status": "healthy",
        "service": "NTP Time Sync",
        "current_time": datetime.now(timezone.utc).isoformat(),
        "endpoints": [
            "/ntp/time - JSON format with NTP details",
            "/ntp/time/binary - Binary NTP packet (48 bytes)",
            "/ntp/time/rfc3339 - Simple RFC3339 timestamp"
        ]
    }
