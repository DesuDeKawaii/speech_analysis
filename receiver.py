import os
from fastapi import FastAPI, Form, Request
from database import SessionLocal, Call
from datetime import datetime
import uvicorn

app = FastAPI()

@app.post("/")
async def handle_megafon_webhook(request: Request):
    form_data = await request.form()
    data = dict(form_data)
    
    callid = data.get("callid")
    status = data.get("status")
    link = data.get("link")
    cmd = data.get("cmd")
    user = data.get("user", "Неизвестный")
    phone = data.get("phone")
    duration = data.get("duration", 0)

    # Ловим только успешные звонки с записью
    if cmd == "history" and status == "Success" and link:
        session = SessionLocal()
        try:
            exists = session.query(Call).filter(Call.id == callid).first()
            if not exists:
                new_call = Call(
                    id=callid,
                    date=datetime.now(),
                    operator=user,
                    phone=phone, # <-- Исправлено: теперь поле называется 'phone'
                    duration=int(duration),
                    status="NEW",
                    ai_data={"audio_url": link}
                )
                session.add(new_call)
                session.commit()
                print(f"✅ УСПЕХ: Звонок {callid} сохранен в базу.")
            else:
                print(f"⚠️ Пропуск: Звонок {callid} уже в базе.")
        except Exception as e:
            print(f"❌ Ошибка записи: {e}")
        finally:
            session.close()
    
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)