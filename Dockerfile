# Используем легкую версию Python 3.10
FROM python:3.10-slim

# Устанавливаем рабочую папку внутри контейнера
WORKDIR /app

# Запрещаем Python создавать лишние файлы кэша и заставляем выводить логи сразу
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Сначала копируем файл зависимостей и устанавливаем их
# (Это ускоряет повторную сборку)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код бота
COPY . .

# Запускаем бота (убедись, что твой файл с кодом называется main.py)
CMD ["python", "main.py"]
