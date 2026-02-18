import os
from dotenv import load_dotenv
from pathlib import Path

# Загружаем переменные из .env
load_dotenv()

class Config:
    """Централизованная конфигурация приложения"""
    
    # Megafon PBX
    MEGAFON_HOST = os.getenv("MEGAFON_HOST", "").rstrip('/')
    MEGAFON_KEY = os.getenv("MEGAFON_KEY")
    
    # Yandex Cloud
    YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
    YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
    YANDEX_GPT_MODEL = os.getenv("YANDEX_GPT_MODEL", "yandexgpt-lite")
    
    # Yandex API Endpoints
    YANDEX_GPT_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    SPEECHKIT_STT_URL = "https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize"
    SPEECHKIT_OPERATIONS_URL = "https://operation.api.cloud.yandex.net/operations"
    
    # Email
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.yandex.ru")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    EMAIL_TO = os.getenv("EMAIL_TO")
    
    # Настройки обработки
    ANALYSIS_MINUTES_TARGET = int(os.getenv("ANALYSIS_MINUTES_TARGET", "2000"))
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
    TEMP_AUDIO_PATH = Path(os.getenv("TEMP_AUDIO_PATH", "./temp_audio"))
    
    @classmethod
    def validate(cls):
        """Проверяет наличие обязательных переменных"""
        required = {
            "MEGAFON_HOST": cls.MEGAFON_HOST,
            "MEGAFON_KEY": cls.MEGAFON_KEY,
            "YANDEX_FOLDER_ID": cls.YANDEX_FOLDER_ID,
            "YANDEX_API_KEY": cls.YANDEX_API_KEY,
        }
        
        missing = [key for key, value in required.items() if not value]
        
        if missing:
            raise ValueError(
                f"❌ Отсутствуют обязательные переменные в .env: {', '.join(missing)}\n"
                f"Скопируйте .env.example в .env и заполните значения."
            )
        
        # Создаем папку для временных аудио файлов
        cls.TEMP_AUDIO_PATH.mkdir(exist_ok=True)
        
        return True

# Валидация при импорте (опционально, можно убрать для тестов)
# Config.validate()
