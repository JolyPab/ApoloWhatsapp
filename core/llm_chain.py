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
        # Процессная in-memory память по сессиям, если Redis недоступен
        self._memory_store: dict[str, ConversationBufferMemory] = {}

    def get_conversation_memory(self, session_id: str) -> ConversationBufferMemory:
        """Возвращает процессную in-memory память для сессии.
        Пока Redis отключён, храним состояние диалога в self._memory_store.
        """
        if session_id not in self._memory_store:
            logger.info(f"Creating in-process memory for session {session_id}")
            self._memory_store[session_id] = ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_history"
            )
        return self._memory_store[session_id]

    def add_message_to_memory(self, session_id: str, human_message: str, ai_message: str):
        """Добавляет сообщения в память чата."""
        memory = self.get_conversation_memory(session_id)
        memory.chat_memory.add_user_message(human_message)
        memory.chat_memory.add_ai_message(ai_message)
        logger.info(f"Added messages to persistent memory for session {session_id}")

    def get_chat_history_from_memory(self, session_id: str) -> list:
        """Получает историю чата из процессной памяти."""
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
            ("system", "Dado un historial de chat y la última pregunta del usuario "
                       "que podría referenciar contexto del historial, "
                       "formula una pregunta independiente que pueda entenderse "
                       "sin el historial del chat. NO respondas la pregunta, "
                       "solo reformúlala si es necesario, de lo contrario devuélvela tal como está."),
            ("placeholder", "{chat_history}"),
            ("user", "{input}"),
        ])

    @staticmethod
    def _get_qa_prompt():
        return ChatPromptTemplate.from_messages([
            ("system", "Eres un asistente experto en bienes raíces para 'Century21 Apolo' en Cancún. "
                       "Tu objetivo principal es ayudar a los clientes a encontrar propiedades y organizar visitas. "
                       "Siempre mantén un tono amigable, profesional y entusiasta. "
                       "\n\nINSTRUCCIONES IMPORTANTES:"
                       "\n- Usa SIEMPRE la información del contexto proporcionado para responder"
                       "\n- Si no tienes la información específica, ofrece ayudar de otras maneras"
                       "\n- NUNCA inventes información que no esté en el contexto"
                       "\n- Cuando menciones propiedades, incluye detalles como precio, ubicación y características"
                       "\n- Siempre intenta guiar hacia agendar una visita o contactar con un asesor"
                       "\n- Sé específico con precios, ubicaciones y características cuando estén disponibles"
                       "\n- Si el cliente muestra interés serio, sugiere contactar directamente con el asesor"
                       "\n- Cuando presentes múltiples opciones, enuméralas como 1., 2., 3. y mantén consistencia en los números entre mensajes"
                       "\n- Si el usuario se refiere a 'opción 2', 'la 2', 'la segunda', etc., entiende que habla de la opción #2 listada previamente y entrega más detalles de esa opción"
                       "\n- Mantén las respuestas concisas (máx. 6-8 líneas) y ofrece continuar con más detalles si el cliente lo pide"
                       "\n\nContexto de propiedades disponibles:\n{context}"),
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