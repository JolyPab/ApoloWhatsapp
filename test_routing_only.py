#!/usr/bin/env python3
"""
Упрощённый тест умного роутинга без Twilio зависимостей
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_routing_logic():
    """Тестируем только логику роутинга"""
    print("🧠 ТЕСТИРОВАНИЕ УМНОГО РОУТИНГА")
    print("=" * 60)
    
    from core.smart_router import smart_router
    
    test_cases = [
        {
            'name': 'Inmuebles24 ссылка',
            'message': '¡Hola! Quiero que se comuniquen conmigo por este inmueble en Inmuebles24 https://www.inmuebles24.com/propiedades/clasificado/veclcapa-hermosa-casa-en-residencial-rio-cancun-146144201.html',
            'expected_strategy': 'consultant',
            'expected_info': ['Inmuebles24', 'Cancún', 'casa']
        },
        {
            'name': 'Обычный запрос',
            'message': 'Hola, busco una casa en renta en Cancún',
            'expected_strategy': 'direct',
            'expected_info': []
        },
        {
            'name': 'Конкретный адрес', 
            'message': 'Me interesa el departamento en Avenida Bonampak',
            'expected_strategy': 'hybrid',
            'expected_info': []
        },
        {
            'name': 'Другая внешняя ссылка',
            'message': 'Vi esta casa en MercadoLibre: https://mercadolibre.com.mx/casa-residencial-cancun',
            'expected_strategy': 'direct',  # Пока не поддерживаем
            'expected_info': []
        }
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        print(f"\n📝 ТЕСТ {i}: {test['name']}")
        print(f"   Сообщение: {test['message'][:50]}...")
        
        # Анализируем
        analysis = smart_router.analyze_message(test['message'])
        
        print(f"   Стратегия: {analysis['strategy']} (ожидалась: {test['expected_strategy']})")
        print(f"   Причина: {analysis['routing_reason']}")
        
        # Проверяем извлечённую информацию
        if analysis['extracted_info']:
            print(f"   Извлечено:")
            for key, value in analysis['extracted_info'].items():
                print(f"     {key}: {value}")
                
        # Проверяем правильность
        strategy_correct = analysis['strategy'] == test['expected_strategy']
        if strategy_correct:
            print("   ✅ СТРАТЕГИЯ ПРАВИЛЬНАЯ")
            passed += 1
        else:
            print("   ❌ СТРАТЕГИЯ НЕПРАВИЛЬНАЯ")
    
    print(f"\n📊 ИТОГ: {passed}/{len(test_cases)} тестов пройдено")
    return passed == len(test_cases)

def test_url_parsing():
    """Тестируем парсинг URL"""
    print("\n🔍 ТЕСТИРОВАНИЕ ПАРСИНГА URL")
    print("=" * 60)
    
    from core.smart_router import smart_router
    
    test_urls = [
        {
            'url': 'https://www.inmuebles24.com/propiedades/clasificado/veclcapa-hermosa-casa-en-residencial-rio-cancun-146144201.html',
            'expected': {
                'location': 'Cancún',
                'property_type': 'casa',
                'area': 'Residencial Rio'
            }
        },
        {
            'url': 'https://www.inmuebles24.com/propiedades/departamento-en-renta-zona-hotelera-cancun-123456.html',
            'expected': {
                'location': 'Cancún', 
                'property_type': 'departamento'
            }
        }
    ]
    
    for i, test in enumerate(test_urls, 1):
        print(f"\n🔗 URL ТЕСТ {i}:")
        print(f"   URL: {test['url']}")
        
        # Создаём тестовое сообщение
        test_message = f"Hola, me interesa esta propiedad: {test['url']}"
        analysis = smart_router.analyze_message(test_message)
        
        if analysis['extracted_info']:
            extracted = analysis['extracted_info']
            print(f"   Извлечено:")
            for key, value in extracted.items():
                if value:
                    print(f"     {key}: {value}")
            
            # Проверяем ожидаемые значения
            print(f"   Проверки:")
            for key, expected_value in test['expected'].items():
                actual_value = extracted.get(key)
                if actual_value and expected_value.lower() in actual_value.lower():
                    print(f"     ✅ {key}: найдено '{actual_value}'")
                else:
                    print(f"     ❌ {key}: ожидалось '{expected_value}', получено '{actual_value}'")
        else:
            print("   ❌ Информация не извлечена")

def test_smart_query_generation():
    """Тестируем генерацию умных запросов"""
    print("\n💡 ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ УМНЫХ ЗАПРОСОВ")
    print("=" * 60)
    
    from core.smart_router import smart_router
    
    test_data = [
        {
            'info': {'location': 'Cancún', 'property_type': 'casa', 'area': 'Residencial Rio'},
            'original': 'Quiero esta casa'
        },
        {
            'info': {'location': 'Cancún', 'property_type': 'departamento'},
            'original': 'Me interesa este departamento'
        },
        {
            'info': {'location': 'Playa del Carmen'},
            'original': 'Busco algo aquí'
        }
    ]
    
    for i, test in enumerate(test_data, 1):
        print(f"\n🎯 ЗАПРОС {i}:")
        print(f"   Оригинал: {test['original']}")
        print(f"   Информация: {test['info']}")
        
        smart_query = smart_router.generate_smart_query(test['original'], test['info'])
        print(f"   Умный запрос: {smart_query}")
        
        # Проверяем качество запроса
        query_lower = smart_query.lower()
        checks = [
            ("Упоминание типа", any(prop_type in query_lower for prop_type in ['casa', 'departamento', 'propiedad'])),
            ("Упоминание локации", any(loc in query_lower for loc in [test['info'].get('location', '').lower(), test['info'].get('area', '').lower()] if loc)),
            ("Поисковые слова", any(word in query_lower for word in ['similares', 'opciones', 'disponibles', 'tenemos']))
        ]
        
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"     {status} {check_name}")

def main():
    """Главная функция"""
    success1 = test_routing_logic()
    test_url_parsing()
    test_smart_query_generation()
    
    print("\n🎯 ОБЩИЕ ВЫВОДЫ:")
    print("=" * 60)
    
    if success1:
        print("✅ Основная логика роутинга работает")
    else:
        print("❌ Есть проблемы в логике роутинга")
    
    print("\n💡 ПРЕИМУЩЕСТВА НОВОГО ПОДХОДА:")
    print("   🎯 Распознаёт внешние ссылки")
    print("   🧠 Извлекает контекст из URL")
    print("   💬 Формирует персонализированные ответы") 
    print("   🔄 Переключает режимы обработки")
    print("   📈 Повышает конверсию лидов")

if __name__ == "__main__":
    main() 