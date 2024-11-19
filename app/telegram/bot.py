import sys

from aiogram import Bot, Dispatcher
from common.config import cfg

try:
    bot = Bot(token=cfg.TELEGRAM_TOKEN)
    dp = Dispatcher()
except Exception as e:
    cfg.logger.error(str(e))
    sys.exit(1)
