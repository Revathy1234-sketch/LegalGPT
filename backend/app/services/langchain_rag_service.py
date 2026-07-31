ChatGoogleGenerativeAI = None
LANGCHAIN_GEMINI_IMPORT_ERROR = "langchain-google-genai import skipped for startup safety"

PromptTemplate = None
StrOutputParser = None
LANGCHAIN_PROMPT_IMPORT_ERROR = "langchain prompt modules import skipped for startup safety"

from app.core.config import settings
from app.services.vector_service import vector_service


class LangChainRAGService:

    def __init__(self):
        self.initialization_error = None

        if (
            ChatGoogleGenerativeAI is None
            or PromptTemplate is None
            or StrOutputParser is None
        ):
            self.initialization_error = (
                "LangChain Gemini dependencies are unavailable. "
                f"Original error: {LANGCHAIN_GEMINI_IMPORT_ERROR or LANGCHAIN_PROMPT_IMPORT_ERROR}"
            )
            self.llm = None
            self.prompt = None
            self.chain = None
            return

        if not settings.GEMINI_API_KEY or not settings.GEMINI_MODEL:
            self.initialization_error = "GEMINI_API_KEY or GEMINI_MODEL is not configured."
            self.llm = None
            self.prompt = None
            self.chain = None
            return

        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0,
            max_output_tokens=1500,
            timeout=60,
            max_retries=0,
        )

        self.prompt = PromptTemplate(
            template="""
You are a legal contract assistant.

Answer ONLY from the provided context.

If answer not found say:

Information not found in contract.

Context:
{context}

Question:
{question}
""",
            input_variables=[
                "context",
                "question"
            ]
        )

        self.chain = (
            self.prompt
            | self.llm
            | StrOutputParser()
        )

    def ask(
        self,
        contract_id: str,
        question: str
    ):
        if self.chain is None:
            return {
                "answer": "AI services are not configured yet. Please add a valid Gemini API key in backend/.env to enable RAG responses.",
                "sources": []
            }

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

        answer = self.chain.invoke(
            {
                "context": context,
                "question": question
            }
        )

        return {
            "answer": answer,
            "sources": results
        }


langchain_rag_service = LangChainRAGService()