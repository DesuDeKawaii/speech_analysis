import requests
import os
from datetime import datetime, timedelta
from database import SessionLocal, Call
from dotenv import load_dotenv

load_dotenv()

# ВАЖНО: В .env должно быть MEGAFON_HOST=https://mamolog.megapbx.ru/crmapi/v1
HOST = os.getenv("MEGAFON_HOST", "").rstrip('/')
KEY = os.getenv("MEGAFON_KEY", "")

def sync_calls_from_megafon(days_back=7):
    print(f"📡 Стучусь в API, используя формат с вебхука...")
    
    session = SessionLocal()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # ПАРАМЕТРЫ ИЗ СКРИНШОТА (image_891d63.png)
    # Используем 'crm_token' вместо 'token'
    payload = {
        "cmd": "history",
        "crm_token": KEY, 
        "start": start_date.strftime("%Y%m%dT%H%M%SZ"),
        "end": end_date.strftime("%Y%m%dT%H%M%SZ"),
        "limit": 100
    }
    
    # Маскируемся под Go-http-client или Chrome
    headers = {
        "User-Agent": "Go-http-client/1.1",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        # Шлем как обычную форму (data=), НЕ как JSON
        resp = requests.post(HOST, data=payload, headers=headers, timeout=15)
        
        print(f"Статус ответа: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"⛔ Ошибка: {resp.text[:200]}")
            return

        # Пробуем распарсить JSON (обычно в ответ на 'history' они его шлют)
        try:
            data = resp.json()
        except:
            print("❌ ОШИБКА: Сервер ответил не JSON. Текст ответа:")
            print(resp.text[:300])
            return

        calls = data if isinstance(data, list) else data.get("calls", [])
        
        if not calls:
            print("📭 Список звонков пуст.")
            return

        print(f"📥 Найдено {len(calls)} записей. Сохраняю...")
        
        added_count = 0
        for item in calls:
            call_id = item.get("callid") or item.get("uid")
            if not call_id: continue
            
            if session.query(Call).filter(Call.id == str(call_id)).first():
                continue
                
            new_call = Call(
                id=str(call_id),
                date=datetime.now(), 
                operator=item.get("user", "Оператор"),
                phone=item.get("phone"),
                duration=int(item.get("duration", 0)),
                audio_url=item.get("link"),  # Ссылка на аудио
                status="NEW",
                ai_data={}
            )
            session.add(new_call)
            added_count += 1

        session.commit()
        print(f"✅ УСПЕХ! Добавлено {added_count} звонков.")

    except Exception as e:
        print(f"🔥 Ошибка: {e}")
    finally:
        session.close()

def download_audio(audio_url: str, save_path: str) -> bool:
    """Скачивает аудио файл из АТС Мегафон по ссылке
    
    Args:
        audio_url: URL для скачивания аудио
        save_path: Путь куда сохранить файл
        
    Returns:
        bool: True если успешно скачано
    """
    print(f"📥 Скачиваем аудио: {audio_url}")
    
    try:
        # Headers для авторизации (если нужна)
        headers = {
            "User-Agent": "Go-http-client/1.1"
        }
        
        # Если URL содержит токен, используем его
        # Иначе добавляем ключ как параметр
        if "token" not in audio_url.lower() and KEY:
            params = {"token": KEY}
        else:
            params = {}
        
        response = requests.get(
            audio_url, 
            headers=headers,
            params=params,
            timeout=60,
            stream=True
        )
        
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✅ Файл сохранен: {save_path}")
            return True
        else:
            print(f"❌ Ошибка скачивания: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"🔥 Ошибка при скачивании аудио: {e}")
        return False

if __name__ == "__main__":
    sync_calls_from_megafon()