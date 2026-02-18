#!/bin/bash
# Скрипт для настройки автоматического запуска на Linux/Mac сервере

echo "🔧 Настройка cron для автоматического запуска отчетов"

# Определяем путь к проекту
PROJECT_DIR=$(dirname "$(readlink -f "$0")")
PYTHON_BIN=$(which python3)

echo "📂 Путь к проекту: $PROJECT_DIR"
echo "🐍 Python: $PYTHON_BIN"

# Создаем временный файл для cron
CRON_FILE="/tmp/speech_analysis_cron"

# Записываем правила cron
cat > $CRON_FILE << EOF
# Отчёт за первую половину месяца (1-15) - запуск 15-го числа в 9:00
0 9 15 * * cd $PROJECT_DIR && $PYTHON_BIN reporter.py --first-half >> $PROJECT_DIR/logs/cron.log 2>&1

# Отчёт за вторую половину месяца (16-конец) - запуск в последний день месяца в 9:00
# Трик: проверяем, что завтра будет 1-е число (т.е. сегодня последний день месяца)
0 9 28-31 * * [ \$(date -d tomorrow +\%d) -eq 1 ] && cd $PROJECT_DIR && $PYTHON_BIN reporter.py --second-half >> $PROJECT_DIR/logs/cron.log 2>&1
EOF

echo ""
echo "📄 Содержимое cron правил:"
cat $CRON_FILE

echo ""
read -p "❓ Добавить эти правила в crontab? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]
then
    # Добавляем в crontab
    crontab -l > /tmp/current_cron 2>/dev/null || true
    cat $CRON_FILE >> /tmp/current_cron
    crontab /tmp/current_cron
    
    echo "✅ Cron правила добавлены!"
    echo ""
    echo "📋 Текущий crontab:"
    crontab -l
else
    echo "❌ Отменено"
fi

# Очистка
rm -f $CRON_FILE /tmp/current_cron

echo ""
echo "💡 СОВЕТ: Для ручного тестирования запустите:"
echo "   python3 reporter.py --mock --first-half"
