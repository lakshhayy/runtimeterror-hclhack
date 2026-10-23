"""Grounded policy answers: retrieve the latest effective chunks for the user's audience, then answer only from them.

Run: python -m app.services.rag "question"   (prints the top 4 scores, to tune RAG_MIN_SCORE)
"""
import sys

from sqlalchemy import text

from app.config import settings
from app.core.audit import log_audit
from app.core.errors import AppError
from app.core.guardrails import guard_user_text
from app.core.llm import LLMUnavailable, chat_json, embed
from app.schemas.rag import LlmRagReply, RagAnswer, RagSource

SAFE_REPLY = ("I couldn't find this in Kestrel Bank's approved policy documents. "
              "Please contact a loan officer for help.")

SYSTEM_PROMPT = """You are Kestrel Bank's policy assistant.
Answer ONLY from the numbered context sections below. Do not use outside knowledge.
Be concise (1-3 sentences) and use plain language a customer understands.
If the context does not contain the answer, set found=false and leave answer empty.
List the numbers of the context sections you used in usedSources."""

# Latest effective version per document, filtered by audience and loan type, ranked by cosine distance.
RETRIEVE_SQL = text("""
WITH latest AS (
    SELECT DISTINCT ON (doc_key) doc_key, version
    FROM policy_chunks
    WHERE effective_date <= CURRENT_DATE
    ORDER BY doc_key, effective_date DESC
)
SELECT c.id, c.doc_key, c.doc_title, c.section, c.content, c.version, c.effective_date, c.loan_type, c.audience,
       1 - (c.embedding <=> CAST(:q AS vector)) AS score
FROM policy_chunks c
JOIN latest l ON l.doc_key = c.doc_key AND l.version = c.version
WHERE c.audience = ANY(:aud)
  AND (CAST(:lt AS text) IS NULL OR c.loan_type IN (CAST(:lt AS text), 'ALL'))
ORDER BY c.embedding <=> CAST(:q AS vector)
LIMIT :k
""")


def allowed_audiences(role: str) -> list[str]:
    """Customers only see customer documents; staff also see internal ones."""
    return ["CUSTOMER"] if role == "CUSTOMER" else ["CUSTOMER", "INTERNAL"]


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vector) + "]"


def retrieve(db, question: str, role: str, loan_type: str | None = None, k: int = 4) -> list[dict]:
    """Top-k chunks with a similarity score (1 = identical). Raises LLMUnavailable if embedding fails."""
    params = {"q": _vector_literal(embed(question)), "aud": allowed_audiences(role), "lt": loan_type, "k": k}
    return [dict(row._mapping) for row in db.execute(RETRIEVE_SQL, params)]


def _source(chunk: dict) -> RagSource:
    return RagSource(document=chunk["doc_title"], section=chunk["section"], version=chunk["version"],
                     effective_date=chunk["effective_date"].isoformat())


def _context(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[{i}] {c['doc_title']} — {c['section']} (v{c['version']}, effective {c['effective_date']})\n{c['content']}"
        for i, c in enumerate(chunks, start=1)
    )


def _safe_reply() -> RagAnswer:
    return RagAnswer(answer=SAFE_REPLY, confidence="LOW", sources=[], follow_up_required=True)


def _build_answer(question: str, chunks: list[dict]) -> RagAnswer:
    """Ask the LLM to answer from the chunks; fall back to the top chunk if the LLM is down."""
    if not chunks or chunks[0]["score"] < settings.RAG_MIN_SCORE:
        return _safe_reply()

    top = chunks[0]
    reply = chat_json(SYSTEM_PROMPT, f"Context:\n{_context(chunks)}\n\nQuestion: {question}", LlmRagReply)
    if reply is None:
        excerpt = top["content"][:400].rstrip()
        return RagAnswer(answer=f"Here is the most relevant policy section: {excerpt}", confidence="MEDIUM",
                         sources=[_source(top)], follow_up_required=True)
    if not reply.found or not reply.answer.strip():
        return _safe_reply()

    used = [chunks[i - 1] for i in dict.fromkeys(reply.used_sources) if 1 <= i <= len(chunks)] or [top]
    confidence = "HIGH" if top["score"] >= settings.RAG_HIGH_SCORE else "MEDIUM"
    return RagAnswer(answer=reply.answer.strip(), confidence=confidence,
                     sources=[_source(c) for c in used], follow_up_required=False)


def answer_question(db, user, question: str, loan_type: str | None = None) -> RagAnswer:
    """Guard -> retrieve -> grounded answer -> audit."""
    masked = guard_user_text(db, user, question, where="rag")
    try:
        chunks = retrieve(db, masked, user.role, loan_type)
    except LLMUnavailable:
        raise AppError(503, "AI_UNAVAILABLE", "The policy assistant is unavailable right now. Please try again shortly.")

    answer = _build_answer(masked, chunks)
    log_audit(db, action="RAG_ASK", user_id=user.id, input={"question": masked, "loanType": loan_type},
              output={"confidence": answer.confidence, "sources": [s.model_dump(by_alias=True) for s in answer.sources],
                      "topScore": round(chunks[0]["score"], 3) if chunks else None},
              commit=True)
    return answer


if __name__ == "__main__":
    from app.database import SessionLocal

    q = " ".join(sys.argv[1:]) or "Can I foreclose my vehicle loan after six months?"
    with SessionLocal() as session:
        for row in retrieve(session, q, "OFFICER"):
            print(f"{row['score']:.3f}  {row['doc_title']} v{row['version']} — {row['section']} [{row['audience']}]")
