import logging
import re
from utils.redis_client import redis_client
from utils.twilio_client import twilio_client
from core.llm_chain import llm_chain
from core.lead_detector import lead_detector
from core.smart_router import smart_router
from config import settings

logger = logging.getLogger(__name__)

def process_message(from_number: str, message_body: str, message_sid: str):
    """
    Main logic for processing an incoming WhatsApp message.
    """
    # 1. Deduplication
    if redis_client.is_duplicate(message_sid):
        return

    logger.info(f"Processing message from {from_number}: '{message_body}'")

    # 2. Smart Routing Analysis
    routing_analysis = smart_router.analyze_message(message_body)
    logger.info(f"Routing strategy: {routing_analysis['strategy']} - {routing_analysis['routing_reason']}")

    # 3. Lead Detection
    lead_info = lead_detector.analyze_message(message_body)
    if lead_info.get("is_lead"):
        handle_lead(from_number, lead_info)

    # 4. Generate response based on routing strategy
    if routing_analysis['strategy'] == 'consultant':
        # Консультативный режим для внешних ссылок
        extracted_info = routing_analysis['extracted_info']
        smart_query = smart_router.generate_smart_query(message_body, extracted_info)
        bot_response = llm_chain.invoke_chain(smart_query, from_number)
        bot_response = smart_router.format_consultant_response(bot_response, extracted_info)
    else:
        # Обычный режим с использованием памяти чата
        bot_response = llm_chain.invoke_chain(message_body, from_number)

    # 5. Extract image URLs and send the response back to the user
    image_urls = re.findall(r'https?://\S+\.(?:png|jpg|jpeg)', bot_response, flags=re.IGNORECASE)
    text_response = re.sub(r'https?://\S+\.(?:png|jpg|jpeg)', '', bot_response, flags=re.IGNORECASE).strip()
    twilio_client.send_whatsapp_message(from_number, text_response or ' ', media_urls=image_urls or None)

    logger.info(f"Response sent to {from_number}")


def handle_lead(user_number: str, lead_data: dict):
    """Handles a detected lead."""
    logger.info(f"LEAD DETECTED for user {user_number}!")
    logger.info(f"Lead Details: {lead_data}")

    realtor_number = settings.LEAD_NOTIFICATION_NUMBER
    if realtor_number:
        lead_message = f"Nuevo lead de {user_number}: {lead_data}"
        twilio_client.send_whatsapp_message(realtor_number, lead_message)

    interest = lead_data.get("interest")
    if interest == "visit":
        twilio_client.send_whatsapp_message(
            user_number,
            "¡Excelente! Un asesor se pondrá en contacto contigo en breve para coordinar los detalles de tu visita."
        )
    elif interest in ["buy", "rent"]:
        twilio_client.send_whatsapp_message(
            user_number,
            "¡Perfecto! Gracias por tu interés. Un asesor te contactará pronto para darte más información."
        )
