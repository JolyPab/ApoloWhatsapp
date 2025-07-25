#!/usr/bin/env python3
"""
Тестовый скрипт для проверки RAG системы Century 21 Apolo Bot
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def test_config():
    """Проверяем, что все необходимые переменные настроены"""
    print("🔧 Проверка конфигурации...")
    
    required_vars = [
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_API_KEY', 
        'AZURE_EMBEDDINGS_ENDPOINT',
        'AZURE_EMBEDDINGS_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print(f"✅ {var}: настроено")
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные: {missing_vars}")
        return False
    
    return True

def test_faiss_index():
    """Проверяем, что FAISS индексы доступны"""
    print("\n📚 Проверка FAISS индексов...")
    
    faiss_path = os.getenv('FAISS_INDEX_PATH', 'apolo_faiss')
    
    if not os.path.exists(faiss_path):
        print(f"❌ Папка FAISS не найдена: {faiss_path}")
        return False
    
    required_files = ['index.faiss', 'index.pkl']
    for file in required_files:
        file_path = os.path.join(faiss_path, file)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path) / (1024*1024)  # MB
            print(f"✅ {file}: {size:.1f} MB")
        else:
            print(f"❌ Файл не найден: {file}")
            return False
    
    return True

def test_llm_chain():
    """Тестируем LLM цепочку"""
    print("\n🤖 Тестирование LLM цепочки...")
    
    try:
        from core.llm_chain import llm_chain
        
        # Тестовый вопрос
        test_question = "Расскажи о недвижимости Century 21 Apolo"
        print(f"❓ Вопрос: {test_question}")
        
        # Пробуем получить ответ
        response = llm_chain.invoke_chain(test_question, [])
        print(f"💬 Ответ: {response[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка LLM цепочки: {e}")
        return False

def test_lead_detection():
    """Тестируем детекцию лидов"""
    print("\n🎯 Тестирование детекции лидов...")
    
    try:
        from core.lead_detector import lead_detector
        
        test_messages = [
            "Привет! Как дела?",
            "Хочу купить квартиру в Канкуне",
            "Можно посмотреть дом завтра?",
            "Сколько стоит аренда офиса?"
        ]
        
        for msg in test_messages:
            result = lead_detector.analyze_message(msg)
            is_lead = result.get('is_lead', False)
            interest = result.get('interest', 'none')
            print(f"📝 '{msg}' → Лид: {is_lead}, Интерес: {interest}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка детекции лидов: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование Century 21 Apolo Bot")
    print("=" * 50)
    
    # Последовательно тестируем компоненты
    tests = [
        ("Конфигурация", test_config),
        ("FAISS индексы", test_faiss_index),
        ("LLM цепочка", test_llm_chain),
        ("Детекция лидов", test_lead_detection)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Критическая ошибка в {test_name}: {e}")
            results.append((test_name, False))
    
    # Итоги
    print("\n" + "=" * 50)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nРезультат: {passed}/{len(results)} тестов пройдено")
    
    if passed == len(results):
        print("🎉 Все тесты пройдены! Бот готов к работе!")
    else:
        print("⚠️  Есть проблемы, требующие исправления.")

if __name__ == "__main__":
    main() 