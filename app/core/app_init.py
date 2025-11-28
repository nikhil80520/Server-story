"""
Application initialization and startup/shutdown event handlers.
"""
import logging
from fastapi import FastAPI

from app.core.config import settings
from app.utils.firebase_init import initialize_firebase

logger = logging.getLogger(__name__)


def init_firebase() -> None:
    """Initialize Firebase before anything else."""
    initialize_firebase()
    logger.info("✅ Firebase initialized")


def init_openai() -> None:
    """Initialize and test OpenAI API key."""
    if settings.openai_api_key and settings.openai_api_key != "test":
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=settings.openai_api_key,
                timeout=60.0
            )
            logger.info("✅ OpenAI client initialized successfully (60s timeout)")
            logger.info("🎵 Using OpenAI TTS for audio generation")
        except Exception as e:
            logger.warning(f"⚠️ OpenAI initialization failed: {str(e)}")
    else:
        logger.warning("⚠️ OpenAI API key not configured - story generation will not work")


def init_sentry() -> None:
    """Initialize Sentry error tracking."""
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn="https://486344263e9d7536d5219194c7987cf3@o4509915720450048.ingest.de.sentry.io/4509915728183376",
            send_default_pii=True,
        )
        logger.info("✅ Sentry error tracking initialized")
    except Exception as e:
        logger.warning(f"⚠️ Sentry initialization failed: {str(e)}")


def register_routers(app: FastAPI) -> tuple[bool, bool]:
    """
    Register all application routers.
    
    Returns:
        Tuple of (stories_loaded, iot_loaded) booleans
    """
    # Core routers (always available)
    from app.routers.auth import auth, users
    from app.routers.content import children, reference_images
    from app.routers.iot import ntp
    from app.routers.system import health, admin, analytics, notifications
    
    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(users.router)
    app.include_router(children.router)
    app.include_router(reference_images.router)
    app.include_router(ntp.router)
    app.include_router(admin.router)
    app.include_router(analytics.router)
    app.include_router(notifications.router)
    
    logger.info("✅ Core routers registered (including notifications)")
    
    # Optional: Lullabies router
    try:
        from app.routers.content import lullabies
        app.include_router(lullabies.router)
        logger.info("✅ Lullabies router loaded")
    except ImportError as e:
        logger.warning(f"⚠️ Lullabies router not loaded (missing dependencies): {e}")
    except Exception as e:
        logger.error(f"❌ Lullabies router failed: {e}")
    
    # Optional: Conversational AI router
    try:
        from app.routers.social import conversation
        app.include_router(conversation.router)
        logger.info("✅ Conversational AI router loaded")
    except ImportError as e:
        logger.warning(f"⚠️ Conversational AI router not loaded (missing dependencies): {e}")
    except Exception as e:
        logger.error(f"❌ Conversational AI router failed: {e}")
    
    # Optional: Stories router
    stories_loaded = False
    try:
        from app.routers.content import stories
        from app.routers.social import websocket, lullaby_websocket
        app.include_router(stories.router)
        app.include_router(websocket.router)
        app.include_router(lullaby_websocket.router)
        stories_loaded = True
        logger.info("✅ Story and WebSocket routers loaded")
    except ImportError as e:
        logger.warning(f"⚠️ Story routers not loaded: {e}")
    except Exception as e:
        logger.error(f"❌ Story routers failed: {e}")
    
    # Optional: IoT router
    iot_loaded = False
    try:
        from app.routers.iot import iot
        app.include_router(iot.router)
        iot_loaded = True
        logger.info("✅ IoT router loaded")
    except ImportError as e:
        logger.warning(f"⚠️ IoT router not loaded: {e}")
    except Exception as e:
        logger.error(f"❌ IoT router failed: {e}")
    
    return stories_loaded, iot_loaded


async def startup_handler(app: FastAPI, stories_loaded: bool, iot_loaded: bool) -> None:
    """Handle application startup tasks."""
    logger.info("🚀 ESP32 Storytelling Server started successfully!")
    logger.info(f"📊 Environment: {'Development' if settings.debug else 'Production'}")
    logger.info(f"🌐 CORS Origins: {settings.cors_origins_list}")
    
    if not stories_loaded:
        logger.warning("⚠️ Story router not loaded — /stories endpoints unavailable")
    if not iot_loaded:
        logger.warning("⚠️ IoT router not loaded — /iot endpoints unavailable")
    
    # Log registered routes
    logger.info("🛣️ Registered routes:")
    for route in app.router.routes:
        methods = getattr(route, "methods", None)
        if methods:
            logger.info(f"   {route.path} -> {','.join(sorted(methods))}")
    
    # Start background services
    try:
        from app.services.infrastructure.enhanced_background_service import enhanced_background_service
        await enhanced_background_service.start(num_workers=settings.background_workers)
        logger.info("✅ Enhanced background service started")
    except Exception as e:
        logger.warning(f"⚠️ Enhanced background service failed: {e}")
    
    # Note: MQTT service has been consolidated into app.routers.iot.IoTDeviceServiceFirestore
    
    logger.info("🤖 AI Services:")
    logger.info(f"  - OpenAI: {'✅ Configured' if settings.openai_api_key and settings.openai_api_key != 'test' else '❌ Not configured'}")
    logger.info(f"  - Firebase: ✅ Connected")
    logger.info("📖 Story Generation: OpenAI TTS with Full Parallel Processing")


async def shutdown_handler() -> None:
    """Handle application shutdown tasks."""
    logger.info("🛑 Shutting down ESP32 Storytelling Server...")
    
    # Cleanup conversational AI
    try:
        from app.routers.social.conversation import cleanup_conversations
        await cleanup_conversations()
        logger.info("✅ Conversational AI cleaned up")
    except Exception as e:
        logger.warning(f"⚠️ Error cleaning up conversational AI: {e}")
    
    # Stop background service
    try:
        from app.services.infrastructure.enhanced_background_service import enhanced_background_service
        await enhanced_background_service.stop()
        logger.info("✅ Enhanced background service stopped")
    except Exception as e:
        logger.warning(f"⚠️ Error stopping background service: {e}")
    
    # Note: MQTT service has been consolidated into app.routers.iot.IoTDeviceServiceFirestore
    
    logger.info("🛑 Server shutdown complete")
