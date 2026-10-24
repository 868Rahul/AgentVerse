"""
Employee handbook retrieval (RAG).

Pipeline
1. Load resource/EmployeeHandbook.pdf page by page
2. Clean the text (non-breaking spaces, odd hyphens, repeated page headers, table of contents)
3. Split it by handbook section ("VII. HOURS OF WORK ..." / "A. Hours of Work") and then into
   ~1000 character chunks; every chunk starts with its section title and keeps its page number
4. Hybrid search: vector similarity (ChromaDB) + keyword BM25, merged with reciprocal rank fusion.
   If embeddings are unavailable (quota, Ollama down) keyword search still answers.

The vector index is built automatically the first time it is needed (or with tests/rag/importRag.py).
"""

import asyncio
import logging
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from ai.rag.chromaClient import get_vector_store
from core.config import settings

logger = logging.getLogger(__name__)

# Logged by pypdf for every page of this PDF, harmless
logging.getLogger("pypdf").setLevel(logging.ERROR)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
# Seconds before retrying the vector index after embeddings failed
VECTOR_RETRY_SECONDS = 300

_CHAR_FIXES = {
    "\xa0": " ",
    "‐": "-",
    "‑": "-",
    "–": "-",
    "—": "-",
    "ʹ": "'",
    "ʺ": '"',
    "’": "'",
    "‘": "'",
    "“": '"',
    "”": '"',
}
# Lines printed on top of every page
_PAGE_HEADER_LINES = (
    "{ORGANIZATION NAME} Employee Handbook",
    "©2004 National Council of Nonprofit Associations",
    "May be duplicated, with attribution, by charitable organizations.",
)
_SECTION_RE = re.compile(r"^([IVXLC]+)\.\s+([A-Z][A-Z0-9 ,'&/()\-]+)$")
_SUBSECTION_RE = re.compile(r"^([A-Z])\.\s+(\S.{1,70})$")
_TOC_LINE_RE = re.compile(r"\.{5,}")
_PAGE_NUMBER_RE = re.compile(r"^([ivxlc]+|\d+)$", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = set(
    "a an and are as at be by can do does for from has have how i if in is it its me my of on or our "
    "shall should that the their there this to was what when where which who will with you your".split()
)


def _clean_line(line: str) -> str:
    for bad, good in _CHAR_FIXES.items():
        line = line.replace(bad, good)
    return re.sub(r"\s+", " ", line).strip()


@dataclass
class _Section:
    title: str
    page: int
    lines: list[tuple[int, str]] = field(default_factory=list)


def load_handbook_chunks(pdf_path: str | Path | None = None) -> list[Document]:
    """Read the handbook PDF and return section aware chunks with page metadata."""
    reader = PdfReader(str(pdf_path or settings.HANDBOOK_PDF_PATH))
    sections: list[_Section] = []
    main_title = "Introduction"
    current = _Section(title=main_title, page=1)

    for page_index, page in enumerate(reader.pages, start=1):
        for raw in (page.extract_text() or "").splitlines():
            line = _clean_line(raw)
            if not line or line in _PAGE_HEADER_LINES or _PAGE_NUMBER_RE.match(line) or _TOC_LINE_RE.search(line):
                continue
            if match := _SECTION_RE.match(line):
                main_title = f"{match.group(1)}. {match.group(2).title()}"
                sections.append(current)
                current = _Section(title=main_title, page=page_index)
                continue
            if (match := _SUBSECTION_RE.match(line)) and not line.endswith("."):
                sections.append(current)
                current = _Section(title=f"{main_title} > {match.group(1)}. {match.group(2)}", page=page_index)
                continue
            current.lines.append((page_index, line))
    sections.append(current)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n", ". ", " ", ""],
    )
    chunks: list[Document] = []
    for section in sections:
        if not section.lines:
            continue
        # Remember on which page every character offset starts, to give each chunk a page number
        text, offsets = "", []
        for page_index, line in section.lines:
            offsets.append((len(text), page_index))
            text += line + "\n"
        for piece in splitter.split_text(text):
            start = text.find(piece[:50])
            page_index = next((p for off, p in reversed(offsets) if off <= max(start, 0)), section.page)
            chunks.append(
                Document(
                    page_content=f"[{section.title}]\n{piece.strip()}",
                    metadata={"section": section.title, "page": page_index, "chunk": len(chunks)},
                )
            )
    return chunks


def _tokenize(text: str) -> list[str]:
    # crude plural stemming so "hours" matches "hour" and "days" matches "day"
    return [
        w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
        for w in _WORD_RE.findall(text.lower())
        if w not in _STOPWORDS
    ]


class KeywordIndex:
    """Small BM25 index, enough for a few hundred chunks without extra dependencies."""

    def __init__(self, docs: list[Document], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.tfs = [Counter(_tokenize(d.page_content)) for d in docs]
        self.lengths = [sum(tf.values()) for tf in self.tfs]
        self.avg_length = sum(self.lengths) / max(len(self.lengths), 1)
        df = Counter(term for tf in self.tfs for term in tf)
        n = len(docs)
        self.idf = {term: math.log(1 + (n - f + 0.5) / (f + 0.5)) for term, f in df.items()}

    def search(self, query: str, k: int) -> list[Document]:
        terms = _tokenize(query)
        scores = []
        for i, tf in enumerate(self.tfs):
            score = 0.0
            for term in terms:
                if term in tf:
                    freq = tf[term]
                    norm = freq + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg_length)
                    score += self.idf[term] * freq * (self.k1 + 1) / norm
            if score > 0:
                scores.append((score, i))
        scores.sort(reverse=True)
        return [self.docs[i] for _, i in scores[:k]]


def _reciprocal_rank_fusion(result_lists: list[list[Document]], k: int, c: int = 60) -> list[Document]:
    scores: dict[int, float] = {}
    by_id: dict[int, Document] = {}
    for results in result_lists:
        for rank, doc in enumerate(results):
            chunk_id = doc.metadata["chunk"]
            by_id[chunk_id] = doc
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (c + rank + 1)
    ranked = sorted(scores, key=scores.get, reverse=True)
    return [by_id[i] for i in ranked[:k]]


class HandbookRetriever:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._chunks: list[Document] | None = None
        self._keyword: KeywordIndex | None = None
        self._vector_ready = False
        self._vector_failed_at = 0.0

    async def _ensure_chunks(self) -> None:
        if self._chunks is None:
            self._chunks = await asyncio.to_thread(load_handbook_chunks)
            self._keyword = KeywordIndex(self._chunks)
            logger.info(f"Handbook loaded: {len(self._chunks)} chunks")

    async def _ensure_vector_index(self) -> bool:
        """Embed the chunks once. Returns False when embeddings are unavailable."""
        if self._vector_ready:
            return True
        if time.monotonic() - self._vector_failed_at < VECTOR_RETRY_SECONDS:
            return False
        try:
            store = get_vector_store()
            existing = await asyncio.to_thread(lambda: store._collection.count())
            if existing != len(self._chunks):
                logger.info(f"Building handbook vector index ({len(self._chunks)} chunks)")
                await asyncio.to_thread(store.reset_collection)
                await store.aadd_documents(self._chunks, ids=[f"chunk-{d.metadata['chunk']}" for d in self._chunks])
            self._vector_ready = True
        except Exception as e:
            self._vector_failed_at = time.monotonic()
            logger.warning(f"Handbook vector index unavailable, using keyword search only: {e}")
        return self._vector_ready

    async def rebuild(self) -> int:
        """Re-read the PDF and re-embed everything (used after replacing the PDF)."""
        async with self._lock:
            self._chunks, self._vector_ready, self._vector_failed_at = None, False, 0.0
            await self._ensure_chunks()
            await asyncio.to_thread(get_vector_store().reset_collection)
            await self._ensure_vector_index()
            return len(self._chunks)

    async def warm_up(self) -> None:
        try:
            async with self._lock:
                await self._ensure_chunks()
                await self._ensure_vector_index()
        except Exception as e:
            logger.warning(f"Handbook warm up failed: {e}")

    async def sections(self) -> list[str]:
        async with self._lock:
            await self._ensure_chunks()
        return list(dict.fromkeys(d.metadata["section"] for d in self._chunks))

    async def search(self, query: str, k: int = 5) -> list[Document]:
        async with self._lock:
            await self._ensure_chunks()
            vector_ok = await self._ensure_vector_index()

        result_lists = [self._keyword.search(query, k * 2)]
        if vector_ok:
            try:
                result_lists.insert(0, await get_vector_store().asimilarity_search(query, k=k * 2))
            except Exception as e:
                self._vector_ready = False
                self._vector_failed_at = time.monotonic()
                logger.warning(f"Handbook vector search failed, using keyword search only: {e}")
        return _reciprocal_rank_fusion(result_lists, k)


handbook_retriever = HandbookRetriever()
