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
        Analiza el siguiente mensaje de un cliente en un chat de bienes raíces.
        Tu tarea es determinar si el usuario expresa una intención clara de comprar, rentar o agendar una visita.

        Responde SOLO con un objeto JSON en el siguiente formato:
        {{
            "is_lead": boolean,
            "interest": "buy" | "rent" | "visit" | "inquiry" | "none",
            "property_mentions": ["nombre_propiedad_1", "nombre_propiedad_2"]
        }}

        - "is_lead": true si el usuario muestra interés concreto (ej: "quiero verla", "me interesa comprar", "podemos agendar una visita?"). False para preguntas generales o saludos.
        - "interest": 
            - "buy": Usuario quiere comprar (palabras clave: "comprar", "adquirir", "me interesa comprar")
            - "rent": Usuario quiere rentar (palabras clave: "rentar", "alquilar", "renta")  
            - "visit": Usuario solicita explícitamente ver una propiedad (palabras clave: "visita", "ver", "conocer", "mostrar")
            - "inquiry": Usuario hace preguntas específicas sobre una propiedad pero no se compromete a visita/compra
            - "none": No muestra interés (ej: "hola", "gracias", preguntas muy generales)
        - "property_mentions": Lista de nombres específicos de propiedades o direcciones mencionadas.

        SEÑALES DE LEAD REAL:
        - Menciona querer "ver", "visitar", "conocer" una propiedad específica
        - Expresa interés en "comprar" o "adquirir"
        - Pregunta sobre "agendar", "cita", "visita"
        - Menciona estar "interesado/a" en una propiedad específica
        - Pregunta sobre disponibilidad para ver propiedades

        Mensaje del Usuario: "{message}"

        JSON Response:
        """

# Singleton instance
lead_detector = LeadDetector(llm_chain) 