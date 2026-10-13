FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости системы для компиляции
RUN apt-get update && apt-get install -y gcc libffi-dev && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt ПЕРВЫМ (для кэширования)
COPY requirements.txt .

# Устанавливаем Python-библиотеки
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь остальной код
COPY . .

# Запускаем бота
CMD ["python", "bot.py"]
