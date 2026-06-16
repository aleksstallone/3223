# 🎯 Minecraft Donate Bot

Telegram-бот для приёма донатов на Minecraft сервер через **ЮKassa** с автоматической выдачей прав через **RCON**. Поддерживает **PostgreSQL** и **SQLite**, готов к деплою на любом хостинге (Render, Heroku, Docker).

## ✨ Возможности
- Покупка доната с выбором товара и вводом ника
- Оплата через ЮKassa (тестовый режим)
- Автоматическая выдача прав через RCON
- История покупок для пользователя (с пагинацией)
- Админ-команда `/admin` для выполнения произвольных RCON-команд
- Вебхук для приёма уведомлений от ЮKassa
- Поддержка SQLite (по умолчанию) и PostgreSQL

## 🚀 Быстрый старт

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка `.env`

Скопируйте `.env.example` в `.env` и заполните все переменные:

- `BOT_TOKEN` – токен от @BotFather
- `SHOP_ID` и `SECRET_KEY` – из личного кабинета ЮKassa
- `RCON_HOST`, `RCON_PORT`, `RCON_PASSWORD` – данные вашего сервера
- `PRODUCTS` – список товаров в формате `Название|Цена|Команда{ник};...`
- `ADMIN_IDS` – Telegram ID администраторов (через запятую)
- `DATABASE_URL` – для PostgreSQL оставьте как есть или укажите свою

### 3. Запуск

```
python main.py
```

## ☁️ Деплой на хостинг

### Render

1. Создайте новый Web Service, укажите репозиторий.
1. В настройках укажите:

- Build Command: `pip install -r requirements.txt`
- Start Command: `python main.py`
1. Добавьте переменные окружения из `.env.example`.
1. Укажите публичный URL в `WEBHOOK_URL` (например, `https://ваш-домен/webhook`).

### Heroku

1. Установите Heroku CLI, создайте приложение.
1. Добавьте переменные окружения через `heroku config:set`.
1. Задеплойте ветку: `git push heroku main`.

### Docker

```
docker build -t donate-bot .
docker run -p 8080:8080 --env-file .env donate-bot
```

## 🔒 Важно

- Для работы вебхуков необходим публичный HTTPS-адрес (используйте ngrok для тестов).
- В тестовом режиме ЮKassa (`TEST_MODE=true`) используйте тестовые карты.

## 📜 Лицензия

MIT

