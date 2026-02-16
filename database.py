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
    date = Column(DateTime)
    operator = Column(String)
    phone = Column(String)
    duration = Column(Integer)
    status = Column(String)
    ai_data = Column(JSON)

# Правильный способ создания таблиц
Base.metadata.create_all(bind=engine)