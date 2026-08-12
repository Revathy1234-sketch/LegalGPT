import logging
from typing import Any, Dict, List
from langchain.prompts import PromptTemplate
from app.core.config import settings
from app.services.vector_service import vector_service
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class LangChainRAGService:

    def __init__(self):
        self.prompt = PromptTemplate(
            template="""You are a legal contract assistant.

Answer ONLY from the provided context.

If answer not found say:

Information not found in contract.

Context:
{context}

Question:
{question}""",
            input_variables=["context", "question"]
        )

    def ask(
        self,
        contract_id: str,
        question: str
    ) -> Dict[str, Any]:
        results = vector_service.search_contract(
            contract_id,
            question,
            top_k=5
        )
        if not results:
            return {
                "answer": "Information not found in contract.",
                "sources": []
            }

        context = "\n\n".join(
            item["parent_text"]
            for item in results
        )

        try:
            answer, _ = LLMService.invoke(
                self.prompt,
                {
                    "context": context,
                    "question": question
                }
            )
        except Exception as exc:
            logger.error("LangChainRAGService LLM invocation failed: %s", exc)
            return {
                "answer": f"Information not found in contract. (Error: {exc})",
                "sources": results
            }

        return {
            "answer": answer,
            "sources": results
        }


langchain_rag_service = LangChainRAGService()