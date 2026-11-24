import os
import glob
from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.models.entities import DocChunk, CrawlerSyncRun
from app.rag.embeddings import embedding_service
from app.core.config import settings


class DocsCrawler:
    def __init__(self):
        self.chunk_size = 1000
        self.chunk_overlap = 150

    def chunk_text(self, text: str, header: Optional[str] = None) -> List[str]:
        """Split text into overlapping chunks, preserving sentence boundaries where possible."""
        lines = text.split("\n\n")
        chunks = []
        current = ""

        prefix = f"### {header}\n" if header else ""

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            if len(current) + len(line_str) < self.chunk_size:
                current += line_str + "\n\n"
            else:
                if current:
                    chunks.append((prefix + current).strip())
                current = line_str[-self.chunk_overlap:] if len(line_str) > self.chunk_overlap else line_str + "\n\n"

        if current.strip():
            chunks.append((prefix + current).strip())

        return chunks if chunks else [text[:self.chunk_size]]

    async def index_local_runbooks(self, db: AsyncSession, runbooks_dir: str = "../runbooks") -> int:
        """Scan local markdown runbooks and ingest into doc_chunks table."""
        resolved_dir = os.path.abspath(runbooks_dir)
        if not os.path.exists(resolved_dir):
            resolved_dir = os.path.abspath("./runbooks")
            if not os.path.exists(resolved_dir):
                return 0

        files = glob.glob(os.path.join(resolved_dir, "*.md"))
        indexed_count = 0

        for file_path in files:
            filename = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            title = filename.replace(".md", "").replace("-", " ").title()
            first_line = content.split("\n")[0] if content else ""
            if first_line.startswith("#"):
                title = first_line.lstrip("#").strip()

            chunks = self.chunk_text(content, header=title)
            embeddings = await embedding_service.get_embeddings_batch(chunks)

            # Delete old chunks for this file
            source_url = f"file://runbooks/{filename}"
            await db.execute(delete(DocChunk).where(DocChunk.source_url == source_url))

            for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                doc = DocChunk(
                    source_type="runbook",
                    title=title,
                    source_url=source_url,
                    section_header=f"Section {idx + 1}",
                    content=chunk,
                    metadata_json={"filename": filename, "chunk_index": idx},
                    embedding=emb
                )
                db.add(doc)
                indexed_count += 1

        await db.commit()
        return indexed_count

    async def crawl_web_page(self, db: AsyncSession, url: str, source_type: str = "documentation") -> int:
        """Crawl an individual web URL (e.g. from Documentation or Academy), parse semantic sections, and index."""
        indexed_count = 0
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                res = await client.get(url, headers={"User-Agent": "GitLabPlatformSupportCrawler/1.0"})
                if res.status_code != 200:
                    return 0
                html = res.text

            soup = BeautifulSoup(html, "html.parser")

            # Remove script, style, nav, footer
            for el in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                el.decompose()

            page_title = soup.title.string.strip() if soup.title and soup.title.string else url

            # Find main article or content body
            content_el = soup.find("article") or soup.find("main") or soup.body
            if not content_el:
                return 0

            # Extract sections based on H1/H2/H3
            sections = []
            current_header = page_title
            current_body = []

            for child in content_el.descendants:
                if child.name in ["h1", "h2", "h3"]:
                    if current_body:
                        sections.append((current_header, " ".join(current_body)))
                        current_body = []
                    current_header = child.get_text(strip=True)
                elif child.name in ["p", "li", "pre", "code"]:
                    t = child.get_text(strip=True)
                    if t and len(t) > 20:
                        current_body.append(t)

            if current_body:
                sections.append((current_header, " ".join(current_body)))

            if not sections:
                sections.append((page_title, content_el.get_text(separator=" ", strip=True)))

            # Delete existing chunks for this URL
            await db.execute(delete(DocChunk).where(DocChunk.source_url == url))

            # Chunk and embed
            all_chunks = []
            all_headers = []
            for header, text_content in sections:
                sub_chunks = self.chunk_text(text_content, header=header)
                for sc in sub_chunks:
                    all_chunks.append(sc)
                    all_headers.append(header)

            if all_chunks:
                embeddings = await embedding_service.get_embeddings_batch(all_chunks)
                for chunk, header, emb in zip(all_chunks, all_headers, embeddings):
                    doc = DocChunk(
                        source_type=source_type,
                        title=page_title,
                        source_url=url,
                        section_header=header,
                        content=chunk,
                        metadata_json={"url": url, "scraped_at": str(func.now())},
                        embedding=emb
                    )
                    db.add(doc)
                    indexed_count += 1

                await db.commit()

        except Exception as e:
            print(f"Error crawling {url}: {e}")

        return indexed_count


docs_crawler = DocsCrawler()
