import requests
import json
import time
from typing import Dict, Optional
from pathlib import Path

from config import Config
from logger import logger


class YandexGPTClient:
    """Клиент для работы с Yandex Foundation Models (YandexGPT)"""
    
    def __init__(self):
        self.api_url = Config.YANDEX_GPT_API_URL
        self.api_key = Config.YANDEX_API_KEY
        self.folder_id = Config.YANDEX_FOLDER_ID
        self.model = Config.YANDEX_GPT_MODEL
        
    def _make_request(self, messages: list, temperature: float = 0.3) -> Optional[str]:
        """Отправляет запрос в YandexGPT API
        
        Args:
            messages: Список сообщений [{"role": "user", "text": "..."}]
            temperature: Температура генерации (0-1)
            
        Returns:
            str: Ответ модели или None при ошибке
        """
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "modelUri": f"gpt://{self.folder_id}/{self.model}",
            "completionOptions": {
                "temperature": temperature,
                "maxTokens": 2000
            },
            "messages": messages
        }
        
        for attempt in range(Config.RETRY_ATTEMPTS):
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["result"]["alternatives"][0]["message"]["text"]
                elif response.status_code == 429:
                    # Rate limit, ждем и повторяем
                    logger.warning(f"Rate limit exceeded, waiting 5 seconds...")
                    time.sleep(5)
                    continue
                else:
                    logger.error(f"YandexGPT API error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Request to YandexGPT failed (attempt {attempt + 1}): {e}")
                if attempt < Config.RETRY_ATTEMPTS - 1:
                    time.sleep(2)
                    
        return None
    
    def analyze_call(self, transcript: str, sentiment_data: dict) -> Optional[Dict]:
        """Анализирует звонок на основе транскрипта и данных о тоне
        
        Args:
            transcript: Текст диалога
            sentiment_data: Данные о тоне из SpeechSense
            
        Returns:
            dict: Структурированный анализ звонка
        """
        # Формируем промпт
        operator_sentiment = sentiment_data.get("operator", "unknown")
        client_sentiment = sentiment_data.get("client", "unknown")
        interruptions = sentiment_data.get("statistics", {}).get("interruptions", 0)
        
        prompt = f"""Ты - эксперт по контролю качества (ОКК) в Маммологическом центре L7.
Твоя задача - проанализировать транскрипт звонка и оценить работу оператора по СТРОГОМУ чек-листу.

ТРАНСКРИПТ ЗВОНКА:
{transcript}

ДАННЫЕ АНАЛИЗА ЭМОЦИЙ (SpeechSense):
- Тон оператора: {operator_sentiment}
- Тон клиента: {client_sentiment}
- Перебиваний: {interruptions}

КРИТЕРИИ ОЦЕНКИ (Максимум 10 баллов за каждый блок, кроме бонусов):

1. ПРИВЕТСТВИЕ (0-10 баллов)
   - Назвал "Маммологический центр L7"?
   - Представился по имени?
   - Вежливое приветствие (Доброе утро/день/вечер)?
   - Спросил "Чем могу вам помочь?"

2. ВЫЯВЛЕНИЕ ПОТРЕБНОСТИ (0-10 баллов)
   - Задал уточняющие вопросы (минимум 3 вопроса)?
   - Выслушал клиента, не перебивал?
   - Уточнил детали (возраст, день цикла и т.д.)?

3. ПРЕЗЕНТАЦИЯ (0-10 баллов)
   - Обозначил конкурентные преимущества (L7 - лидер, опыт врачей, оборудование)?
   - Рассказал про услугу/врача подробно?
   - Предложил 2 слота времени на выбор (активное предложение)?
   - Озвучил стоимость (четко, "сумма рублей", "входит то-то")?
   - Предложил доп. услуги (если уместно)?

4. ОТРАБОТКА ВОЗРАЖЕНИЙ (0-10 баллов)
   - Если были возражения ("дорого", "подумаю") - отработал ли их по скрипту (аргументы про качество, оборудование)?
   - Если возражений НЕ БЫЛО - ставь 10.
   - Если оператор сдался без борьбы - ставь 0-3.

5. ЗАВЕРШЕНИЕ ДИАЛОГА (0-10 баллов)
   - Резюмировал договоренности (дата, время, врач, адрес)?
   - Спросил "Остались ли вопросы?"
   - Спросил "Откуда вы о нас узнали?" (Маркетинговый вопрос - ВАЖНО)
   - Попрощался по имени ("Всего доброго, [Имя]")?

6. БОНУСНЫЕ БАЛЛЫ (0-5 баллов)
   - Инициатива в диалоге (оператор вел разговор)?
   - Речь сотрудника внятная, разборчивая?
   - Тон приятный, бодрый, доброжелательный?

ФОРМАТ ОТВЕТА (JSON):
{{
  "greeting": оценка (0-10),
  "greeting_comment": "что сделано/не сделано",
  "needs": оценка (0-10),
  "needs_comment": "сколько вопросов задано, уточнил ли детали",
  "presentation": оценка (0-10),
  "presentation_comment": "были ли преимущества, вилка времени, цена",
  "objection": оценка (0-10),
  "objection_comment": "насколько уверенно отработал или 'возражений не было'",
  "closing": оценка (0-10),
  "closing_comment": "резюме, источник рекламы, прощание",
  "bonus": оценка (0-5),
  "bonus_comment": "общее впечатление",
  "summary": "Краткое резюме звонка (сильные/слабые стороны)",
  "recommendation": "Одна главная рекомендация для оператора (на что обратить внимание)"
}}"""

        messages = [
            {"role": "system", "text": "Ты строгий, но справедливый контролер качества. Отвечай только в JSON."},
            {"role": "user", "text": prompt}
        ]
        
        logger.info("Отправляем запрос в YandexGPT для анализа звонка...")
        response_text = self._make_request(messages, temperature=0.1)
        
        if not response_text:
            logger.error("Не удалось получить ответ от YandexGPT")
            return None
            
        # Парсим JSON из ответа
        try:
            # Убираем markdown разметку если есть
            clean_text = response_text.strip()
            if "```" in clean_text:
                clean_text = clean_text.split("```")[1]
                if clean_text.strip().startswith("json"):
                    clean_text = clean_text.strip()[4:]
            
            result = json.loads(clean_text.strip())
            
            # Рассчитываем итоговый балл (среднее по 5 основным категориям * 2 + бонус) -> шкала 0-100
            # 5 категорий по 10 баллов = 50 макс. Умножаем на 2 = 100.
            # Но у нас есть бонус. Давайте сделаем простую сумму: ((сумма 5 категорий) / 50) * 100 + бонус (доп баллы)
            # Или просто сумма баллов.
            # В старом коде было: (g+n+p+o)/4.
            # Тут сделаем: (sum(5 main categories) / 50) * 10. То есть средний балл 0-10.
            
            total_main = result['greeting'] + result['needs'] + result['presentation'] + result['objection'] + result['closing']
            avg_score = (total_main / 50) * 10
            
            # Добавим бонус к оценке, но не выше 10
            avg_score = min(10.0, avg_score + (result.get('bonus', 0) * 0.2)) # Бонус 5 баллов может дать +1 к общей оценке
            
            logger.info(f"✅ Звонок проанализирован. Оценка: {avg_score:.1f}/10")
            
            # Сохраняем совместимость с полями, которые ожидает reporter.py/excel
            # В Excel ожидаются: greeting, needs, presentation, objection...
            # Плюс summary и recommendation.
            # Мы добавили новые поля в JSON, но старые ключи тоже есть.
            
            return result

            
        except json.JSONDecodeError as e:
            logger.error(f"Не удалось распарсить JSON ответ от GPT: {e}")
            logger.error(f"Ответ был: {response_text[:500]}")
            return None
    
    def generate_operator_summary(self, recommendations: list[str], operator_name: str) -> str:
        """Генерирует общую рекомендацию оператору на основе всех звонков за период
        
        Args:
            recommendations: Список рекомендаций по каждому звонку
            operator_name: Имя оператора
            
        Returns:
            str: Обобщенная рекомендация
        """
        if not recommendations:
            return "Недостаточно данных для анализа"
        
        prompt = f"""Ты - HR специалист медицинской клиники. Перед тобой список рекомендаций для оператора {operator_name} по {len(recommendations)} звонкам за последние 2 недели.

РЕКОМЕНДАЦИИ ПО ЗВОНКАМ:
{chr(10).join(f"{i+1}. {rec}" for i, rec in enumerate(recommendations))}

ЗАДАЧА:
Обобщи эти рекомендации в один связный абзац (3-5 предложений) для итогового отчета. 

Выдели:
- Основные сильные стороны оператора
- Главные зоны роста (что повторяется чаще всего)
- Конкретные действия для улучшения

Пиши профессионально, но дружелюбно. Без JSON, просто текст."""

        messages = [
            {"role": "user", "text": prompt}
        ]
        
        logger.info(f"Генерируем итоговую рекомендацию для {operator_name}...")
        response = self._make_request(messages, temperature=0.5)
        
        return response or "Не удалось сгенерировать рекомендацию"


# Singleton instance
gpt_client = YandexGPTClient()
