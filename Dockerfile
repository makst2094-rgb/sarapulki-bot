FROM python:3.11-slim

# Устанавливаем системные зависимости для компиляции библиотек
RUN apt-get update && apt-get install -y gcc libffi-dev && rm -rf /var/lib/apt/lists/*

# Создаем рабочую папку
WORKDIR /app

# Копируем файл зависимостей первым (для ускорения сборки)
COPY requirements.txt .

# Обновляем pip и устанавливаем все библиотеки
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Копируем ВЕСЬ код из репозитория в контейнер
COPY . .

# Запускаем бота (пробуем найти bot.py в корне или в папке src)
CMD ["sh", "-c", "if [ -f bot.py ]; then python bot.py; else python src/bot.py; fi"]
