FROM python:3.11

WORKDIR /app

# Устанавливаем все необходимые системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем библиотеки (используем готовые бинарники где возможно)
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir --only-binary=:all: aiogram asyncpg aiohttp pydantic pydantic-core || pip install --no-cache-dir aiogram asyncpg aiohttp pydantic pydantic-core

# Копируем весь код
COPY . .

# Запускаем бота
CMD ["sh", "-c", "if [ -f bot.py ]; then python bot.py; else python src/bot.py; fi"]
