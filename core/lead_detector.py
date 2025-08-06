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
        Analiza el siguiente mensaje del usuario en un chat inmobiliario.
        Tu tarea es determinar si el usuario expresa una intención clara de comprar, rentar o agendar una visita a una propiedad.

        Responde SOLO con un objeto JSON en el siguiente formato:
        {{
            "is_lead": booleano,
            "interest": "buy" | "rent" | "visit" | "inquiry" | "none",
            "property_mentions": ["property_name_1", "property_name_2"]
        }}

        - "is_lead": verdadero si el usuario muestra interés concreto (por ejemplo, "quiero verlo", "estoy interesado en comprar", "podemos agendar una visita?"). Falso para preguntas generales o saludos.
        - "interest":
            - "buy": el usuario quiere comprar.
            - "rent": el usuario quiere rentar.
            - "visit": el usuario pide explícitamente ver una propiedad.
            - "inquiry": el usuario hace preguntas específicas pero aún no se compromete a visitar/comprar.
            - "none": no hay interés mostrado (por ejemplo, "hola", "gracias").
        - "property_mentions": lista de nombres o direcciones de propiedades mencionadas en el mensaje.

        Mensaje del usuario: "{message}"

        Respuesta JSON:
        """

# Singleton instance
lead_detector = LeadDetector(llm_chain)
