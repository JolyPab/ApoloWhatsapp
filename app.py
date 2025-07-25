import logging
from flask import Flask, request, Response
from config import settings
from core.logic import process_message

# Configure logging
logging.basicConfig(level=settings.LOGGING_LEVEL)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Handles incoming WhatsApp messages from Twilio.
    """
    try:
        data = request.values
        message_sid = data.get('MessageSid')
        from_number = data.get('From', '').split(':')[-1]
        message_body = data.get('Body', '')

        if not all([message_sid, from_number, message_body]):
            logger.warning(f"Invalid payload received: {data}")
            return Response(status=400)

        process_message(
            from_number=from_number,
            message_body=message_body,
            message_sid=message_sid
        )

    except Exception as e:
        logger.exception(f"An error occurred in the webhook: {e}")
        # Return a 200 status even on errors to prevent Twilio from retrying
    
    return Response(status=200)

if __name__ == "__main__":
    # This is for local development testing only
    # Use a WSGI server like Gunicorn in production
    app.run(port=5000, debug=True) 