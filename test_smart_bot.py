#!/usr/bin/env python3
"""
Тест улучшенного бота с умным роутингом
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_smart_routing():
    """Тестируем умный роутинг"""
    print("🧠 ТЕСТИРОВАНИЕ УМНОГО РОУТИНГА")
    print("=" * 60)
    
    from core.smart_router import smart_router
    
    test_messages = [
        {
            'message': '¡Hola! Quiero que se comuniquen conmigo por este inmueble en Inmuebles24 https://www.inmuebles24.com/propiedades/clasificado/veclcapa-hermosa-casa-en-residencial-rio-cancun-146144201.html',
            'expected_strategy': 'consultant'
        },
        {
            'message': 'Hola, busco una casa en renta en Cancún',
            'expected_strategy': 'direct'
        },
        {
            'message': 'Me interesa el departamento en Avenida Bonampak',
            'expected_strategy': 'hybrid'
        }
    ]
    
    for i, test in enumerate(test_messages, 1):
        print(f"\n📝 ТЕСТ {i}:")
        print(f"   Сообщение: {test['message'][:60]}...")
        
        analysis = smart_router.analyze_message(test['message'])
        
        print(f"   Стратегия: {analysis['strategy']}")
        print(f"   Ожидалась: {test['expected_strategy']}")
        print(f"   Причина: {analysis['routing_reason']}")
        
        if analysis['extracted_info']:
            print(f"   Извлечённая информация:")
            for key, value in analysis['extracted_info'].items():
                print(f"     {key}: {value}")
        
        # Проверяем правильность
        if analysis['strategy'] == test['expected_strategy']:
            print("   ✅ ПРОЙДЕН")
        else:
            print("   ❌ ПРОВАЛЕН")

def test_full_pipeline():
    """Тестируем полный пайплайн обработки сообщения"""
    print("\n🚀 ТЕСТИРОВАНИЕ ПОЛНОГО ПАЙПЛАЙНА")
    print("=" * 60)
    
    from core.logic import process_message
    from unittest.mock import patch
    
    # Мокаем отправку сообщений
    with patch('core.logic.twilio_client.send_whatsapp_message') as mock_send:
        with patch('core.logic.redis_client.is_duplicate', return_value=False):
            with patch('core.logic.redis_client.get_session_history', return_value=[]):
                with patch('core.logic.redis_client.save_session_history'):
                    
                    test_message = "¡Hola! Quiero que se comuniquen conmigo por este inmueble en Inmuebles24 https://www.inmuebles24.com/propiedades/clasificado/veclcapa-hermosa-casa-en-residencial-rio-cancun-146144201.html"
                    
                    print(f"📱 Обрабатываем сообщение:")
                    print(f"   {test_message[:60]}...")
                    
                    try:
                        process_message(
                            from_number="+525555555555",
                            message_body=test_message,
                            message_sid="test_sid_123"
                        )
                        
                        # Проверяем, что сообщение было отправлено
                        if mock_send.called:
                            sent_message = mock_send.call_args[0][1]  # Второй аргумент - текст сообщения
                            print(f"\n💬 Ответ бота:")
                            print(f"   {sent_message[:200]}...")
                            
                            # Проверяем ключевые элементы ответа
                            checks = [
                                ("Упоминание Inmuebles24", "inmuebles24" in sent_message.lower()),
                                ("Предложение альтернатив", any(word in sent_message.lower() for word in ["opciones", "similares", "tenemos"])),
                                ("Призыв к действию", "?" in sent_message),
                                ("Консультативный тон", any(word in sent_message.lower() for word in ["ayude", "encontrar", "presupuesto"]))
                            ]
                            
                            print(f"\n✅ ПРОВЕРКИ КАЧЕСТВА ОТВЕТА:")
                            for check_name, passed in checks:
                                status = "✅" if passed else "❌"
                                print(f"   {status} {check_name}")
                            
                            passed_checks = sum(1 for _, passed in checks if passed)
                            print(f"\n📊 Результат: {passed_checks}/{len(checks)} проверок пройдено")
                            
                            return passed_checks == len(checks)
                        else:
                            print("❌ Сообщение не было отправлено")
                            return False
                            
                    except Exception as e:
                        print(f"❌ Ошибка обработки: {e}")
                        return False

def test_comparison():
    """Сравниваем старый и новый подходы"""
    print("\n⚖️  СРАВНЕНИЕ ПОДХОДОВ")
    print("=" * 60)
    
    from core.llm_chain import llm_chain
    from core.smart_router import smart_router
    
    test_message = "¡Hola! Quiero que se comuniquen conmigo por este inmueble en Inmuebles24 https://www.inmuebles24.com/propiedades/clasificado/veclcapa-hermosa-casa-en-residencial-rio-cancun-146144201.html"
    
    print("📋 СТАРЫЙ ПОДХОД (прямой запрос к RAG):")
    try:
        old_response = llm_chain.invoke_chain(test_message, [])
        print(f"   {old_response[:150]}...")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print("\n🧠 НОВЫЙ ПОДХОД (умный роутинг):")
    try:
        analysis = smart_router.analyze_message(test_message)
        if analysis['strategy'] == 'consultant':
            extracted_info = analysis['extracted_info']
            smart_query = smart_router.generate_smart_query(test_message, extracted_info)
            rag_response = llm_chain.invoke_chain(smart_query, [])
            new_response = smart_router.format_consultant_response(rag_response, extracted_info)
            print(f"   {new_response[:150]}...")
        else:
            print("   Не активирован консультативный режим")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

def main():
    """Главная функция тестирования"""
    test_smart_routing()
    test_comparison()
    success = test_full_pipeline()
    
    print("\n🎯 ИТОГОВЫЕ ВЫВОДЫ:")
    print("=" * 60)
    if success:
        print("✅ Умный роутинг работает!")
        print("✅ Бот теперь правильно обрабатывает внешние ссылки")
        print("✅ Консультативный режим активируется")
        print("✅ Качество ответов улучшено")
    else:
        print("❌ Есть проблемы в работе умного роутинга")
    
    print("\n🚀 СЛЕДУЮЩИЕ ШАГИ:")
    print("   1. Протестировать с реальными Twilio кредами")
    print("   2. Добавить больше паттернов для других сайтов")
    print("   3. Улучшить извлечение информации из URL")
    print("   4. Настроить A/B тестирование ответов")

if __name__ == "__main__":
    main() 