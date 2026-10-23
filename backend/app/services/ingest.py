"""Policy ingestion: Markdown with YAML front matter -> section chunks -> embeddings -> policy_chunks.

Run: python -m app.services.ingest
"""
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy import delete

from app.config import settings
from app.core.llm import embed_many
from app.models import PolicyChunk

BACKEND_DIR = Path(__file__).resolve().parents[2]
REQUIRED_META = ("doc_key", "title", "version", "effective_date", "loan_type", "doc_type", "customer_segment", "audience")


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Split '---\\nyaml\\n---\\nbody' into (meta, body)."""
    text = text.lstrip("﻿")
    if not text.startswith("---"):
        raise ValueError("Missing YAML front matter")
    _, meta_text, body = text.split("---", 2)
    meta = yaml.safe_load(meta_text) or {}
    missing = [k for k in REQUIRED_META if k not in meta]
    if missing:
        raise ValueError(f"Front matter is missing: {', '.join(missing)}")
    meta["version"] = str(meta["version"])
    if not isinstance(meta["effective_date"], date):
        meta["effective_date"] = date.fromisoformat(str(meta["effective_date"]))
    return meta, body


def chunk_by_section(body: str) -> list[tuple[str, str]]:
    """One chunk per '## ' section. Text before the first section becomes 'Overview'. Empty sections are skipped."""
    sections: list[tuple[str, list[str]]] = [("Overview", [])]
    for line in body.splitlines():
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif line.startswith("# "):
            continue  # document title, already in front matter
        else:
            sections[-1][1].append(line)
    chunks = []
    for title, lines in sections:
        content = "\n".join(lines).strip()
        if content:
            chunks.append((title, content))
    return chunks


def policy_folder(folder: str | None = None) -> Path:
    """POLICY_DIR is relative to the backend folder."""
    path = Path(folder or settings.POLICY_DIR)
    return path if path.is_absolute() else BACKEND_DIR / path


def ingest_file(db, path: Path) -> int:
    """Replace this doc_key + version's chunks with freshly embedded ones. Returns the chunk count."""
    meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
    chunks = chunk_by_section(body)
    db.execute(delete(PolicyChunk).where(PolicyChunk.doc_key == meta["doc_key"],
                                         PolicyChunk.version == meta["version"]))
    texts = [f"{meta['title']} — {section}\n{content}" for section, content in chunks]
    vectors = embed_many(texts)
    for (section, content), vector in zip(chunks, vectors):
        db.add(PolicyChunk(
            doc_key=meta["doc_key"], doc_title=meta["title"], section=section, content=content,
            version=meta["version"], effective_date=meta["effective_date"], loan_type=meta["loan_type"],
            doc_type=meta["doc_type"], customer_segment=meta["customer_segment"], audience=meta["audience"],
            embedding=vector,
        ))
    return len(chunks)


def ingest_policies(db, folder: str | None = None) -> int:
    """Ingest every .md file in the policy folder; one commit at the end. Returns the total chunk count."""
    total = 0
    for path in sorted(policy_folder(folder).glob("*.md")):
        count = ingest_file(db, path)
        print(f"  {path.name}: {count} chunks")
        total += count
    db.commit()
    return total


if __name__ == "__main__":
    from app.database import SessionLocal, init_db

    init_db()
    with SessionLocal() as session:
        print(f"Ingested {ingest_policies(session)} chunks")
