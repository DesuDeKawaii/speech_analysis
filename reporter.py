#!/usr/bin/env python3
"""
Главный скрипт для автоматической генерации отчетов по звонкам

Запускается по расписанию (cron):
- 15-го числа каждого месяца (для периода 1-15)
- В конце месяца (для периода 16-30/31)

Алгоритм:
1. Определяет период анализа
2. Выбирает 2000 минут звонков (равномерно между операторами)
3. Обрабатывает через SpeechSense + YandexGPT
4. Генерирует Excel отчет
5. Отправляет на email
"""

import sys
import random
from datetime import datetime, timedelta

from database import init_db, SessionLocal, Call
from call_selector import select_balanced_calls, get_period_dates
from processor import process_calls_batch
from main import generate_excel
from email_sender import send_report
from logger import logger
from config import Config

OPERATORS = ["Смирнова Анна", "Кузнецова Елена", "Васильева Мария"]


def _create_mock_calls(start_date: datetime, end_date: datetime, count: int = 15):
    """Создаёт фейковые звонки в БД для mock-тестирования.
    
    Звонки создаются со статусом NEW в рамках указанного периода,
    чтобы call_selector мог их найти и передать в processor.
    """
    session = SessionLocal()
    
    # Проверяем, есть ли уже звонки NEW за период
    existing = session.query(Call).filter(
        Call.status == "NEW",
        Call.date >= start_date,
        Call.date <= end_date
    ).count()
    
    if existing > 0:
        logger.info(f"ℹ️ В БД уже есть {existing} звонков NEW за период. Пропускаем генерацию.")
        session.close()
        return
    
    logger.info(f"🎲 Генерируем {count} mock-звонков для периода {start_date.date()} - {end_date.date()}...")
    
    period_days = max(1, (end_date - start_date).days)
    
    for i in range(count):
        call_date = start_date + timedelta(
            days=random.randint(0, period_days - 1),
            hours=random.randint(8, 18),
            minutes=random.randint(0, 59)
        )
        
        call = Call(
            id=f"mock_{i}_{random.randint(10000, 99999)}",
            date=call_date,
            operator=random.choice(OPERATORS),
            phone=f"+7-999-{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10,99)}",
            duration=random.randint(90, 420),  # 1.5 - 7 минут
            audio_url="mock://audio.mp3",
            status="NEW",
            ai_data={}
        )
        session.add(call)
    
    session.commit()
    session.close()
    logger.info(f"✅ Создано {count} mock-звонков\n")


def main(use_mock: bool = False, period_type: str = "auto"):
    """Главная функция генерации отчета
    
    Args:
        use_mock: Использовать mock данные для тестирования
        period_type: "first_half", "second_half" или "auto"
    """
    logger.info("\n" + "="*70)
    logger.info("🚀 ЗАПУСК СИСТЕМЫ АНАЛИЗА ЗВОНКОВ")
    logger.info("="*70 + "\n")
    
    try:
        # Валидируем конфигурацию
        logger.info("🔧 Проверяем конфигурацию...")
        Config.validate()
        logger.info("✅ Конфигурация в порядке\n")
        
    except ValueError as e:
        logger.error(f"❌ {e}")
        return False
    
    # Инициализация БД
    logger.info("💾 Инициализация базы данных...")
    init_db()
    logger.info("✅ БД готова\n")
    
    # Определяем период
    start_date, end_date = get_period_dates(period_type)
    period_text = f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
    
    # В режиме mock — создаём фейковые звонки в БД для текущего периода
    if use_mock:
        _create_mock_calls(start_date, end_date)
    
    # Шаг 1: Выбор звонков
    logger.info("📋 ШАГ 1: Выбор звонков для анализа")
    logger.info("-" * 70)
    
    selected_calls = select_balanced_calls(start_date, end_date)
    
    if not selected_calls:
        logger.error("❌ Нет звонков для обработки. Завершение.")
        return False
    
    logger.info(f"✅ Выбрано {len(selected_calls)} звонков\n")
    
    # Шаг 2: Обработка звонков
    logger.info("🤖 ШАГ 2: Обработка через SpeechSense + YandexGPT")
    logger.info("-" * 70)
    
    stats = process_calls_batch(selected_calls, use_mock=use_mock)
    
    if stats['successful'] == 0:
        logger.error("❌ Ни один звонок не был обработан успешно. Завершение.")
        return False
    
    logger.info(f"✅ Обработано {stats['successful']} звонков\n")
    
    # Шаг 3: Генерация Excel
    logger.info("📊 ШАГ 3: Генерация Excel отчета")
    logger.info("-" * 70)
    
    excel_path = generate_excel()
    
    if not excel_path:
        logger.error("❌ Не удалось создать Excel отчет. Завершение.")
        return False
    
    logger.info(f"✅ Отчет создан: {excel_path}\n")
    
    # Шаг 4: Отправка на email
    logger.info("📧 ШАГ 4: Отправка отчета на email")
    logger.info("-" * 70)
    
    if Config.EMAIL_TO and Config.SMTP_USER:
        if send_report(excel_path, period_text=period_text):
            logger.info("✅ Отчет отправлен\n")
        else:
            logger.warning("⚠️ Отчет создан, но не отправлен (проверьте настройки SMTP)\n")
    else:
        logger.info("ℹ️ Email не настроен, пропускаем отправку\n")
    
    # Итоги
    logger.info("\n" + "="*70)
    logger.info("🎉 ПРОЦЕСС ЗАВЕРШЕН УСПЕШНО")
    logger.info("="*70)
    logger.info(f"📅 Период: {period_text}")
    logger.info(f"📞 Обработано звонков: {stats['successful']}/{stats['total']}")
    logger.info(f"📄 Файл отчета: {excel_path}")
    logger.info("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    # Парсим аргументы командной строки
    use_mock = "--mock" in sys.argv or "-m" in sys.argv
    
    period_type = "auto"
    if "--first-half" in sys.argv:
        period_type = "first_half"
    elif "--second-half" in sys.argv:
        period_type = "second_half"
    
    if use_mock:
        logger.info("🎭 РЕЖИМ ТЕСТИРОВАНИЯ: Используются mock данные\n")
    
    success = main(use_mock=use_mock, period_type=period_type)
    
    sys.exit(0 if success else 1)
