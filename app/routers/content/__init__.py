"""Content management routers."""
from .stories import router as stories_router
from .children import router as children_router
from .reference_images import router as reference_images_router

__all__ = ['stories_router', 'children_router', 'reference_images_router']
