from fastapi import APIRouter

from app.api.routes import admin, auth, customer, desktop, downloads, health, payments, public, support

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(public.router, prefix="/public", tags=["public"])
api_router.include_router(customer.router, prefix="/customer", tags=["customer"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(desktop.router, prefix="/desktop", tags=["desktop"])
api_router.include_router(downloads.router, prefix="/downloads", tags=["downloads"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(support.router, prefix="/support", tags=["support"])
