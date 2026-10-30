import asyncio
import io
import logging
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import asyncpg
import httpx
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()
INVITE = "У меня есть товар"
ASK_PHOTO = "Отправьте одним сообщением фотографию и название товара в подписи."
ASK_CAPTION = "Добавьте название в подпись к фото и отправьте одним сообщением."
CREATED = "Товар создан."
FAILED = "Не удалось сохранить товар."


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in settings.admin_ids


def catalog_markup(user_id: int | None) -> InlineKeyboardMarkup | None:
    rows: list[list[InlineKeyboardButton]] = []
    if settings.webapp_url.startswith("https://"):
        rows.append(
            [InlineKeyboardButton(text="Открыть каталог", web_app=WebAppInfo(url=settings.webapp_url))]
        )
    if is_admin(user_id):
        rows.append([InlineKeyboardButton(text="Создать товар", callback_data="create_product")])
    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_invite(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if user_id is not None:
        logger.info("message from user_id=%s", user_id)
    markup = catalog_markup(user_id)
    if markup is None:
        await message.answer(INVITE)
        return
    await message.answer(INVITE, reply_markup=markup)


@router.message(Command("create"))
@router.message(F.text == "Создать товар")
async def ask_for_product(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if not is_admin(user_id):
        await send_invite(message)
        return
    await message.answer(ASK_PHOTO)


@router.callback_query(F.data == "create_product")
async def ask_for_product_callback(query: CallbackQuery) -> None:
    if not is_admin(query.from_user.id):
        await query.answer()
        return
    if isinstance(query.message, Message):
        await query.message.answer(ASK_PHOTO)
    await query.answer()


@router.message(F.photo)
async def save_product(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id if message.from_user else None
    if not is_admin(user_id):
        await send_invite(message)
        return
    caption = (message.caption or "").strip()
    if not caption:
        await message.answer(ASK_CAPTION)
        return
    if message.photo is None:
        await message.answer(ASK_PHOTO)
        return

    buffer = io.BytesIO()
    await bot.download(message.photo[-1], destination=buffer)
    payload = buffer.getvalue()
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.api_url}/products",
                data={"name": caption},
                files={"file": ("photo.jpg", payload, "image/jpeg")},
                headers={"X-Bot-Token": settings.bot_secret},
            )
    except httpx.HTTPError:
        logger.exception("catalog api is unreachable")
        await message.answer(FAILED)
        return
    if response.status_code != 201:
        logger.error("catalog api returned %s: %s", response.status_code, response.text)
        await message.answer(FAILED)
        return
    await message.answer(CREATED)


@router.message(CommandStart())
@router.message()
async def invite(message: Message) -> None:
    await send_invite(message)


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "instance": socket.gethostname()})


def run_health_only() -> None:
    app = web.Application()
    app.router.add_get("/health", health)
    web.run_app(app, host="::", port=8080)


def start_health_server() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.split("?", 1)[0] != "/health":
                self.send_response(404)
                self.end_headers()
                return
            body = f'{{"status":"ok","instance":"{socket.gethostname()}"}}'.encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    class DualStackServer(ThreadingHTTPServer):
        address_family = socket.AF_INET6

        def server_bind(self) -> None:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            super().server_bind()

    server = DualStackServer(("::", 8080), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


async def on_startup(bot: Bot) -> None:
    try:
        await bot.set_my_commands([BotCommand(command="start", description="Открыть каталог")])
        admin_commands = [
            BotCommand(command="start", description="Открыть каталог"),
            BotCommand(command="create", description="Создать товар"),
        ]
        for admin_id in settings.admin_ids:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
    except Exception:
        logger.exception("failed to configure bot commands")
    if not settings.public_base_url:
        logger.info("PUBLIC_BASE_URL is empty, webhook is not registered")
        return
    webhook_url = f"{settings.public_base_url}/telegram/webhook"
    try:
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.bot_secret,
            drop_pending_updates=True,
        )
    except Exception:
        logger.exception("failed to set webhook")
        return
    logger.info("webhook set to %s", webhook_url)


POLL_LOCK = 742021


async def run_single_poller(bot: Bot, dispatcher: Dispatcher) -> None:
    if not settings.database_url:
        logger.warning("DATABASE_URL is empty, polling without a leader lock")
        await dispatcher.start_polling(bot)
        return

    connection: asyncpg.Connection | None = None
    while connection is None:
        try:
            connection = await asyncpg.connect(settings.database_url)
        except Exception:
            logger.exception("postgres lock connection failed")
            await asyncio.sleep(2)
    announced = False
    try:
        while True:
            locked = await connection.fetchval("SELECT pg_try_advisory_lock($1)", POLL_LOCK)
            if locked:
                logger.info("this instance polls for updates")
                await dispatcher.start_polling(bot)
                return
            if not announced:
                logger.info("another instance is polling, waiting")
                announced = True
            await asyncio.sleep(5)
    finally:
        await connection.close()


def main() -> None:
    if not settings.bot_token or not settings.bot_secret:
        logger.warning("BOT_TOKEN or BOT_SECRET is empty, serving health only")
        run_health_only()
        return
    try:
        bot = Bot(token=settings.bot_token)
    except Exception:
        logger.exception("bot token rejected, serving health only")
        run_health_only()
        return

    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    dispatcher.startup.register(on_startup)

    if not settings.public_base_url:
        start_health_server()
        logger.info("PUBLIC_BASE_URL is empty, receiving updates by polling")
        asyncio.run(run_single_poller(bot, dispatcher))
        return

    app = web.Application()
    app.router.add_get("/health", health)
    SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=settings.bot_secret,
    ).register(app, path="/webhook")
    setup_application(app, dispatcher, bot=bot)
    web.run_app(app, host="::", port=8080)


if __name__ == "__main__":
    main()
