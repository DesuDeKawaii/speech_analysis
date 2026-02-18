#!/usr/bin/env python3
"""
Скрипт для тестирования системы анализа звонков

Проверяет:
1. Конфигурацию (.env файл)
2. Подключение к базе данных
3. API Yandex Cloud (опционально)
4. Генерацию mock отчета
"""

import sys
from pathlib import Path

print("="*70)
print("🧪 ТЕСТИРОВАНИЕ СИСТЕМЫ АНАЛИЗА ЗВОНКОВ")
print("="*70)
print()

# Тест 1: Импорты
print("📦 Тест 1: Проверка установленных пакетов...")
try:
    import pandas
    import openpyxl
    import sqlalchemy
    import requests
    from dotenv import load_dotenv
    print("   ✅ Все пакеты установлены")
except ImportError as e:
    print(f"   ❌ Отсутствует пакет: {e}")
    print("   Выполните: pip install -r requirements.txt")
    sys.exit(1)

print()

# Тест 2: Конфигурация
print("🔧 Тест 2: Проверка конфигурации...")
try:
    from config import Config
    Config.validate()
    print("   ✅ Конфигурация корректна")
    print(f"   • Megafon Host: {Config.MEGAFON_HOST}")
    print(f"   • Yandex Folder: {Config.YANDEX_FOLDER_ID}")
    print(f"   • GPT Model: {Config.YANDEX_GPT_MODEL}")
except ValueError as e:
    print(f"   ⚠️ Ошибка конфигурации: {e}")
    print("   Создайте файл .env на основе .env.example")
    print()
    
    # Проверяем наличие .env
    if not Path(".env").exists():
        print("   💡 Подсказка:")
        print("      cp .env.example .env")
        print("      nano .env  # и заполните значения")

print()

# Тест 3: База данных
print("💾 Тест 3: Проверка базы данных...")
try:
    from database import init_db, SessionLocal, Call
    init_db()
    
    session = SessionLocal()
    count = session.query(Call).count()
    session.close()
    
    print(f"   ✅ БД работает. Звонков в базе: {count}")
except Exception as e:
    print(f"   ❌ Ошибка БД: {e}")
    sys.exit(1)

print()

# Тест 4: Логирование
print("📝 Тест 4: Проверка логирования...")
try:
    from logger import logger
    logger.info("Тестовое сообщение")
    
    if Path("logs").exists():
        print("   ✅ Логирование работает")
        print(f"   • Папка логов: {Path('logs').absolute()}")
    else:
        print("   ⚠️ Папка logs не создана")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

print()

# Тест 5: Yandex Cloud API (опционально)
print("☁️  Тест 5: Проверка Yandex Cloud API...")
print("   (Этот тест отправляет реальный запрос в Yandex Cloud)")
test_api = input("   Протестировать API? (y/n): ").lower() == 'y'

if test_api:
    try:
        from yandex_gpt import gpt_client
        
        print("   📡 Отправляем тестовый запрос в YandexGPT...")
        result = gpt_client._make_request([
            {"role": "user", "text": "Привет! Ответь одним словом: работает ли API?"}
        ])
        
        if result:
            print(f"   ✅ YandexGPT работает! Ответ: {result[:50]}...")
        else:
            print("   ❌ Не удалось получить ответ от API")
    except Exception as e:
        print(f"   ❌ Ошибка API: {e}")
else:
    print("   ⏭️  Пропущено")

print()

# Тест 6: Mock генерация отчета
print("📊 Тест 6: Генерация тестового отчета...")
test_report = input("   Сгенерировать mock отчет? (y/n): ").lower() == 'y'

if test_report:
    try:
        from main import create_mock_data, generate_excel
        
        print("   🎲 Создаем тестовые данные...")
        create_mock_data()
        
        print("   📄 Генерируем Excel отчет...")
        report_path = generate_excel()
        
        if report_path and Path(report_path).exists():
            print(f"   ✅ Отчет создан: {report_path}")
        else:
            print("   ❌ Не удалось создать отчет")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
else:
    print("   ⏭️  Пропущено")

print()
print("="*70)
print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
print("="*70)
print()
print("💡 Следующие шаги:")
print("   1. Если все тесты прошли - запустите: python reporter.py --mock")
print("   2. Для полного теста с реальными API: python reporter.py --first-half")
print("   3. Настройте cron для автоматического запуска: ./setup_cron.sh")
print()
