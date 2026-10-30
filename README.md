# Каталог товаров

Администратор отправляет боту фото с названием в подписи. Файл сохраняется в MinIO, запись в PostgreSQL. Страница Next.js показывает каталог в браузере и в Telegram Mini App.

Сервисы `api`, `bot` и `web` не хранят состояние на диске процесса. Несколько реплик делят PostgreSQL и MinIO. Бот принимает обновления вебхуком, Nginx распределяет их по репликам.

Образ MinIO - `bitnamilegacy/minio`: официальные `minio/minio` сняты с Docker Hub. API и консоль те же.

## Запуск

```bash
cp .env.example .env
```

Заполните в `.env` `BOT_TOKEN` и `ADMIN_IDS`. Для приёма сообщений ботом и кнопки Mini App укажите публичный HTTPS:

- `WEBAPP_URL` - адрес каталога, который открывает Telegram
- `PUBLIC_BASE_URL` - тот же origin, на него ставится вебхук `{PUBLIC_BASE_URL}/telegram/webhook`

```bash
docker compose up -d --build
```

Каталог в браузере: http://localhost

Консоль MinIO только с этой машины: http://127.0.0.1:9001

Несколько инстансов:

```bash
docker compose up -d --build --scale api=2 --scale bot=2 --scale web=2
```

Пока `PUBLIC_BASE_URL` пустой, сообщения забирает одна реплика бота. Остальные ждут и подхватывают опрос, если она остановится. С публичным HTTPS бот принимает вебхук, и Nginx раздаёт его по всем репликам.

## Создание товара

В боте администратор нажимает «Создать товар» или отправляет `/create`, затем одним сообщением присылает фотографию и название в подписи.

Тот же контракт, что использует бот:

```bash
curl -s -X POST http://localhost/api/products \
  -H "X-Bot-Token: $BOT_SECRET" \
  -F "name=Кружка" \
  -F "file=@photo.jpg;type=image/jpeg"
```

Подходят JPEG, PNG и WebP, до 10 МБ.
