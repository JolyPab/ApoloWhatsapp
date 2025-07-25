"""
Умный роутер для обработки внешних ссылок и переключения режимов бота
"""

import re
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class SmartRouter:
    """Умная маршрутизация запросов в зависимости от контекста"""
    
    def __init__(self):
        # Паттерны для извлечения информации из URL
        self.url_patterns = {
            'inmuebles24': {
                'pattern': r'inmuebles24\.com/propiedades/.*?-(.*?)-(.*?)-(.*?)-\d+\.html',
                'location_index': 2,  # Позиция города в URL
                'area_index': 1,      # Позиция района
                'type_index': 0       # Тип недвижимости
            }
        }
    
    def analyze_message(self, message: str) -> Dict:
        """
        Анализирует сообщение и определяет стратегию ответа
        """
        analysis = {
            'has_external_link': False,
            'extracted_info': {},
            'strategy': 'direct',  # direct, consultant, hybrid
            'routing_reason': ''
        }
        
        # Проверяем наличие внешних ссылок (приоритет выше!)
        external_info = self._extract_external_link_info(message)
        if external_info:
            analysis['has_external_link'] = True
            analysis['extracted_info'] = external_info
            analysis['strategy'] = 'consultant'
            analysis['routing_reason'] = f"Клиент интересуется объектом с {external_info.get('source', 'внешней платформы')}"
        # Проверяем упоминание конкретных адресов (только если нет внешних ссылок)
        elif self._mentions_specific_address(message):
            analysis['strategy'] = 'hybrid'
            analysis['routing_reason'] = "Упоминается конкретный адрес"
        
        return analysis
    
    def _extract_external_link_info(self, message: str) -> Optional[Dict]:
        """Извлекает информацию из внешних ссылок"""
        
        # Ищем ссылки на Inmuebles24
        inmuebles_match = re.search(r'inmuebles24\.com/propiedades/[^\s]+', message)
        if inmuebles_match:
            url = inmuebles_match.group(0)
            return self._parse_inmuebles24_url(url, message)
        
        return None
    
    def _parse_inmuebles24_url(self, url: str, full_message: str) -> Dict:
        """Парсит URL от Inmuebles24"""
        info = {
            'source': 'Inmuebles24',
            'url': url,
            'location': None,
            'area': None,
            'property_type': None
        }
        
        # Пытаемся извлечь информацию из URL
        # Пример: hermosa-casa-en-residencial-rio-cancun-146144201.html
        pattern = r'([^/]+)\.html$'
        match = re.search(pattern, url)
        if match:
            url_part = match.group(1)
            parts = url_part.split('-')
            
            # Ищем ключевые слова
            if 'cancun' in url_part.lower():
                info['location'] = 'Cancún'
            
            if 'residencial' in url_part.lower():
                # Извлекаем название жилого комплекса
                residencial_match = re.search(r'residencial[-\s](\w+)', url_part.lower())
                if residencial_match:
                    info['area'] = f"Residencial {residencial_match.group(1).title()}"
            
            # Определяем тип недвижимости
            if 'casa' in url_part.lower():
                info['property_type'] = 'casa'
            elif 'departamento' in url_part.lower():
                info['property_type'] = 'departamento'
            elif 'oficina' in url_part.lower():
                info['property_type'] = 'oficina'
        
        return info
    
    def _mentions_specific_address(self, message: str) -> bool:
        """Проверяет упоминание конкретных адресов"""
        address_keywords = [
            'calle', 'avenida', 'av.', 'boulevard', 'fraccionamiento',
            'colonia', 'col.', 'residencial', 'plaza', 'centro'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in address_keywords)
    
    def generate_smart_query(self, original_message: str, extracted_info: Dict) -> str:
        """Генерирует умный запрос для RAG на основе извлечённой информации"""
        
        location = extracted_info.get('location')
        area = extracted_info.get('area')
        prop_type = extracted_info.get('property_type')
        
        # Формируем запрос в зависимости от доступной информации
        query_parts = []
        
        if prop_type:
            if prop_type == 'casa':
                query_parts.append("casas")
            elif prop_type == 'departamento':
                query_parts.append("departamentos")
            else:
                query_parts.append(prop_type)
        else:
            query_parts.append("propiedades")
        
        if area:
            query_parts.append(f"en {area}")
        elif location:
            query_parts.append(f"en {location}")
        
        # Добавляем фразу для поиска альтернатив
        query = f"¿Qué {' '.join(query_parts)} similares tenemos disponibles? Busco opciones en la misma zona o zonas parecidas."
        
        return query
    
    def format_consultant_response(self, rag_response: str, extracted_info: Dict) -> str:
        """Форматирует ответ в консультативном стиле"""
        
        source = extracted_info.get('source', 'la plataforma externa')
        location = extracted_info.get('location', 'esa zona')
        prop_type = extracted_info.get('property_type', 'propiedad')
        
        # Начинаем с признания запроса
        intro = f"¡Hola! Vi que te interesa una {prop_type} de {source}. "
        
        # Предлагаем альтернативы
        if location:
            middle = f"Aunque no tengo acceso directo a esa publicación, tenemos excelentes opciones en {location} y zonas similares. "
        else:
            middle = "Aunque no tengo acceso directo a esa publicación, tenemos excelentes opciones similares. "
        
        # Добавляем информацию из RAG
        rag_info = f"\n\n{rag_response}"
        
        # Призыв к действию
        call_to_action = "\n\n¿Te gustaría que te ayude a encontrar algo similar o tienes algún presupuesto y preferencias específicas en mente?"
        
        return intro + middle + rag_info + call_to_action

# Singleton instance
smart_router = SmartRouter() 