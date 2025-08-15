"""
Утилиты для извлечения данных о недвижимости из ответов RAG
"""
import re
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class PropertyExtractor:
    """Извлекает информацию о недвижимости из текстов и JSON данных"""
    
    def __init__(self, property_data_file: str = "apolo_all_listings_parsed.json"):
        """Инициализирует экстрактор с данными о недвижимости"""
        try:
            with open(property_data_file, 'r', encoding='utf-8') as f:
                self.properties_data = json.load(f)
            logger.info(f"Loaded {len(self.properties_data)} properties from {property_data_file}")
        except Exception as e:
            logger.error(f"Failed to load property data: {e}")
            self.properties_data = []
    
    def extract_property_info_from_response(self, rag_response: str) -> List[Dict]:
        """
        Извлекает информацию о недвижимости из ответа RAG.
        Ищет упоминания конкретных объектов недвижимости.
        """
        properties_mentioned = []
        
        # Ищем различные паттерны упоминания недвижимости
        patterns = [
            r'(Casa|Departamento|Oficina|Propiedad).*?en\s+([^,\.]+)',  # "Casa en La Florida"
            r'ubicada?\s+en\s+([^,\.]+)',  # "ubicada en Naucalpan"
            r'(\$\s*[\d,]+)',  # Цены
            r'(\d+)\s*(m2|metros)',  # Площади
            r'(\d+)\s*(recámaras?|habitaciones?)',  # Комнаты
        ]
        
        for prop in self.properties_data:
            # Проверяем совпадения по названию, адресу, району
            title_words = self._extract_key_words(prop.get('title', ''))
            address_words = self._extract_key_words(prop.get('address', ''))
            
            response_lower = rag_response.lower()
            
            # Ищем совпадения ключевых слов
            matches = 0
            for word in title_words + address_words:
                if len(word) > 3 and word in response_lower:  # Игнорируем короткие слова
                    matches += 1
            
            # Если найдено достаточно совпадений, добавляем объект
            if matches >= 2:
                properties_mentioned.append({
                    'title': prop.get('title'),
                    'price': prop.get('price'),
                    'address': prop.get('address'),
                    'photos': prop.get('photos', [])[:4],  # Максимум 4 фото
                    'agent_name': prop.get('agent_name'),
                    'agent_phone': prop.get('agent_phone'),
                    'url': prop.get('url'),
                    'features': prop.get('features'),
                    'match_score': matches
                })
        
        # Сортируем по релевантности и возвращаем топ-3
        properties_mentioned.sort(key=lambda x: x['match_score'], reverse=True)
        return properties_mentioned[:3]
    
    def _extract_key_words(self, text: str) -> List[str]:
        """Извлекает ключевые слова из текста"""
        if not text:
            return []
        
        # Убираем стоп-слова и извлекаем значимые слова
        stop_words = {'en', 'de', 'la', 'el', 'y', 'o', 'con', 'por', 'para', 'un', 'una', 'del', 'las', 'los'}
        words = re.findall(r'\b\w{3,}\b', text.lower())
        return [word for word in words if word not in stop_words]
    
    def find_property_by_criteria(self, location: str = None, property_type: str = None, 
                                max_price: str = None) -> List[Dict]:
        """
        Ищет недвижимость по конкретным критериям
        """
        results = []
        
        for prop in self.properties_data:
            match = True
            
            if location:
                location_lower = location.lower()
                title_lower = prop.get('title', '').lower()
                address_lower = prop.get('address', '').lower()
                if location_lower not in title_lower and location_lower not in address_lower:
                    match = False
            
            if property_type:
                prop_type_lower = property_type.lower()
                title_lower = prop.get('title', '').lower()
                if prop_type_lower not in title_lower:
                    match = False
            
            if match:
                results.append({
                    'title': prop.get('title'),
                    'price': prop.get('price'),
                    'address': prop.get('address'),
                    'photos': prop.get('photos', [])[:4],
                    'agent_name': prop.get('agent_name'),
                    'agent_phone': prop.get('agent_phone'),
                    'url': prop.get('url'),
                    'features': prop.get('features')
                })
        
        return results[:5]  # Возвращаем топ-5 результатов

# Singleton instance
property_extractor = PropertyExtractor()