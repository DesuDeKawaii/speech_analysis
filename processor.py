import os
from pathlib import Path
from typing import Optional

from database import SessionLocal, Call
from config import Config
from logger import logger
from megafon import download_audio
from yandex_speech import speech_client
from yandex_gpt import gpt_client


def process_call(call: Call, use_mock: bool = False) -> bool:
    """Обрабатывает один звонок через весь пайплайн
    
    Шаги:
    1. Скачивает аудио из АТС (если есть ссылка в ai_data)
    2. Отправляет в SpeechSense для транскрибации и анализа эмоций
    3. Анализирует через YandexGPT
    4. Сохраняет результат в БД
    5. Удаляет временный аудио файл
    
    Args:
        call: Объект звонка из БД
        use_mock: Использовать моковые данные (для тестирования без API)
        
    Returns:
        bool: True если обработка успешна
    """
    session = SessionLocal()
    
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"🔄 Обрабатываем звонок #{call.id}")
        logger.info(f"   Оператор: {call.operator}")
        logger.info(f"   Дата: {call.date.strftime('%d.%m.%Y %H:%M')}")
        logger.info(f"   Длительность: {call.duration // 60}:{call.duration % 60:02d}")
        logger.info(f"{'='*60}")
        
        # Шаг 1: Получение аудио файла
        audio_path = None
        
        if use_mock:
            logger.info("🎭 РЕЖИМ ТЕСТИРОВАНИЯ: Используем mock данные")
            audio_path = "mock.mp3"  # Фейковый путь
        else:
            # Получаем ссылку на аудио из БД
            audio_url = call.audio_url
            
            if not audio_url:
                logger.error("❌ Нет ссылки на аудио файл в БД")
                return False
            
            # Скачиваем файл
            Config.TEMP_AUDIO_PATH.mkdir(exist_ok=True)
            audio_filename = f"call_{call.id}.mp3"
            audio_path = Config.TEMP_AUDIO_PATH / audio_filename
            
            if not download_audio(audio_url, str(audio_path)):
                logger.error("❌ Не удалось скачать аудио файл")
                return False
        
        # Шаг 2: Анализ через SpeechSense
        if use_mock:
            speech_result = speech_client.analyze_audio_mock(str(audio_path))
        else:
            speech_result = speech_client.analyze_audio(str(audio_path))
        
        if not speech_result:
            logger.error("❌ Не удалось проанализировать аудио через SpeechSense")
            if audio_path and audio_path != "mock.mp3":
                os.remove(audio_path)
            return False
        
        # Шаг 3: Анализ через YandexGPT
        transcript = speech_result.get("transcript", "")
        sentiment_data = {
            "operator": speech_result.get("sentiment", {}).get("operator", "neutral"),
            "client": speech_result.get("sentiment", {}).get("client", "neutral"),
            "statistics": speech_result.get("statistics", {})
        }
        
        gpt_result = gpt_client.analyze_call(transcript, sentiment_data)
        
        if not gpt_result:
            logger.error("❌ Не удалось проанализировать звонок через GPT")
            if audio_path and audio_path != "mock.mp3":
                os.remove(audio_path)
            return False
        
        # Шаг 4: Сохраняем результаты в БД
        call.ai_data = gpt_result
        call.status = "PROCESSED"
        
        session.add(call)
        session.commit()
        
        logger.info("✅ Звонок успешно обработан и сохранен в БД")
        
        # Шаг 5: Удаляем временный файл
        if audio_path and audio_path != "mock.mp3" and Path(audio_path).exists():
            os.remove(audio_path)
            logger.info("🗑️  Временный аудио файл удален")
        
        return True
        
    except Exception as e:
        logger.error(f"🔥 Критическая ошибка при обработке звонка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
    finally:
        session.close()


def process_calls_batch(calls: list[Call], use_mock: bool = False) -> dict:
    """Обрабатывает пакет звонков
    
    Args:
        calls: Список звонков для обработки
        use_mock: Использовать моковые данные
        
    Returns:
        dict: Статистика обработки
    """
    total = len(calls)
    successful = 0
    failed = 0
    
    logger.info(f"\n🚀 Начинаем обработку {total} звонков...")
    
    for i, call in enumerate(calls, 1):
        logger.info(f"\n📍 Прогресс: {i}/{total}")
        
        if process_call(call, use_mock=use_mock):
            successful += 1
        else:
            failed += 1
            # Помечаем как FAILED в БД
            session = SessionLocal()
            try:
                call.status = "FAILED"
                session.add(call)
                session.commit()
            finally:
                session.close()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 ИТОГИ ОБРАБОТКИ:")
    logger.info(f"   ✅ Успешно: {successful}")
    logger.info(f"   ❌ Ошибки: {failed}")
    logger.info(f"   📈 Успешность: {successful/total*100:.1f}%")
    logger.info(f"{'='*60}\n")
    
    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "success_rate": successful / total if total > 0 else 0
    }
