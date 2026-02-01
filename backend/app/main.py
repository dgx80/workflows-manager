"""FastAPI application for CICD Monitor."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import events, websocket

app = FastAPI(
    title="CICD Monitor API",
    description="Real-time monitoring API for CICD workflows",
    version="0.1.0",
)

# CORS configuration for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # SolidStart dev
        "http://localhost:5173",  # Vite dev
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(events.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "cicd-monitor"}


@app.get("/health")
async def health():
    """Health check for container orchestration."""
    return {"status": "healthy"}
