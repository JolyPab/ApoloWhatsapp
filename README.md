# Apolo Real Estate WhatsApp Bot

This project is a sophisticated WhatsApp bot for the real estate agency "Apolo", designed to interact with clients, provide information about properties, and identify potential leads.

It's built with Flask, Twilio for WhatsApp communication, and Azure OpenAI with LangChain for advanced natural language understanding and generation.

## Project Structure

The project follows a modular architecture for clarity and maintainability:

```
/
├── bot/
│   ├── app.py              # Main Flask application, handles webhooks.
│   ├── config.py           # Centralized configuration for all services.
│   │
│   ├── core/
│   │   ├── llm_chain.py      # Handles all LangChain and AI model interactions.
│   │   ├── lead_detector.py  # Analyzes messages to identify sales leads.
│   │   └── logic.py          # Core business logic orchestrating the bot's responses.
│   │
│   └── utils/
│       ├── redis_client.py   # Manages connection and operations with Redis.
│       └── twilio_client.py  # Encapsulates all Twilio API interactions.
│
├── apolo_faiss/            # Directory for the FAISS vector store index.
├── requirements.txt        # Python package dependencies.
├── startup.sh              # Startup script for Gunicorn (used by Azure).
└── .env                    # (Optional) For local environment variables.
```

## Setup and Configuration

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Variables**:
    Create a `.env` file in the root directory or set the following environment variables in your deployment environment (like Azure App Service Configuration):

    ```
    # Twilio Configuration
    TWILIO_ACCOUNT_SID=your_account_sid
    TWILIO_AUTH_TOKEN=your_auth_token
    TWILIO_PHONE_NUMBER=your_twilio_whatsapp_number
    LEAD_NOTIFICATION_NUMBER=realtor_number_to_receive_leads

    # Redis Configuration
    REDIS_HOST=your_redis_host
    REDIS_PORT=6380
    REDIS_PASSWORD=your_redis_password
    REDIS_USERNAME=default

    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
    AZURE_OPENAI_API_KEY=your_openai_api_key
    OPENAI_API_VERSION=2023-05-15
    AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name

    # FAISS Index Path (optional, defaults to 'apolo_faiss')
    FAISS_INDEX_PATH=apolo_faiss
    ```

## How to Run

### Local Development

For testing locally, you can run the Flask development server. It's recommended to use a tool like `ngrok` to expose your local server to the internet so you can configure it as a webhook in Twilio.

```bash
flask run --port 5000
```

### Production (Azure)

The `startup.sh` script is configured to run the application using Gunicorn. Azure App Service will automatically use this script.

1.  **Deployment**: Deploy the application code to Azure App Service.
2.  **Configuration**: Set the environment variables listed above in the App Service's "Configuration" section.
3.  **Webhook**: In your Twilio console, set the WhatsApp webhook URL to `https://<your-app-name>.azurewebsites.net/webhook`.

## Key Features

-   **Modular Design**: Easy to understand, maintain, and extend.
-   **Lead Detection**: A dedicated module analyzes user intent to identify potential customers and forwards leads to a configured number.
-   **Property Photos**: Image links in responses are automatically sent as WhatsApp images.
-   **RAG (Retrieval-Augmented Generation)**: Uses a FAISS vector store to provide answers based on your specific property data.
-   **Session Management**: Uses Redis to maintain conversation history and prevent processing duplicate messages.
-   **Centralized Configuration**: All settings are managed in one place.
