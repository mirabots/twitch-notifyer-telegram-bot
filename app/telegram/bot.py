import sys

from aiogram import Bot, Dispatcher

from app.common.config import cfg
from app.common.utils import get_logger, levelDEBUG, levelINFO

logger = get_logger(levelDEBUG if cfg.ENV == "dev" else levelINFO)

try:
    bot = Bot(token=cfg.TELEGRAM_TOKEN)
    dp = Dispatcher()
except Exception as e:
    logger.error(str(e))
    sys.exit(1)
