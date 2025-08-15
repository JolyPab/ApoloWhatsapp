from twilio.rest import Client
import logging
from config import settings

logger = logging.getLogger(__name__)

class TwilioClient:
    def __init__(self):
        if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_PHONE_NUMBER]):
            raise ValueError("Twilio credentials are not fully configured.")
        
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = f'whatsapp:{settings.TWILIO_PHONE_NUMBER}'

    MAX_CHARS_PER_MESSAGE = 1500  # немного меньше лимита Twilio для запаса

    def _split_body(self, body: str) -> list[str]:
        """Разбивает длинный текст на безопасные части по ~1500 символов.
        Пытаемся делить по абзацам/строкам/точкам.
        """
        if not body or len(body) <= self.MAX_CHARS_PER_MESSAGE:
            return [body]

        chunks: list[str] = []
        remaining = body
        limit = self.MAX_CHARS_PER_MESSAGE

        while remaining:
            if len(remaining) <= limit:
                chunks.append(remaining)
                break

            # Ищем естественную точку разрыва в пределах лимита
            window = remaining[:limit]
            split_idx = max(
                window.rfind("\n\n"),
                window.rfind("\n"),
                window.rfind(". "),
                window.rfind("; "),
                window.rfind(" - "),
            )
            if split_idx == -1:
                split_idx = limit

            chunk = remaining[:split_idx].rstrip()
            if not chunk:
                # защита от зацикливания
                chunk = remaining[:limit]
                split_idx = limit
            chunks.append(chunk)
            remaining = remaining[split_idx:].lstrip()

        return chunks

    def send_whatsapp_message(self, to_number: str, body: str, media_url: str = None):
        """
        Sends a WhatsApp message to a specified number with optional media.
        Если текст превышает лимит Twilio, автоматически разбиваем на несколько сообщений.
        Медиа прикладываем только к первому сообщению.
        """
        try:
            to_number_formatted = f'whatsapp:{to_number}'
            parts = self._split_body(body)

            for idx, part in enumerate(parts):
                message_params = {
                    'from_': self.from_number,
                    'body': part,
                    'to': to_number_formatted
                }

                # Add media URL only to the very first part
                if idx == 0 and media_url:
                    message_params['media_url'] = [media_url]

                message = self.client.messages.create(**message_params)
                logger.info(
                    f"Message sent to {to_number}: SID {message.sid}, part {idx+1}/{len(parts)}, Media: {bool(idx==0 and media_url)}"
                )
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {to_number}: {e}")
            return False
    
    def send_whatsapp_message_with_multiple_photos(self, to_number: str, body: str, photo_urls: list):
        """
        Sends multiple photos as separate messages to WhatsApp.
        WhatsApp via Twilio supports only one media per message.
        """
        if not photo_urls:
            return self.send_whatsapp_message(to_number, body)
        
        success_count = 0
        
        # Send first photo with the first text part
        if self.send_whatsapp_message(to_number, body, photo_urls[0]):
            success_count += 1
        
        # Send additional photos (limit to 3-4 total to avoid spam)
        for photo_url in photo_urls[1:4]:  # Send max 4 photos total
            if self.send_whatsapp_message(to_number, "", photo_url):
                success_count += 1
        
        logger.info(f"Sent {success_count} media messages to {to_number}")
        return success_count > 0

# Singleton instance
twilio_client = TwilioClient() 