"""RAG (policy assistant) routes."""
from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.database import get_db
from app.schemas.rag import RagAnswer, RagAskIn
from app.services.rag import answer_question

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/ask", response_model=RagAnswer)
def ask(body: RagAskIn, db=Depends(get_db), user=Depends(get_current_user)):
    """Answer a policy question from approved documents only, with sources."""
    return answer_question(db, user, body.question, body.loan_type)
