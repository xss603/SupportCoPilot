from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import async_session_factory, get_db
from app.models.entities import CrawlerSyncRun, DocChunk, DocsDriftCluster
from app.rag.crawler import docs_crawler
from app.rag.hybrid_retriever import hybrid_retriever
from app.schemas.knowledge import (
    CrawlerSyncRunSchema,
    CrawlRequest,
    CrawlTriggerResponse,
    DocChunkItem,
    DocDraftResponse,
    DocsDriftClusterSchema,
    RAGPlaygroundResponse,
    RAGQueryRequest,
    RAGQueryResultItem,
)

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base & RAG"])


async def run_background_crawler(source_type: str, url: Optional[str] = None):
    async with async_session_factory() as db:
        if source_type == "runbooks":
            await docs_crawler.index_local_runbooks(db)
        elif url:
            await docs_crawler.crawl_web_page(db, url=url, source_type=source_type)


@router.get("/chunks", response_model=List[DocChunkItem])
async def list_knowledge_chunks(
    source_type: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Browse indexed documentation and academy chunks."""
    stmt = select(DocChunk).order_by(desc(DocChunk.created_at)).limit(limit).offset(offset)
    if source_type:
        stmt = stmt.where(DocChunk.source_type == source_type)

    res = await db.execute(stmt)
    chunks = res.scalars().all()

    return [
        DocChunkItem(
            id=c.id,
            source_type=c.source_type,
            title=c.title,
            source_url=c.source_url,
            section_header=c.section_header,
            content_preview=c.content[:300] + ("..." if len(c.content) > 300 else ""),
            created_at=c.created_at,
        )
        for c in chunks
    ]


@router.post("/crawl", response_model=CrawlTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_crawl(
    payload: CrawlRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger manual re-indexing of runbooks, documentation, or academy pages."""
    target_url = payload.url or (
        settings.DOCS_BASE_URL if payload.source_type == "documentation" else settings.ACADEMY_BASE_URL
    )
    background_tasks.add_task(run_background_crawler, payload.source_type, target_url)
    return CrawlTriggerResponse(
        status="accepted",
        message=f"Crawling job initiated for {payload.source_type}",
    )


@router.get("/crawl/status", response_model=List[CrawlerSyncRunSchema])
async def get_crawl_status(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return recent crawler sync run history."""
    stmt = select(CrawlerSyncRun).order_by(desc(CrawlerSyncRun.started_at)).limit(limit)
    res = await db.execute(stmt)
    return [CrawlerSyncRunSchema.model_validate(run) for run in res.scalars().all()]


@router.post("/playground", response_model=RAGPlaygroundResponse)
async def rag_playground_query(
    payload: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Live RAG Playground endpoint: tests hybrid vector + FTS retrieval with abstention threshold.
    """
    raw_results = await hybrid_retriever.retrieve(
        db=db,
        query=payload.query,
        top_k=payload.top_k,
        source_type=payload.source_type,
    )

    items = [
        RAGQueryResultItem(
            title=r["title"],
            source_url=r["source_url"],
            section_header=r.get("section_header"),
            content=r["content"],
            similarity_score=r["similarity_score"],
            source_type=r["source_type"],
        )
        for r in raw_results
    ]
    max_score = max((item.similarity_score for item in items), default=0.0)
    abstained = max_score < settings.RAG_MIN_CONFIDENCE

    return RAGPlaygroundResponse(
        results=items,
        max_score=max_score,
        abstained=abstained,
    )


@router.get("/drift", response_model=List[DocsDriftClusterSchema])
async def list_docs_drift_clusters(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """List low-confidence Docs Drift clusters detected from incoming issues."""
    stmt = select(DocsDriftCluster).order_by(desc(DocsDriftCluster.issue_count), desc(DocsDriftCluster.updated_at))
    if status_filter:
        stmt = stmt.where(DocsDriftCluster.status == status_filter)
    res = await db.execute(stmt)
    return [DocsDriftClusterSchema.model_validate(c) for c in res.scalars().all()]


@router.post("/drift/{cluster_id}/generate-draft", response_model=DocDraftResponse)
async def generate_drift_doc_draft(
    cluster_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new Academy guide / Docs PR draft for a Docs Drift cluster."""
    res = await db.execute(select(DocsDriftCluster).where(DocsDriftCluster.id == cluster_id))
    cluster = res.scalar_one_or_none()
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Docs drift cluster not found")

    title = cluster.generated_doc_title or f"Guide: {cluster.cluster_label}"
    draft = cluster.generated_doc_draft or (
        f"# {title}\n\n"
        f"## Problem Summary\n{cluster.topic_summary}\n\n"
        f"## Diagnostic & Resolution Checklist\n"
        f"*(Draft scaffolded from cluster {cluster.id}; full LLM synthesis implemented in M3.)*\n"
    )
    cluster.generated_doc_title = title
    cluster.generated_doc_draft = draft
    cluster.status = "draft_generated"
    await db.commit()

    return DocDraftResponse(
        cluster_id=cluster.id,
        title=title,
        markdown_draft=draft,
        status=cluster.status,
    )
