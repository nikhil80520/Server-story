"""
Routers package - organized by functional area.

Structure:
- auth/: Authentication and user management routers
- content/: Stories, children, and reference images routers
- social/: Sharing, conversation, and websocket routers
- iot/: IoT device and NTP routers
- system/: Health, analytics, and admin routers
"""

# Re-export routers for backward compatibility (if needed)
# Individual routers can be imported from their subdirectories:
# from app.routers.auth import auth, users
# from app.routers.content import stories, children, reference_images
# from app.routers.social import sharing, conversation, websocket
# from app.routers.iot import iot, ntp
# from app.routers.system import health, analytics, admin
