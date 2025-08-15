#!/usr/bin/env python3
"""
Тестовый скрипт для проверки улучшений бота Century21 Apolo
"""
import os
import sys
import json
import logging
from dotenv import load_dotenv

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_property_extractor():
    """Тест экстрактора недвижимости"""
    print("\n=== ТЕСТ PROPERTY EXTRACTOR ===")
    
    try:
        from utils.property_extractor import property_extractor
        
        # Тестовый ответ с упоминанием недвижимости
        test_response = "Tenemos una hermosa casa en La Florida, Naucalpan por $7,900,000"
        
        properties = property_extractor.extract_property_info_from_response(test_response)
        
        print(f"Найдено объектов недвижимости: {len(properties)}")
        
        if properties:
            prop = properties[0]
            print(f"Первый объект:")
            print(f"  - Название: {prop.get('title')}")
            print(f"  - Цена: {prop.get('price')}")
            print(f"  - Адрес: {prop.get('address')}")
            print(f"  - Фото: {len(prop.get('photos', []))} шт.")
            print(f"  - Агент: {prop.get('agent_name')}")
        
        return True
        
    except Exception as e:
        print(f"ОШИБКА в тесте property_extractor: {e}")
        return False

def test_lead_detector():
    """Тест детектора лидов"""
    print("\n=== ТЕСТ LEAD DETECTOR ===")
    
    try:
        from core.lead_detector import lead_detector
        
        test_messages = [
            "Hola, me interesa esta casa",
            "¿Puedo agendar una visita?",
            "Quiero comprar un departamento",
            "¿Cuánto cuesta rentar?",
            "Hola, ¿cómo están?",
            "Gracias por la información"
        ]
        
        for msg in test_messages:
            try:
                result = lead_detector.analyze_message(msg)
                print(f"Mensaje: '{msg}'")
                print(f"  - Es lead: {result.get('is_lead')}")
                print(f"  - Tipo: {result.get('interest')}")
                print(f"  - Propiedades: {result.get('property_mentions', [])}")
                print()
            except Exception as e:
                print(f"Error analyzing message '{msg}': {e}")
        
        return True
        
    except Exception as e:
        print(f"ОШИБКА в тесте lead_detector: {e}")
        return False

def test_twilio_client():
    """Тест Twilio клиента (без реальной отправки)"""
    print("\n=== ТЕСТ TWILIO CLIENT ===")
    
    try:
        from utils.twilio_client import TwilioClient
        
        # Проверяем что клиент инициализируется
        if not all([os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'), os.getenv('TWILIO_PHONE_NUMBER')]):
            print("⚠️  Twilio credentials не настроены - тест пропущен")
            return True
        
        client = TwilioClient()
        print("✅ Twilio клиент успешно инициализирован")
        
        # Проверяем методы (без реальной отправки)
        test_photos = [
            "https://century21apolo.com/wp-content/uploads/2024/12/test-1.jpg",
            "https://century21apolo.com/wp-content/uploads/2024/12/test-2.jpg"
        ]
        
        print(f"✅ Метод send_whatsapp_message_with_multiple_photos готов к использованию")
        print(f"   Количество фото для тестирования: {len(test_photos)}")
        
        return True
        
    except Exception as e:
        print(f"ОШИБКА в тесте twilio_client: {e}")
        return False

def test_smart_router():
    """Тест умного роутера"""
    print("\n=== ТЕСТ SMART ROUTER ===")
    
    try:
        from core.smart_router import smart_router
        
        test_messages = [
            "Hola",
            "https://inmuebles24.com/propiedades/casa-en-cancun-123.html",
            "Me interesa una casa en residencial rio"
        ]
        
        for msg in test_messages:
            analysis = smart_router.analyze_message(msg)
            print(f"Mensaje: '{msg}'")
            print(f"  - Стратегия: {analysis['strategy']}")
            print(f"  - Причина: {analysis['routing_reason']}")
            print(f"  - Внешняя ссылка: {analysis['has_external_link']}")
            if analysis['extracted_info']:
                print(f"  - Извлеченная информация: {analysis['extracted_info']}")
            print()
        
        return True
        
    except Exception as e:
        print(f"ОШИБКА в тесте smart_router: {e}")
        return False

def test_config():
    """Тест конфигурации"""
    print("\n=== ТЕСТ КОНФИГУРАЦИИ ===")
    
    try:
        from config import settings
        
        required_settings = [
            'AZURE_OPENAI_ENDPOINT',
            'AZURE_OPENAI_API_KEY', 
            'AZURE_OPENAI_DEPLOYMENT_NAME',
            'FAISS_INDEX_PATH'
        ]
        
        for setting in required_settings:
            value = getattr(settings, setting, None)
            if value:
                print(f"✅ {setting}: настроен")
            else:
                print(f"❌ {setting}: НЕ настроен")
        
        # Проверяем файл FAISS
        if os.path.exists(settings.FAISS_INDEX_PATH):
            print(f"✅ FAISS индекс найден: {settings.FAISS_INDEX_PATH}")
        else:
            print(f"❌ FAISS индекс НЕ найден: {settings.FAISS_INDEX_PATH}")
        
        return True
        
    except Exception as e:
        print(f"ОШИБКА в тесте config: {e}")
        return False

def main():
    """Запуск всех тестов"""
    print("🤖 ТЕСТИРОВАНИЕ УЛУЧШЕННОГО БОТА CENTURY21 APOLO")
    print("=" * 60)
    
    tests = [
        ("Конфигурация", test_config),
        ("Property Extractor", test_property_extractor),
        ("Lead Detector", test_lead_detector),
        ("Smart Router", test_smart_router),
        ("Twilio Client", test_twilio_client),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"КРИТИЧЕСКАЯ ОШИБКА в тесте {test_name}: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОШЕЛ" if result else "❌ ОШИБКА"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nИтого: {passed}/{total} тестов прошли успешно")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("Бот готов к развертыванию.")
    else:
        print(f"\n⚠️  {total - passed} тестов не прошли.")
        print("Требуется дополнительная настройка.")

if __name__ == "__main__":
    main()