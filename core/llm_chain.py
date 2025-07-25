import logging
import os
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
from langchain.schema import AIMessage, HumanMessage
from config import settings

logger = logging.getLogger(__name__)

class LLMChain:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.OPENAI_API_VERSION,
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            model_name="gpt-4",
            temperature=0.7,
        )
        self.retriever = self._load_vector_store().as_retriever()
        self.rag_chain = self._create_rag_chain()

    def _load_vector_store(self):
        if not os.path.exists(settings.FAISS_INDEX_PATH):
            raise FileNotFoundError(f"FAISS index not found at {settings.FAISS_INDEX_PATH}")
        logger.info(f"Loading FAISS index from {settings.FAISS_INDEX_PATH}")
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=settings.AZURE_EMBEDDINGS_DEPLOYMENT_NAME,
            openai_api_key=settings.AZURE_EMBEDDINGS_API_KEY,
            azure_endpoint=settings.AZURE_EMBEDDINGS_ENDPOINT,
        )
        return FAISS.load_local(
            settings.FAISS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )

    def _create_rag_chain(self):
        history_aware_retriever = create_history_aware_retriever(
            self.llm, self.retriever, self._get_history_aware_prompt()
        )
        question_answer_chain = create_stuff_documents_chain(
            self.llm, self._get_qa_prompt()
        )
        return create_retrieval_chain(history_aware_retriever, question_answer_chain)

    @staticmethod
    def _get_history_aware_prompt():
        return ChatPromptTemplate.from_messages([
            ("system", "Given a chat history and the latest user question "
                       "which might reference context in the chat history, "
                       "formulate a standalone question which can be understood "
                       "without the chat history. Do NOT answer the question, "
                       "just reformulate it if needed and otherwise return it as is."),
            ("placeholder", "{chat_history}"),
            ("user", "{input}"),
        ])

    @staticmethod
    def _get_qa_prompt():
        return ChatPromptTemplate.from_messages([
            ("system", "You are an expert real estate assistant for 'Apolo'. "
                       "Your goal is to help users find properties and organize visits. "
                       "Be friendly, professional, and concise. "
                       "Use the following context to answer the user's question. "
                       "If the information is not in the context, say you don't have that detail and offer to help in other ways. "
                       "Do not make up information.\n\n"
                       "Context:\n{context}"),
            ("user", "{input}"),
        ])

    def invoke_chain(self, question: str, chat_history: list) -> str:
        """
        Invokes the RAG chain to get an answer.
        """
        logger.info(f"Invoking RAG chain for question: '{question}'")
        history_messages = [AIMessage(content=msg['ai']) if 'ai' in msg else HumanMessage(content=msg['human']) for msg in chat_history]
        
        response = self.rag_chain.invoke({
            "input": question,
            "chat_history": history_messages
        })
        
        logger.info(f"RAG chain response: {response['answer']}")
        return response.get("answer", "I'm sorry, I encountered an issue and can't respond right now.")

# Singleton instance
llm_chain = LLMChain() 