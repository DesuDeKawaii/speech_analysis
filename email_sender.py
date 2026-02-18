import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from datetime import datetime

from config import Config
from logger import logger


def send_report(file_path: str, recipients: list[str] = None, period_text: str = None):
    """Отправляет Excel отчет на email
    
    Args:
        file_path: Путь к Excel файлу
        recipients: Список email адресов (по умолчанию из конфига)
        period_text: Текст периода для письма (например "01.02 - 15.02")
    """
    if not Path(file_path).exists():
        logger.error(f"❌ Файл не найден: {file_path}")
        return False
    
    if recipients is None:
        if not Config.EMAIL_TO:
            logger.warning("⚠️ Email получатель не настроен в .env")
            return False
        recipients = [Config.EMAIL_TO]
    
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        logger.warning("⚠️ SMTP учетные данные не настроены в .env")
        return False
    
    try:
        logger.info(f"📧 Отправляем отчет на: {', '.join(recipients)}")
        
        # Формируем письмо
        msg = MIMEMultipart()
        msg['From'] = Config.SMTP_USER
        msg['To'] = ", ".join(recipients)
        
        if period_text:
            msg['Subject'] = f"Отчет по звонкам за период {period_text}"
        else:
            msg['Subject'] = f"Отчет по звонкам от {datetime.now().strftime('%d.%m.%Y')}"
        
        # Текст письма
        body = f"""Добрый день!

Во вложении отчет по анализу звонков операторов.

Период: {period_text or 'последние 2 недели'}
Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}

С уважением,
Система автоматического анализа звонков
"""
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Прикрепляем Excel файл
        with open(file_path, 'rb') as f:
            attachment = MIMEApplication(f.read(), _subtype='xlsx')
            attachment.add_header(
                'Content-Disposition',
                'attachment',
                filename=Path(file_path).name
            )
            msg.attach(attachment)
        
        # Отправляем через SMTP
        with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ Отчет успешно отправлен!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки email: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
