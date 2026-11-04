from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes.health import router as health_router
from app.api.routes.datasets import router as datasets_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.cleaning import router as cleaning_router
from app.api.routes.ai_understanding import router as ai_understanding_router
from app.api.routes.ask_data import router as ask_data_router
from app.api.routes.automated_insights import router as automated_insights_router
from app.api.routes.reports import router as reports_router

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGIN,
    allow_origin_regex=settings.FRONTEND_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(datasets_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(cleaning_router, prefix="/api/v1")
app.include_router(ai_understanding_router, prefix="/api/v1")
app.include_router(ask_data_router, prefix="/api/v1")
app.include_router(automated_insights_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "tagline": "Your Autonomous Data Analyst",
        "brand": "Powered by Saniya",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/api/v1/health",
    }
