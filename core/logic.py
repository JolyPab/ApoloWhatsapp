import logging
from utils.redis_client import redis_client
from utils.twilio_client import twilio_client
from utils.property_extractor import property_extractor
from core.llm_chain import llm_chain
from core.lead_detector import lead_detector
from core.smart_router import smart_router

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

    def _is_real_lead(info: dict) -> bool:
        """Строже определяем реальный лид:
        - visit: всегда лид
        - buy/rent: лид ТОЛЬКО если есть явное желание контакта/встречи
          И/ИЛИ упоминание конкретного объекта (property_mentions или указательные слова)
        Примеры НЕ лида: «Quiero comprar un departamento en Cancún», «Busco casa en Cancún».
        Примеры лида: «¿Puedo agendar una visita?», «Llámame para ver este depto», «Quiero ver esta casa mañana».
        """
        if not info.get("is_lead"):
            return False
        interest = info.get("interest")
        if interest == "visit":
            return True
        if interest in ("buy", "rent"):
            lowered = message_body.lower()
            contact_kw = [
                "llamame", "llámame", "llamar", "contáctame", "contactame", "contactar",
                "agendar", "agenda", "cita", "ver", "visita", "mostrar"
            ]
            specific_kw = [
                "esta", "este", "esa", "ese", "la casa", "el departamento",
                "esta casa", "este departamento", "inmuebles24", 
            ]
            has_contact_intent = any(k in lowered for k in contact_kw)
            has_specific_ref = bool(info.get("property_mentions")) or any(k in lowered for k in specific_kw)
            # Для buy/rent требуем либо явный запрос контакта/встречи, либо конкретику по объекту
            return has_contact_intent or has_specific_ref
        return False

    if _is_real_lead(lead_info):
        # Обрабатываем лид: отправляем уведомление агенту и пользователю, дальше ответ не нужен
        handle_lead(from_number, message_body, lead_info)
        return

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

    # 5. Decide whether to send photos (only for real estate-related queries)
    def _explicit_photo_request(text: str) -> bool:
        text_l = text.lower()
        return any(k in text_l for k in ["foto", "fotos", "imágen", "imagenes", "imágenes", "mandame fotos", "envíame fotos", "enviame fotos"])  # noqa

    def _has_specific_reference(text: str) -> bool:
        text_l = text.lower()
        specific_kw = [
            "esta", "este", "esa", "ese", "la casa", "el departamento", "residencial", "calle", "avenida", "av.", "boulevard"
        ]
        return any(k in text_l for k in specific_kw)

    should_attach_photos = (
        routing_analysis['strategy'] in ('consultant',)
        or _is_real_lead(lead_info)
        or _explicit_photo_request(message_body)
        or _has_specific_reference(message_body)
    )

    if should_attach_photos:
        # Extract property information from the bot response and try to send photos
        properties_mentioned = property_extractor.extract_property_info_from_response(bot_response)

        if properties_mentioned:
            # Берем только достаточно релевантные объекты (match_score >= 3)
            strong_matches = [p for p in properties_mentioned if p.get('match_score', 0) >= 3]
            first_property = (strong_matches or properties_mentioned)[0]
            photos = first_property.get('photos', [])

            if photos:
                twilio_client.send_whatsapp_message_with_multiple_photos(
                    from_number, bot_response, photos
                )
                logger.info(f"Response with {len(photos)} photos sent to {from_number}")
                return

    # Fallback: send text-only response
    twilio_client.send_whatsapp_message(from_number, bot_response)
    logger.info(f"Response sent to {from_number}")


def handle_lead(user_number: str, original_message: str, lead_data: dict):
    """Обрабатываем лид: уведомляем агента и подтверждаем пользователю."""
    logger.info(f"LEAD DETECTED for user {user_number}!")
    logger.info(f"Lead Details: {lead_data}")

    # 1. Отправляем подтверждение пользователю (одно короткое сообщение)
    interest = lead_data.get("interest")
    if interest == "visit":
        user_reply = (
            "¡Excelente! Un asesor se pondrá en contacto contigo en breve para coordinar los detalles de tu visita."
        )
    elif interest == "buy":
        user_reply = "¡Perfecto! Gracias por tu interés en comprar. Un asesor te contactará pronto."
    elif interest == "rent":
        user_reply = "¡Genial! Un asesor se pondrá en contacto contigo para ayudarte con la renta."
    else:
        user_reply = "¡Gracias! Un asesor te contactará en breve para más detalles."

    twilio_client.send_whatsapp_message(user_number, user_reply)

    # 2. Готовим уведомление агенту (используем тестовый номер из конфигурации)
    from config import settings
    agent_number = settings.AGENT_WHATSAPP_NUMBER
    if agent_number:
        # Извлекаем информацию о недвижимости из сообщения для более детального уведомления
        properties_info = property_extractor.extract_property_info_from_response(original_message)
        
        agent_msg = (
            f"🚨 *LEAD ALERT - Century21 Apolo*\n\n"
            f"📱 *Cliente WhatsApp:* {user_number}\n"
            f"🎯 *Tipo de interés:* {lead_data.get('interest').upper()}\n"
            f"💬 *Mensaje original:*\n{original_message}\n\n"
        )
        
        if lead_data.get('property_mentions'):
            agent_msg += f"🏠 *Propiedades mencionadas:* {', '.join(lead_data.get('property_mentions', []))}\n\n"
        
        if properties_info:
            prop = properties_info[0]  # Primera propiedad encontrada
            agent_msg += (
                f"🔍 *Propiedad relacionada:*\n"
                f"• {prop.get('title', 'N/A')}\n"
                f"• {prop.get('price', 'N/A')}\n"
                f"• {prop.get('address', 'N/A')}\n"
                f"• Agente: {prop.get('agent_name', 'N/A')}\n"
                f"• Tel: {prop.get('agent_phone', 'N/A')}\n\n"
            )
        
        agent_msg += "⚡ *Acción requerida:* Contactar al cliente lo antes posible"
        
        twilio_client.send_whatsapp_message(agent_number, agent_msg)
        logger.info(f"Enhanced lead notification sent to agent {agent_number}")
    else:
        logger.warning("AGENT_WHATSAPP_NUMBER не настроен – уведомление агенту не отправлено") 