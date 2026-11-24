from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.entities import Issue, DuplicateCandidate
from app.core.config import settings


class DuplicateDetector:
    async def find_duplicates(
        self,
        db: AsyncSession,
        current_issue: Issue,
        threshold: float = settings.DUPLICATE_SIMILARITY_THRESHOLD,
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Calculates cosine distance against existing issues to detect duplicate or related tickets.
        """
        if current_issue.embedding is None:
            return []

        # Vector distance expression
        distance_expr = Issue.embedding.cosine_distance(current_issue.embedding)

        stmt = (
            select(
                Issue.id,
                Issue.project_id,
                Issue.iid,
                Issue.title,
                Issue.state,
                Issue.web_url,
                distance_expr.label("distance")
            )
            .where(
                and_(
                    Issue.id != current_issue.id,
                    Issue.embedding.isnot(None)
                )
            )
            .order_by(distance_expr)
            .limit(top_k)
        )

        res = await db.execute(stmt)
        rows = res.all()

        duplicates = []
        for r in rows:
            dist = float(r.distance) if r.distance is not None else 1.0
            similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))

            if similarity >= threshold:
                dup_record = DuplicateCandidate(
                    issue_id=current_issue.id,
                    candidate_issue_id=r.id,
                    similarity_score=round(similarity, 3),
                    comparison_notes=f"Detected {round(similarity * 100, 1)}% semantic similarity with #{r.iid} ({r.title})"
                )
                db.add(dup_record)
                duplicates.append({
                    "candidate_issue_id": r.id,
                    "candidate_iid": r.iid,
                    "candidate_title": r.title,
                    "candidate_web_url": r.web_url,
                    "similarity_score": round(similarity, 3),
                    "comparison_notes": f"High semantic overlap ({round(similarity * 100, 1)}%)"
                })

        if duplicates:
            await db.commit()

        return duplicates


duplicate_detector = DuplicateDetector()
