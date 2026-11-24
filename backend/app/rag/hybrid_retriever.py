from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, text
from app.models.entities import DocChunk
from app.rag.embeddings import embedding_service


class HybridRetriever:
    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 5,
        source_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval combining pgvector cosine distance and keyword matching.
        Returns ranked chunks with citation URLs, section headers, and scores.
        """
        query_vector = await embedding_service.get_embedding(query)

        # 1. Semantic Vector Search Query using pgvector cosine distance (<=>)
        # Cosine distance: 0 is identical, 2 is opposite. Score = 1 - (distance / 2)
        distance_expr = DocChunk.embedding.cosine_distance(query_vector)

        stmt = select(
            DocChunk.id,
            DocChunk.title,
            DocChunk.source_url,
            DocChunk.section_header,
            DocChunk.content,
            DocChunk.source_type,
            distance_expr.label("distance")
        )

        if source_type:
            stmt = stmt.where(DocChunk.source_type == source_type)

        # Extract tokens for keyword boosting
        tokens = [t.lower() for t in query.split() if len(t) > 3][:6]
        if tokens:
            keyword_conditions = [DocChunk.content.ilike(f"%{tok}%") for tok in tokens]
            stmt = stmt.order_by(distance_expr).limit(top_k * 2)
        else:
            stmt = stmt.order_by(distance_expr).limit(top_k)

        result = await db.execute(stmt)
        rows = result.all()

        formatted_results = []
        for row in rows:
            dist = float(row.distance) if row.distance is not None else 1.0
            semantic_score = max(0.0, min(1.0, 1.0 - (dist / 2.0)))

            # Calculate keyword match bonus
            content_lower = row.content.lower()
            keyword_hits = sum(1 for tok in tokens if tok in content_lower)
            keyword_boost = min(0.2, keyword_hits * 0.04)

            final_score = min(1.0, round(semantic_score + keyword_boost, 3))

            formatted_results.append({
                "id": str(row.id),
                "title": row.title,
                "source_url": row.source_url,
                "section_header": row.section_header,
                "content": row.content,
                "source_type": row.source_type,
                "similarity_score": final_score
            })

        # Sort by final hybrid score
        formatted_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return formatted_results[:top_k]


hybrid_retriever = HybridRetriever()
