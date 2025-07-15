import os
import json
import re
import requests
import redis
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate

# --- Load env ---
load_dotenv()
MY_NUMBER  = os.getenv("MY_WHATSAPP_NUMBER")
BOT_NUMBER = os.getenv("BOT_NUMBER")
DIALOG_BASE_URL      = os.getenv("DIALOG_BASE_URL")
DIALOG_API_KEY       = os.getenv("DIALOG_API_KEY")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")
# AGENT_NUMBERS        = json.loads(os.getenv("AGENT_NUMBERS", "[]"))

# Более надежная загрузка AGENT_NUMBERS, чтобы избежать падения из-за некорректного JSON в env
agent_numbers_raw = os.getenv("AGENT_NUMBERS")
try:
    AGENT_NUMBERS = json.loads(agent_numbers_raw) if agent_numbers_raw else []
except json.JSONDecodeError:
    AGENT_NUMBERS = [] # По умолчанию пустой список в случае ошибки

# --- Flask app ---
app = Flask(__name__)

# Настройка логирования для Flask в окружении Gunicorn
if 'gunicorn' in os.environ.get('SERVER_SOFTWARE', ''):
    import logging
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.logger.info('Flask logger configured to use Gunicorn logger settings.')
else:
    # Для локального запуска (не через Gunicorn) или если gunicorn_logger не найден
    import logging
    if not app.debug: # Не устанавливаем INFO для debug режима, чтобы не дублировать
        app.logger.setLevel(logging.INFO)
    app.logger.info('Flask logger configured for standalone/debug mode.')

# Множество для хранения id уже обработанных сообщений - ТЕПЕРЬ НЕ ИСПОЛЬЗУЕТСЯ НАПРЯМУЮ, ЕСЛИ REDIS ДОСТУПЕН
# processed_messages = set() 

# --- Redis Client Initialization ---
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6380))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
# Azure Cache for Redis может требовать имя пользователя (часто 'default')
REDIS_USERNAME = os.getenv("REDIS_USERNAME") 

REDIS_PROCESSED_MESSAGES_KEY_PREFIX = "whatsapp_processed_msg:"
REDIS_MESSAGE_ID_TTL_SECONDS = 24 * 60 * 60 # 24 часа

redis_client = None
USE_REDIS_FOR_PROCESSED_MESSAGES = False

if REDIS_HOST and REDIS_PASSWORD:
    try:
        app.logger.info(f"Attempting to connect to Redis at {REDIS_HOST}:{REDIS_PORT}")
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME, # Добавлено имя пользователя
            password=REDIS_PASSWORD,
            ssl=True, # Azure Cache for Redis требует SSL
            ssl_cert_reqs='none', # ИСПРАВЛЕНО: Для Azure используется 'none', а не 'CERT_NONE'
            socket_connect_timeout=10, # Таймаут подключения в секундах
            socket_timeout=10 # Таймаут операций в секундах
        )
        redis_client.ping() # Проверка соединения
        app.logger.info(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        USE_REDIS_FOR_PROCESSED_MESSAGES = True
    except redis.exceptions.AuthenticationError as e_auth:
        app.logger.error(f"Redis authentication failed (invalid password?): {e_auth}. Falling back to in-memory set.")
        processed_messages_memory = set()
    except redis.exceptions.TimeoutError as e_timeout:
        app.logger.error(f"Redis connection timed out: {e_timeout}. Falling back to in-memory set for processed messages (NOT SUITABLE FOR PRODUCTION WITH MULTIPLE WORKERS).")
        processed_messages_memory = set()
    except redis.exceptions.ConnectionError as e_conn:
        app.logger.error(f"Could not connect to Redis: {e_conn}. Falling back to in-memory set for processed messages (NOT SUITABLE FOR PRODUCTION WITH MULTIPLE WORKERS).")
        processed_messages_memory = set()
    except Exception as e_redis_init:
        app.logger.error(f"An unexpected error occurred during Redis initialization: {e_redis_init}. Falling back to in-memory set.")
        processed_messages_memory = set()
else:
    app.logger.warning("Redis environment variables (REDIS_HOST, REDIS_PASSWORD) not fully set. Falling back to in-memory set for processed messages (NOT SUITABLE FOR PRODUCTION WITH MULTIPLE WORKERS).")
    processed_messages_memory = set()

# --- Embeddings & FAISS index ---
embeddings = AzureOpenAIEmbeddings(
    api_key=os.getenv("AZURE_EMBEDDINGS_API_KEY"),
    azure_endpoint=os.getenv("AZURE_EMBEDDINGS_ENDPOINT"),
    deployment="text-embedding-ada-002",
    api_version="2023-05-15",
    retry_max_session_seconds=120 # Добавим таймаут для стабильности
)
index = FAISS.load_local("apolo_faiss", embeddings, allow_dangerous_deserialization=True)

# --- LLM & Prompt ---
current_date = datetime.now().strftime("%Y-%m-%d")
SYSTEM_PROMPT = '''
Eres un asistente virtual para la selección de bienes raíces. Tu tarea es ayudar al cliente a elegir una propiedad que se ajuste lo máximo posible a sus deseos y necesidades.

Fecha actual: {current_date}

**CASO ESPECIAL: Referencia a Inmuebles24**
- Si el mensaje del CLIENTE menciona "Inmuebles24" o un portal similar, o incluye un enlace a una propiedad de un portal:
    - Tu PRIMERA RESPUESTA DEBE SER: "Claro, con gusto te ayudaré con la propiedad que viste en Inmuebles24. Para buscar la propiedad en nuestro sistema de Century21 Apolo, ¿podrías indicarme el título o nombre del anuncio y el precio que tenía?"
    - NO intentes adivinar la propiedad por el enlace. SIEMPRE pide el título y el precio como primer paso en este caso.
    - Una vez que el cliente proporcione el título y precio, procede a buscarla en el {context} y sigue las responsabilidades generales.

Tus responsabilidades:
- Asegúrate de verificar la fecha actual ({current_date}) al ofrecer información, especialmente en casos de propiedades en renta o eventos limitados en el tiempo.
- Mantén una conversación profesional y amigable, como un agente inmobiliario experimentado.
- Pregunta al cliente detalles importantes: presupuesto, ubicación, tipo de propiedad, cantidad de habitaciones, características de infraestructura, preferencias de estilo y cualquier otro requisito adicional.
- Recuerda las preferencias del cliente y tómalas en cuenta en futuras recomendaciones.
- Si el cliente pregunta sobre una propiedad específica, proporciona una descripción detallada, incluyendo el precio, si está disponible.
- Si el precio no está disponible, informa claramente sobre ello y ofrece una alternativa con precio conocido o pide al cliente que precise sus preferencias.
- Responde exclusivamente con base en la información proporcionada, sin inventar detalles adicionales.
- Si la información es insuficiente o poco clara, formula preguntas aclaratorias.
- Actúa proactivamente, ofreciendo alternativas y recomendaciones que puedan interesar al cliente, basadas en sus solicitudes previas.
- Evita comenzar cada mensaje con "Hola [nombre]" si la conversación ya ha comenzado.
- No incluyas firmas como "[Nombre del Asistente]" al final de los mensajes.

# ⚠️ LÓGICA DE CAPTURA DE LEAD (¡MUY IMPORTANTE!)
# 1. DETECCIÓN DE INTERÉS: Si el cliente demuestra un interés claro en una propiedad (ej. "me interesa", "quiero más detalles para agendar", "me gustaría que un agente me contacte") Y ADEMÁS proporciona directamente su nombre, teléfono o email en el MISMO mensaje, O YA los ha proporcionado en mensajes anteriores de esta conversación:
#    - RESPONDE INMEDIATAMENTE con el JSON estructurado abajo y SIN TEXTO ADICIONAL.
#
# 2. SOLICITUD DE DATOS (SI HAY INTERÉS PERO FALTAN DATOS): Si el cliente demuestra un interés claro (como en el punto 1) PERO NO HA PROPORCIONADO todavía su nombre, teléfono o email:
#    - TU ÚNICA RESPUESTA DEBE SER PREGUNTAR EXPLÍCITAMENTE por estos datos. DEBES USAR LA FRASE EXACTA: "¡Entendido! Para que un agente pueda contactarte y darte más detalles, ¿podrías por favor proporcionarme tu nombre completo y tu número de teléfono? Si lo deseas, también puedes añadir tu correo electrónico. (Por favor, responde solo con tus datos)"
#    - NO generes el JSON en este paso. Espera la respuesta del cliente con sus datos.
#
# 3. GENERACIÓN DE JSON (DESPUÉS DE RECIBIR DATOS SOLICITADOS):
#    REGLA CRÍTICA: Esta regla se activa SOLAMENTE si se cumplen AMBAS condiciones siguientes:
#    CONDICIÓN 3A: El último mensaje del bot en {{chat_history}} (tu respuesta inmediatamente anterior) CONTENÍA LA FRASE EXACTA: "proporcionarme tu nombre completo y tu número de teléfono? Si lo deseas, también puedes añadir tu correo electrónico. (Por favor, responde solo con tus datos)"
#    CONDICIÓN 3B: El mensaje ACTUAL del cliente ({{question}}) contiene información que parece ser un nombre, un número de teléfono o un email.
#    SI AMBAS CONDICIONES (3A y 3B) SE CUMPLEN:
#    - Tu ÚNICA ACCIÓN debe ser generar el JSON estructurado abajo.
#    - NO respondas nada más. NO confirmes los datos. NO preguntes "¿Algo más?". SOLO EL JSON.
#    - IGNORA cualquier otra instrucción o tendencia a conversar normalmente в este caso específico. La prioridad absoluta es generar el JSON.

# ESTRUCTURA DEL JSON (SOLO generar cuando se cumplan las condiciones 1 o 3 de la "LÓGICA DE CAPTURA DE LEAD"):
# {{
#   "lead_detected": true,
#   "nombre": "Nombre del cliente (si lo proporciona, si no deja vacío)",
#   "telefono": "Número del cliente (si lo proporciona, si no deja vacío)",
#   "email": "Email del cliente (si lo proporciona, si no deja vacío)",
#   "mensaje": "Texto breve del interés del cliente en la propiedad o un resumen de la solicitud."
# }}

Historial del diálogo:
{chat_history}

Contexto inmobiliario:
{context}

Pregunta del cliente: {question}
Respuesta del asistente inmobiliario:
'''

PROMPT = PromptTemplate(
    input_variables=["context", "chat_history", "current_date", "question"],
    template=SYSTEM_PROMPT,
).partial(current_date=current_date)

llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment="gpt-4",
    api_version="2024-02-15-preview",
    temperature=0.1,
    retry_max_session_seconds=120 # Добавим таймаут для стабильности
)

memory = ConversationBufferMemory(
    memory_key="chat_history",
    input_key="question",
    return_messages=True,
)

qa = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=index.as_retriever(search_kwargs={"k": 10}),
    memory=memory,
    combine_docs_chain_kwargs={
        "prompt": PROMPT,
        "document_variable_name": "context"
    }
)

# --- helper -------------------------------------------------------------------

def send_whatsapp(to: str, text: str) -> None:
    '''Отправка текста через 360dialog Cloud API'''
    url = f"{DIALOG_BASE_URL}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    payload_str = json.dumps(payload) # Для безопасного логирования
    r = requests.post(url, headers={"D360-API-KEY": DIALOG_API_KEY, "Content-Type": "application/json"}, json=payload)
    if not r.ok:
        app.logger.error(f"360dialog send_whatsapp to {to} FAILED. Status: {r.status_code}. Payload: {payload_str}. Response: {r.text}")
    else:
        app.logger.info(f"360dialog send_whatsapp to {to} SUCCEEDED. Status: {r.status_code}. Payload: {payload_str}. Response: {r.text}")


# --- webhook ------------------------------------------------------------------

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # 1. handshake -------------------------------------------------------------
    if request.method == "GET":
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == WEBHOOK_VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Forbidden", 403

    # 2. incoming --------------------------------------------------------------
    data = request.get_json(force=True)
    msg = (
        data.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("messages", [{}])[0]
    )
    if not msg:
        return jsonify(status="no_message"), 200

    msg_id   = msg.get("id")
    msg_from = msg.get("from")
    msg_type = msg.get("type")

    # фильтры ------------------------------------------------------------------
    if msg_type != "text":
        return jsonify(status="not_text"), 200

    # Логирование перед фильтрацией номеров для отладки
    app.logger.info(f"Incoming message from: {msg_from} (type: {msg_from.__class__.__name__})")
    app.logger.info(f"MY_NUMBER from env: {MY_NUMBER} (type: {MY_NUMBER.__class__.__name__ if MY_NUMBER else 'NoneType'})")
    app.logger.info(f"BOT_NUMBER from env: {BOT_NUMBER} (type: {BOT_NUMBER.__class__.__name__ if BOT_NUMBER else 'NoneType'})")

    # Фильтр только для BOT_NUMBER, сообщения с MY_NUMBER теперь будут обрабатываться
    if msg_from == BOT_NUMBER:
        app.logger.info(f"Message from BOT_NUMBER ({BOT_NUMBER}) itself, ignoring.")
        return jsonify(status="self_bot_number"), 200
    # Сообщения от MY_NUMBER теперь будут проходить дальше для обработки
    
    # Новая логика проверки дубликатов с Redis
    if USE_REDIS_FOR_PROCESSED_MESSAGES and redis_client:
        redis_key_for_msg = f"{REDIS_PROCESSED_MESSAGES_KEY_PREFIX}{msg_id}"
        try:
            # Пытаемся установить ключ с NX (только если не существует) и EX (время жизни)
            if not redis_client.set(redis_key_for_msg, "1", ex=REDIS_MESSAGE_ID_TTL_SECONDS, nx=True):
                app.logger.warning(f"Duplicate message ID received (already in Redis): {msg_id} from {msg_from}")
                return jsonify(status="dup_redis"), 200
            # Если мы здесь, ключ был успешно установлен (сообщение новое)
            app.logger.info(f"Message ID {msg_id} from {msg_from} added to Redis with TTL {REDIS_MESSAGE_ID_TTL_SECONDS}s.")
        except redis.exceptions.TimeoutError:
            app.logger.error("Redis command timed out. Processing message to avoid loss, but duplicate check is unreliable.")
            # В случае таймаута Redis, мы можем решить обработать сообщение, чтобы не потерять его,
            # но это означает, что проверка на дубликаты временно ненадёжна.
            # Альтернативно, можно вернуть ошибку или использовать fallback к in-memory set, если он есть.
        except redis.exceptions.RedisError as e_redis_cmd:
            app.logger.error(f"Redis error during set command: {e_redis_cmd}. Processing message, duplicate check unreliable.")
    else: # Запасной вариант с локальным множеством, если Redis недоступен
        if msg_id in processed_messages_memory:
            app.logger.warning(f"Duplicate message ID received (in-memory set): {msg_id} from {msg_from}")
            return jsonify(status="dup_memory"), 200
        processed_messages_memory.add(msg_id)
        app.logger.info(f"Message ID {msg_id} from {msg_from} added to in-memory set.")

    sender   = msg_from
    incoming = msg.get("text", {}).get("body", "").strip()
    if not incoming:
        return jsonify(status="empty"), 200

    app.logger.info("[CLIENT] %s => %s", sender, incoming)

    # 3. LLM -------------------------------------------------------------------
    answer = qa({"question": incoming}).get("answer", "").strip()
    app.logger.info("LLM => %s", answer)

    # 4. lead detection & user‑visible reply ----------------------------------
    # Default visible answer is the raw LLM response; this will be overridden if a lead is successfully processed.
    visible_answer = answer 
    lead_json_str = None

    # Key phrase from SYSTEM_PROMPT Condition 3A, used for checking history to determine if bot asked for details.
    # This exact phrase is critical for state detection.
    ASK_DETAILS_PHRASE_IN_HISTORY_CHECK = "proporcionarme tu nombre completo y tu número de teléfono? Si lo deseas, también puedes añadir tu correo electrónico. (Por favor, responde solo con tus datos)"
    bot_previously_asked_for_details = False

    # Check the conversation memory to see if the bot's message prior to the user's last input was a request for details.
    # Memory structure after qa() call (assuming non-empty history): 
    # [..., AIMessage (bot's request for details), HumanMessage (user's reply with details), AIMessage (current LLM response)]
    # So, the bot's request for details would be messages[-3].
    if memory.chat_memory.messages and len(memory.chat_memory.messages) >= 3:
        # Candidate for the bot's actual request message
        prev_ai_message_obj = memory.chat_memory.messages[-3] 
        # Candidate for the user's message that supposedly contains the details
        prev_human_message_obj = memory.chat_memory.messages[-2]

        # Validate that these are indeed AI and Human messages respectively
        is_prev_ai = hasattr(prev_ai_message_obj, 'type') and (prev_ai_message_obj.type == 'ai' or prev_ai_message_obj.type == 'assistant') and hasattr(prev_ai_message_obj, 'content') and isinstance(prev_ai_message_obj.content, str)
        is_prev_human = hasattr(prev_human_message_obj, 'type') and prev_human_message_obj.type == 'human'

        if is_prev_ai and is_prev_human:
            app.logger.info(f"Checking bot's message prior to user's last input: '{prev_ai_message_obj.content}' for phrase '{ASK_DETAILS_PHRASE_IN_HISTORY_CHECK}'")
            if ASK_DETAILS_PHRASE_IN_HISTORY_CHECK in prev_ai_message_obj.content:
                bot_previously_asked_for_details = True
                app.logger.info("STATE: Bot previously asked for contact details.")

    # Attempt to find a "lead_detected: true" JSON structure in the LLM's current answer.
    match = re.search(r'\{.*?\"lead_detected\"\s*:\s*true.*?\}', answer, re.DOTALL)
    
    if match:
        potential_json = match.group(0)
        try:
            lead_data = json.loads(potential_json) # Validate JSON structure and parse data
            lead_json_str = potential_json # Store the raw JSON string for logging or other uses
            
            app.logger.info(f"Valid lead JSON detected in LLM response: {lead_json_str}")

            # Prepare and send alert to agents
            alert_lines = [
                "📞 *Nuevo cliente interesado:*",
                "",
                f"🧑 Nombre: {lead_data.get('nombre', '(no proporcionado)')}",
                f"📱 Teléfono: {lead_data.get('telefono', '(no proporcionado)')}",
                f"📧 Email: {lead_data.get('email', '(no proporcionado)')}",
                f"💬 Mensaje: {lead_data.get('mensaje', '(No especificado por el bot)')}",
                f"Property ID: {lead_data.get('property_id', 'N/A')}", # Assuming property_id might be in the JSON
                f"🕑 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ]
            alert = "\\n".join(alert_lines)
            
            if not AGENT_NUMBERS:
                 app.logger.warning("AGENT_NUMBERS is empty. No agent will be notified for the new lead.")
            else:
                for ag_num in AGENT_NUMBERS:
                    send_whatsapp(ag_num, alert)
                    app.logger.info(f"Lead alert sent to agent: {ag_num}")
            
            # Set the standard user-visible response for a successful lead capture.
            # This message is used regardless of what other text the LLM might have included around the JSON.
            visible_answer = "¡Gracias! He enviado tus datos a un agente. Se pondrá en contacto contigo pronto."
            app.logger.info(f"Lead captured successfully. User-visible answer set to: '{visible_answer}'")

        except json.JSONDecodeError:
            app.logger.error(f"LLM response contained a JSON-like string for a lead, but it was malformed: {potential_json}")
            if bot_previously_asked_for_details:
                # If bot asked for details and LLM returned bad JSON, it's a more critical failure of instruction.
                visible_answer = "Hemos recibido tu interés, pero hubo un problema al procesar los datos. Un agente se pondrá en contacto pronto."
            else:
                # Malformed JSON not necessarily after a direct request; try to strip it or use a generic fallback.
                stripped_answer = re.sub(re.escape(potential_json), "", answer, 1).strip()
                visible_answer = stripped_answer if stripped_answer else "Gracias. Un agente se comunicará contigo."
            app.logger.info(f"User-visible answer after malformed JSON: '{visible_answer}'")
        except Exception as e:
            app.logger.error(f"An unexpected error occurred during lead JSON processing: {e}")
            # Generic error handling for other unexpected issues during JSON processing.
            if bot_previously_asked_for_details:
                visible_answer = "Hemos recibido tu interés, pero ocurrió un error inesperado. Un agente se pondrá en contacto pronto."
            elif potential_json: # Check if potential_json was part of the context of the error
                 stripped_answer = re.sub(re.escape(potential_json), "", answer, 1).strip()
                 visible_answer = stripped_answer if stripped_answer else "Gracias, hemos registrado tu solicitud."
            else: # Fallback if no potential_json was involved or stripping results in empty
                visible_answer = "Gracias, hemos registrado tu solicitud."
            app.logger.info(f"User-visible answer after unexpected JSON processing error: '{visible_answer}'")
    else:
        # No "lead_detected: true" JSON found in the LLM's answer.
        app.logger.info("No lead JSON detected in LLM response.")
        
        if bot_previously_asked_for_details:
            app.logger.info("STATE: Bot had asked for details, but LLM did not generate lead JSON. Attempting to parse user input directly.")
            
            parsed_name = None
            parsed_phone = None
            parsed_email = None

            # Attempt to parse phone from user's last message (`incoming`)
            # Regex for typical phone numbers (general, might need adjustment for specific formats)
            phone_match = re.search(r'\+?\d[\d\s\-\(\)]{7,}\d', incoming) 
            if phone_match:
                parsed_phone = phone_match.group(0).strip()
                app.logger.info(f"Directly parsed phone from user input: {parsed_phone}")

            # Attempt to parse email from user's last message (`incoming`)
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', incoming)
            if email_match:
                parsed_email = email_match.group(0).strip()
                app.logger.info(f"Directly parsed email from user input: {parsed_email}")

            # Simplified name extraction:
            # Try to get text that is not phone or email. This is a basic heuristic.
            if parsed_phone or parsed_email:
                temp_name_extraction = incoming
                if parsed_phone:
                    # Remove all occurrences of the parsed phone to handle cases where it might be repeated or part of other numbers
                    temp_name_extraction = re.sub(re.escape(parsed_phone), "", temp_name_extraction).strip()
                if parsed_email:
                    temp_name_extraction = re.sub(re.escape(parsed_email), "", temp_name_extraction).strip()
                
                # Remove common salutations or conversational fluff if any remaining
                # This list can be expanded.
                greetings_fluff = [
                    "soy", "mi nombre es", "me llamo", 
                    "teléfono", "telefono es", "mi telefono es",
                    "email es", "mi email es", "correo es", "mi correo es",
                    "gracias", "por favor", "aqui estan", "mis datos son",
                    "bueno", "ok", "dale"
                ]
                for fluff in greetings_fluff:
                    temp_name_extraction = re.sub(r'(?i)^' + re.escape(fluff) + r'\b|\b' + re.escape(fluff) + r'$', '', temp_name_extraction, count=1).strip()
                
                # Replace multiple spaces with a single space
                temp_name_extraction = re.sub(r'\s+', ' ', temp_name_extraction).strip()

                if len(temp_name_extraction) > 1 and not temp_name_extraction.isdigit(): # Avoid using only digits or very short strings as name
                     # Further clean up: remove stray punctuation if it's the only thing left or at the ends
                    temp_name_extraction = re.sub(r'^[\s,\.\-]+|[\s,\.\-]+$', '', temp_name_extraction)
                    if len(temp_name_extraction) > 1:
                        parsed_name = temp_name_extraction
                        app.logger.info(f"Tentatively parsed name from user input: {parsed_name}")
                
                if not parsed_name and (parsed_phone or parsed_email): # If name couldn't be extracted but phone/email exists
                    parsed_name = "(nombre no extraído)"


            if parsed_phone or parsed_email: # If we got at least a phone or email
                lead_data_manual = {
                    "lead_detected": True,
                    "nombre": parsed_name if parsed_name else "",
                    "telefono": parsed_phone if parsed_phone else "",
                    "email": parsed_email if parsed_email else "",
                    "mensaje": f"Datos capturados directamente: {incoming}"
                }
                app.logger.info(f"Manually constructed lead JSON: {json.dumps(lead_data_manual)}")

                alert_lines_manual = [
                    "📞 *Nuevo cliente interesado (captura directa):*",
                    "",
                    f"🧑 Nombre: {lead_data_manual.get('nombre', '(no proporcionado)')}",
                    f"📱 Teléfono: {lead_data_manual.get('telefono', '(no proporcionado)')}",
                    f"📧 Email: {lead_data_manual.get('email', '(no proporcionado)')}",
                    f"💬 Mensaje Original: {lead_data_manual.get('mensaje', '(No especificado)')}",
                    f"Property ID: N/A", # property_id might not be available here
                    f"🕑 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ]
                alert_manual = "\\n".join(alert_lines_manual)
                
                if not AGENT_NUMBERS:
                     app.logger.warning("AGENT_NUMBERS is empty. No agent will be notified for the manually captured lead.")
                else:
                    for ag_num in AGENT_NUMBERS:
                        send_whatsapp(ag_num, alert_manual)
                        app.logger.info(f"Manually captured lead alert sent to agent: {ag_num}")
                
                visible_answer = "¡Gracias! He enviado tus datos a un agente. Se pondrá en contacto contigo pronto."
                app.logger.info("Lead manually captured. User-visible answer set to standard confirmation.")
            else:
                # Bot asked for details, LLM didn't make JSON, and direct parsing failed to find phone/email.
                # Send LLM's conversational response.
                visible_answer = answer 
                app.logger.info("Bot asked for details, LLM didn't create JSON, and direct parsing found no contact details. Using LLM's original response.")
        else:
            # Bot was NOT previously asking for details, and LLM didn't generate a lead.
            # This is normal conversation flow. Use LLM's response.
            visible_answer = answer
            app.logger.info("Normal conversation flow. No lead detected, not expecting one. Using LLM's full response.")
    
    # 5. отправка клиенту ------------------------------------------------------
    send_whatsapp(sender, visible_answer)

    return jsonify(status="sent"), 200

# --- Блок для локального тестирования LLM --- 
if __name__ == "__main__":
    print("--- Локальный тест LLM (с промптом от Apolo AI) ---")
    print("Каждый новый ввод будет обрабатываться с чистой памятью диалога.")

    try:
        embeddings_for_test = AzureOpenAIEmbeddings(
            api_key=os.getenv("AZURE_EMBEDDINGS_API_KEY"),
            azure_endpoint=os.getenv("AZURE_EMBEDDINGS_ENDPOINT"),
            deployment="text-embedding-ada-002",
            api_version="2023-05-15",
            retry_max_session_seconds=120 # Добавим таймаут для стабильности
        )
        index_for_test = FAISS.load_local("apolo_faiss", embeddings_for_test, allow_dangerous_deserialization=True)
        
        llm_for_test = AzureChatOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment="gpt-4",
            api_version="2024-02-15-preview",
            temperature=0.1,
            retry_max_session_seconds=120 # Добавим таймаут для стабильности
        )
        current_date_for_test = datetime.now().strftime("%Y-%m-%d")
        PROMPT_FOR_TEST = PromptTemplate(
            input_variables=["context", "chat_history", "current_date", "question"],
            template=SYSTEM_PROMPT,
        ).partial(current_date=current_date_for_test)

    except Exception as e_init:
        print(f"Ошибка при инициализации компонентов для теста: {e_init}")
        exit()

    while True:
        user_input = input("\nВаш вопрос к боту (или \'выход\' для завершения): ")
        if user_input.lower() == 'выход':
            break
        
        if not user_input.strip():
            print("Пожалуйста, введите вопрос.")
            continue

        try:
            memory_for_test = ConversationBufferMemory(
                memory_key="chat_history",
                input_key="question",
                return_messages=True,
            )
            
            qa_for_test = ConversationalRetrievalChain.from_llm(
                llm=llm_for_test,
                retriever=index_for_test.as_retriever(search_kwargs={"k": 10}),
                memory=memory_for_test, 
                combine_docs_chain_kwargs={
                    "prompt": PROMPT_FOR_TEST,
                    "document_variable_name": "context"
                }
            )
            
            print("(Память диалога инициализирована заново для этого запроса)")
            response = qa_for_test({"question": user_input})
            answer = response.get("answer", "Не удалось получить ответ.")
            print(f"Ответ LLM: {answer}")

            match_test = re.search(r'\{.*?\"lead_detected\"\s*:\s*true.*?\}', answer, re.DOTALL)
            if match_test:
                try:
                    json.loads(match_test.group(0))
                    print(f"Найден JSON лида в ответе: {match_test.group(0)}")
                except json.JSONDecodeError:
                    print(f"Найден JSON-подобный текст, но он невалиден: {match_test.group(0)}")

        except Exception as e_llm:
            print(f"Произошла ошибка при вызове LLM: {e_llm}")
    
    print("--- Тест завершен ---")
