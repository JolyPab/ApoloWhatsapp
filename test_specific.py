#!/usr/bin/env python3
"""
Специальный тест для сценария Inmuebles24 → WhatsApp Bot
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_inmuebles24_scenario():
    """Тестируем реальный сценарий с Inmuebles24"""
    print("🏠 ТЕСТИРОВАНИЕ СЦЕНАРИЯ INMUEBLES24")
    print("=" * 60)
    
    # Реальное сообщение от клиента
    incoming_message = """¡Hola! Quiero que se comuniquen conmigo por este inmueble en Inmuebles24 https://www.inmuebles24.com/propiedades/clasificado/veclcapa-hermosa-casa-en-residencial-rio-cancun-146144201.html"""
    
    print(f"📱 Входящее сообщение:")
    print(f"   {incoming_message}")
    print()
    
    try:
        # Тестируем детекцию лида
        from core.lead_detector import lead_detector
        
        print("🎯 ДЕТЕКЦИЯ ЛИДА:")
        lead_result = lead_detector.analyze_message(incoming_message)
        print(f"   Это лид? {lead_result.get('is_lead', False)}")
        print(f"   Тип интереса: {lead_result.get('interest', 'none')}")
        print(f"   Упомянутые объекты: {lead_result.get('property_mentions', [])}")
        print()
        
        # Тестируем ответ RAG системы
        from core.llm_chain import llm_chain
        
        print("🤖 ОТВЕТ RAG СИСТЕМЫ:")
        rag_response = llm_chain.invoke_chain(incoming_message, [])
        print(f"   Ответ: {rag_response}")
        print()
        
        # Анализируем проблемы
        print("⚠️  ВЫЯВЛЕННЫЕ ПРОБЛЕМЫ:")
        
        # Проблема 1: Данные не совпадают
        if "inmuebles24.com" in incoming_message.lower():
            print("   ❌ Клиент спрашивает об объекте с Inmuebles24")
            print("   ❌ У нас данные только с century21apolo.com")
            print("   ❌ RAG система не знает этот объект")
        
        # Проблема 2: Нет связи между объявлениями
        print("   ❌ Нет маппинга между Inmuebles24 и нашей базой")
        print("   ❌ Бот не понимает, какой объект из нашей базы соответствует запросу")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

def suggest_solutions():
    """Предлагаем решения проблем"""
    print("\n💡 ПРЕДЛАГАЕМЫЕ РЕШЕНИЯ:")
    print("=" * 60)
    
    print("🔧 РЕШЕНИЕ 1: Умная обработка внешних ссылок")
    print("   • Извлекать адрес/район из ссылки Inmuebles24")
    print("   • Искать похожие объекты в базе Century 21 Apolo")
    print("   • Предлагать альтернативы: 'У нас есть похожие дома в том же районе'")
    print()
    
    print("🔧 РЕШЕНИЕ 2: Синхронизация данных")
    print("   • Скрапить данные с Inmuebles24 (где размещается Century 21)")
    print("   • Создать маппинг ID объектов между платформами")
    print("   • Обновлять FAISS индексы обеими источниками")
    print()
    
    print("🔧 РЕШЕНИЕ 3: Умный роутинг")
    print("   • Если объект НЕ из нашей базы → переключить на 'консультант режим'")
    print("   • Предложить консультацию: 'Давайте найдем что-то подходящее!'")
    print("   • Собрать требования: бюджет, район, тип недвижимости")
    print()
    
    print("🔧 РЕШЕНИЕ 4: Улучшенная детекция")
    print("   • Анализировать URL для извлечения деталей объекта")
    print("   • Определять район/тип недвижимости из ссылки")
    print("   • Использовать эту информацию для поиска в RAG")

def test_improved_logic():
    """Тестируем улучшенную логику обработки"""
    print("\n🧠 ТЕСТ УЛУЧШЕННОЙ ЛОГИКИ:")
    print("=" * 60)
    
    # Симулируем улучшенную обработку
    incoming_message = """¡Hola! Quiero que se comuniquen conmigo por este inmueble en Inmuebles24 https://www.inmuebles24.com/propiedades/clasificado/veclcapa-hermosa-casa-en-residencial-rio-cancun-146144201.html"""
    
    # Извлекаем информацию из URL
    if "residencial-rio-cancun" in incoming_message:
        extracted_info = {
            "location": "Cancún",
            "area": "Residencial Río",
            "property_type": "casa",
            "source": "inmuebles24"
        }
        
        print(f"📍 Извлеченная информация:")
        for key, value in extracted_info.items():
            print(f"   {key}: {value}")
        
        # Формируем умный запрос к RAG
        smart_query = f"Какие дома есть в {extracted_info['area']} или похожих районах Канкуна?"
        print(f"\n🔍 Умный запрос к RAG: {smart_query}")
        
        try:
            from core.llm_chain import llm_chain
            response = llm_chain.invoke_chain(smart_query, [])
            print(f"💬 Ответ: {response[:200]}...")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")

def main():
    """Главная функция тестирования"""
    test_inmuebles24_scenario()
    suggest_solutions()
    test_improved_logic()
    
    print("\n🎯 ВЫВОДЫ:")
    print("   1. Текущая система НЕ готова к реальным сценариям")
    print("   2. Нужна умная обработка внешних ссылок")
    print("   3. Требуется синхронизация данных между платформами")
    print("   4. Детекция лидов работает, но нужен контекстный анализ")

if __name__ == "__main__":
    main() 