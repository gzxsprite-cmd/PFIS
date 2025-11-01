from fastapi import APIRouter

from . import metrics, products

router = APIRouter(prefix="/product_tracker", tags=["Product Tracker"])
router.include_router(products.router)
router.include_router(metrics.router)

__all__ = ["router"]
