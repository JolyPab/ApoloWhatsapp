import logging
import json
from core.llm_chain import llm_chain

logger = logging.getLogger(__name__)

class LeadDetector:
    def __init__(self, llm_instance):
        self.llm = llm_instance.llm # Use the same LLM instance

    def analyze_message(self, message: str) -> dict:
        """
        Analyzes a user's message to detect if it's a lead.
        Returns a dictionary with lead information.
        """
        prompt = self._create_lead_detection_prompt(message)
        
        try:
            response = self.llm.invoke(prompt)
            logger.info(f"Lead detection raw response: {response.content}")
            
            # Basic cleaning of the response
            cleaned_response = response.content.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:-4].strip()

            lead_data = json.loads(cleaned_response)
            return lead_data

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse lead detection response: {e}")
            return {"is_lead": False, "reason": "parsing_error"}

    @staticmethod
    def _create_lead_detection_prompt(message: str) -> str:
        return f"""
        Analyze the following user message from a real estate chat.
        Your task is to determine if the user is expressing a clear intent to buy, rent, or schedule a visit for a property.

        Respond ONLY with a JSON object in the following format:
        {{
            "is_lead": boolean,
            "interest": "buy" | "rent" | "visit" | "inquiry" | "none",
            "property_mentions": ["property_name_1", "property_name_2"]
        }}

        - "is_lead": true if the user shows concrete interest (e.g., "I want to see it", "I'm interested in buying", "Can we schedule a visit?"). False for general questions or greetings.
        - "interest": 
            - "buy": User wants to purchase.
            - "rent": User wants to rent.
            - "visit": User explicitly asks to see a property.
            - "inquiry": User is asking specific questions about a property but hasn't committed to a visit/purchase yet.
            - "none": No interest shown (e.g., "hello", "thank you").
        - "property_mentions": A list of any specific property names or addresses mentioned in the message.

        User Message: "{message}"

        JSON Response:
        """

# Singleton instance
lead_detector = LeadDetector(llm_chain) 