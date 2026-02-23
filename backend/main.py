"""
WASTE IQ – FastAPI Backend Entry Point
Handles all REST API routes with Firebase Authentication.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (waste_iq/) — works regardless of launch directory
load_dotenv(Path(__file__).parent.parent / ".env")

# Import routers
from routers import auth_router, bins_router, classify_router, complaints_router
from routers import gamification_router, overflow_router, reports_router, routing_router
from waste_classifier import WasteClassifier
from overflow_model import OverflowModel

app = FastAPI(
    title="WASTE IQ API",
    description="Production-ready Waste Management REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup: pre-load ML models ───────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    print("🚀 WASTE IQ Backend starting up...")
    try:
        app.state.classifier = WasteClassifier()
        print("✅ WasteClassifier loaded")
    except Exception as e:
        print(f"⚠️  WasteClassifier unavailable (TensorFlow not installed): {e}")
        app.state.classifier = None
    try:
        app.state.overflow_model = OverflowModel()
        print("✅ OverflowModel loaded")
    except Exception as e:
        print(f"⚠️  OverflowModel unavailable: {e}")
        app.state.overflow_model = None
    print("🟢 Backend ready — http://localhost:8000/docs")

# ── Shutdown ──────────────────────────────────────────────────────────────────
@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 WASTE IQ Backend shutting down...")

# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "healthy",
        "service": "WASTE IQ API",
        "version": "1.0.0"
    }

# ── Register Routers ──────────────────────────────────────────────────────────
app.include_router(auth_router.router,         prefix="/auth",         tags=["auth"])
app.include_router(bins_router.router,         prefix="/bins",         tags=["bins"])
app.include_router(classify_router.router,     prefix="/classify",     tags=["classify"])
app.include_router(complaints_router.router,   prefix="/complaints",   tags=["complaints"])
app.include_router(gamification_router.router, prefix="/gamification", tags=["gamification"])
app.include_router(overflow_router.router,     prefix="/overflow",     tags=["overflow"])
app.include_router(reports_router.router,      prefix="/reports",      tags=["reports"])
app.include_router(routing_router.router,      prefix="/route",        tags=["routing"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development"
    )
