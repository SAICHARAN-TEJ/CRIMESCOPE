"""Chat router — post-simulation Q&A with the swarm."""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.demo.harlow_case import HARLOW_SEED
from backend.utils.openrouter import openrouter
from backend.config import settings

router = APIRouter()


class ChatRequest(BaseModel):
    question: str


@router.post("/chat/{case_id}")
async def chat(case_id: str, body: ChatRequest):
    """
    Simple RAG-lite chat — feeds the question + case context
    through the reasoning model for a grounded answer.
    """
    # For the demo, always use Harlow context
    context = str(HARLOW_SEED)

    answer = await openrouter.chat(
        settings.reasoning_model_name,
        f"CASE CONTEXT:\n{context[:3000]}\n\nQUESTION: {body.question}",
        system=(
            "You are the CrimeScope swarm intelligence analyst. "
            "Answer based strictly on the case evidence provided."
        ),
    )
    return {"case_id": case_id, "question": body.question, "answer": answer}
