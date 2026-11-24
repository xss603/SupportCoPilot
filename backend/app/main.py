from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import async_session_factory, init_db
from app.api.endpoints.actions import router as actions_router
from app.api.endpoints.audit import router as audit_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.feedback import router as feedback_router
from app.api.endpoints.issues import router as issues_router
from app.api.endpoints.knowledge import router as knowledge_router
from app.api.endpoints.rules import router as rules_router
from app.api.endpoints.stats import router as stats_router
from app.api.endpoints.webhooks import router as webhook_router
from app.rag.crawler import docs_crawler


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Initializing database schema and pgvector extension...")
    try:
        await init_db()
        print("✅ Database tables successfully created.")
    except Exception as e:
        print(f"Notice during DB init: {e}")

    try:
        async with async_session_factory() as db:
            count = await docs_crawler.index_local_runbooks(db, runbooks_dir="./runbooks")
            print(f"📚 Indexed {count} local runbook chunks into vector store.")
    except Exception as e:
        print(f"Notice during runbook indexing: {e}")

    yield

    print("🛑 Shutting down GitLab Support Automation Platform...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Event-Driven GitLab Support Automation & Triage Platform with Hybrid RAG & Co-Pilot Workbench",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware (no wildcard '*' with allow_credentials=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all 9 API Routers under /api/v1
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(webhook_router, prefix=settings.API_V1_STR)
app.include_router(issues_router, prefix=settings.API_V1_STR)
app.include_router(actions_router, prefix=settings.API_V1_STR)
app.include_router(knowledge_router, prefix=settings.API_V1_STR)
app.include_router(rules_router, prefix=settings.API_V1_STR)
app.include_router(feedback_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(stats_router, prefix=settings.API_V1_STR)


@app.get("/healthz", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "mode": "Co-Pilot" if not settings.ENABLE_AUTO_EXECUTION else "Auto-Pilot",
        "model": settings.LLM_MODEL,
    }
