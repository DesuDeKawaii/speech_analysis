import logging
import sys
from pathlib import Path
from datetime import datetime

# Создаем папку для логов
LOG_DIR = Path("./logs")
LOG_DIR.mkdir(exist_ok=True)

# Формат лога
LOG_FORMAT = "[%(asctime)s] %(levelname)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger(name: str = "speech_analysis") -> logging.Logger:
    """Настраивает логгер для приложения
    
    Args:
        name: Имя логгера
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Избегаем дублирования handlers
    if logger.handlers:
        return logger
    
    # Handler для файла (с датой в имени)
    log_file = LOG_DIR / f"processing_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    # Handler для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Глобальный логгер
logger = setup_logger()
