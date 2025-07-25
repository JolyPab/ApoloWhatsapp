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

    def send_whatsapp_message(self, to_number: str, body: str):
        """
        Sends a WhatsApp message to a specified number.
        """
        try:
            to_number_formatted = f'whatsapp:{to_number}'
            message = self.client.messages.create(
                from_=self.from_number,
                body=body,
                to=to_number_formatted
            )
            logger.info(f"Message sent to {to_number}: SID {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {to_number}: {e}")
            return False

# Singleton instance
twilio_client = TwilioClient() 