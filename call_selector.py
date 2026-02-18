from datetime import datetime
from typing import List
from sqlalchemy import and_

from database import SessionLocal, Call
from config import Config
from logger import logger


def select_balanced_calls(
    start_date: datetime,
    end_date: datetime,
    target_minutes: int = None
) -> List[Call]:
    """Выбирает звонки с равномерным распределением между операторами
    
    Алгоритм:
    1. Получить все звонки за период со статусом NEW
    2. Сгруппировать по операторам
    3. Рассчитать целевые минуты на оператора
    4. Для каждого оператора набрать звонки пока не достигнем цели
    
    Args:
        start_date: Начало периода
        end_date: Конец периода
        target_minutes: Целевое количество минут (по умолчанию из конфига)
        
    Returns:
        List[Call]: Список выбранных звонков
    """
    if target_minutes is None:
        target_minutes = Config.ANALYSIS_MINUTES_TARGET
    
    session = SessionLocal()
    
    try:
        # Получаем все звонки за период со статусом NEW
        all_calls = session.query(Call).filter(
            and_(
                Call.date >= start_date,
                Call.date <= end_date,
                Call.status == "NEW"
            )
        ).order_by(Call.date).all()
        
        if not all_calls:
            logger.warning(f"⚠️ Нет звонков за период {start_date.date()} - {end_date.date()}")
            return []
        
        # Группируем по операторам
        operators_calls = {}
        for call in all_calls:
            if call.operator not in operators_calls:
                operators_calls[call.operator] = []
            operators_calls[call.operator].append(call)
        
        logger.info(f"📊 Найдено операторов: {len(operators_calls)}")
        logger.info(f"🎯 Цель: {target_minutes} минут ({target_minutes // 60}ч {target_minutes % 60}м)")
        
        # Рассчитываем целевые минуты на оператора
        operators_count = len(operators_calls)
        target_per_operator = target_minutes / operators_count
        
        logger.info(f"📈 Целевые минуты на оператора: ~{target_per_operator:.0f} мин")
        
        # Выбираем звонки для каждого оператора
        selected_calls = []
        total_minutes = 0
        
        for operator, calls in operators_calls.items():
            operator_minutes = 0
            operator_selected = []
            
            # Сортируем по дате
            calls_sorted = sorted(calls, key=lambda c: c.date)
            
            # Набираем звонки пока не достигнем цели
            for call in calls_sorted:
                if operator_minutes >= target_per_operator:
                    break
                
                operator_selected.append(call)
                operator_minutes += call.duration / 60  # переводим секунды в минуты
            
            selected_calls.extend(operator_selected)
            total_minutes += operator_minutes
            
            logger.info(
                f"  ✅ {operator}: {len(operator_selected)} звонков, "
                f"{operator_minutes:.1f} минут"
            )
        
        logger.info(f"🎉 ИТОГО: {len(selected_calls)} звонков, {total_minutes:.1f} минут")
        
        # Если набрали меньше цели - предупреждаем
        if total_minutes < target_minutes * 0.9:  # допуск 10%
            logger.warning(
                f"⚠️ ВНИМАНИЕ: Набрали только {total_minutes:.0f} минут из {target_minutes}. "
                f"Возможно, недостаточно звонков за период."
            )
        
        return selected_calls
        
    finally:
        session.close()


def get_period_dates(period_type: str = "auto") -> tuple[datetime, datetime]:
    """Определяет даты периода для анализа
    
    Args:
        period_type: "first_half" (1-15), "second_half" (16-конец), или "auto" (определить по текущей дате)
        
    Returns:
        tuple: (start_date, end_date)
    """
    now = datetime.now()
    year = now.year
    month = now.month
    
    if period_type == "auto":
        # Определяем автоматически
        if now.day <= 15:
            period_type = "first_half"
        else:
            period_type = "second_half"
    
    if period_type == "first_half":
        # 1-15 число текущего месяца
        start_date = datetime(year, month, 1, 0, 0, 0)
        end_date = datetime(year, month, 15, 23, 59, 59)
    else:
        # 16 - конец месяца
        start_date = datetime(year, month, 16, 0, 0, 0)
        
        # Определяем последний день месяца
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        
        from datetime import timedelta
        last_day = (next_month - timedelta(days=1)).day
        end_date = datetime(year, month, last_day, 23, 59, 59)
    
    logger.info(f"📅 Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}")
    return start_date, end_date
