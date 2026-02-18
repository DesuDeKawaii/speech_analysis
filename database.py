from sqlalchemy import Column, String, Integer, DateTime, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Создаем движок БД
engine = create_engine("sqlite:///./calls.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Call(Base):
    __tablename__ = "calls"

    id = Column(String, primary_key=True, index=True)
    date = Column(DateTime, index=True)  # Индекс для быстрого поиска
    operator = Column(String, index=True)  # Индекс для группировки
    phone = Column(String)
    duration = Column(Integer)
    status = Column(String, index=True)  # NEW/PROCESSED/FAILED
    audio_url = Column(String)  # Ссылка на аудио в АТС
    ai_data = Column(JSON)  # Результаты анализа от GPT

def init_db():
    """Инициализирует базу данных и создает таблицы"""
    Base.metadata.create_all(bind=engine)
