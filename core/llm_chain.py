import logging
import os
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
from langchain.schema import AIMessage, HumanMessage
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
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

    def get_conversation_memory(self, session_id: str) -> ConversationBufferMemory:
        """Получает Redis-backed память для конкретной сессии."""
        try:
            # Создаем Redis-backed историю чата с SSL для Azure Redis Cache
            redis_url = f"rediss://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}"
            
            message_history = RedisChatMessageHistory(
                session_id=f"chat:{session_id}",
                url=redis_url
            )
            
            # Создаем память с Redis backend
            memory = ConversationBufferMemory(
                chat_memory=message_history,
                return_messages=True,
                memory_key="chat_history"
            )
            
            return memory
            
        except Exception as e:
            logger.warning(f"Redis недоступен для памяти {session_id}: {e}. Использую временную память.")
            # Fallback к временной памяти если Redis недоступен
            return ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history"
            )

    def add_message_to_memory(self, session_id: str, human_message: str, ai_message: str):
        """Добавляет сообщения в память чата."""
        memory = self.get_conversation_memory(session_id)
        memory.chat_memory.add_user_message(human_message)
        memory.chat_memory.add_ai_message(ai_message)
        logger.info(f"Added messages to persistent memory for session {session_id}")

    def get_chat_history_from_memory(self, session_id: str) -> list:
        """Получает историю чата из Redis-backed памяти."""
        memory = self.get_conversation_memory(session_id)
        messages = memory.chat_memory.messages
        logger.info(f"Retrieved {len(messages)} messages from persistent memory for session {session_id}")
        return messages

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

    def invoke_chain(self, question: str, session_id: str) -> str:
        """
        Invokes the RAG chain to get an answer using persistent conversation memory.
        """
        logger.info(f"Invoking RAG chain for question: '{question}' with session: {session_id}")
        
        # Получаем историю из Redis-backed памяти
        chat_history = self.get_chat_history_from_memory(session_id)
        
        response = self.rag_chain.invoke({
            "input": question,
            "chat_history": chat_history
        })
        
        answer = response.get("answer", "I'm sorry, I encountered an issue and can't respond right now.")
        
        # Добавляем текущий диалог в Redis-backed память
        self.add_message_to_memory(session_id, question, answer)
        
        logger.info(f"RAG chain response: {answer}")
        return answer

# Singleton instance
llm_chain = LLMChain() 