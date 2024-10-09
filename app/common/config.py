import sys
from time import sleep

import httpx
import requests
import yaml
from aiofile import async_open

from app.common.utils import (
    disable_unnecessary_loggers,
    get_args,
    get_logger,
    levelDEBUG,
    levelINFO,
)


class ConfigManager:
    def __init__(self) -> None:
        self._config_file = "config/config.yaml"
        self.BOT_ACTIVE = True

        self.secrets_data = {}
        args = get_args()
        self.ENV = args.env

        if self.ENV != "dev":
            disable_unnecessary_loggers()

        self.logger = get_logger(levelDEBUG if self.ENV == "dev" else levelINFO)

        self.load_creds_sync()
        error = self.get_creds()
        if error:
            self.logger.error(error)
            sys.exit(1)
        self.logger.info("Creds from config were loaded")

        error = self.load_secrets_sync()
        if error:
            self.logger.error(error)
            self.logger.error("waiting 120 secs for secrets storage")
            sleep(120)
        error = self.load_secrets_sync()
        if error:
            self.logger.error(error)
            sys.exit(1)

        no_secrets = self.check_secrets(get_db=True)
        if no_secrets:
            self.logger.error(f"No secrets found: {no_secrets}")
            sys.exit(1)
        self.apply_secrets(get_db=True)
        self.logger.info("Secrets were loaded")

    def load_creds_sync(self) -> None:
        with open(self._config_file, "r") as f:
            self.creds_data = yaml.safe_load(f.read())

    async def load_creds_async(self) -> None:
        async with async_open(self._config_file, "r") as f:
            self.creds_data = yaml.safe_load(await f.read())

    def get_creds(self) -> str:
        try:
            self.SECRETS_DOMAIN = self.creds_data["secrets_domain"] or ""
            self.SECRETS_HEADER = self.creds_data["secrets_header"] or ""
            self.SECRETS_TOKEN = self.creds_data["secrets_token"] or ""
        except Exception:
            return "Error getting secrets creds from config-file"
        return ""

    async def update_creds(self, updated_creds: dict) -> None:
        self.creds_data.update(updated_creds)

        self.SECRETS_DOMAIN = self.data["secrets_domain"]
        self.SECRETS_HEADER = self.data["secrets_header"]
        self.SECRETS_TOKEN = self.data["secrets_token"]

        async with async_open(self._config_file, "w") as f:
            yaml.dump(self.creds_data, f)

    def load_secrets_sync(self) -> str:
        try:
            response = requests.get(
                f"{self.SECRETS_DOMAIN}/api/secrets",
                headers={self.SECRETS_HEADER: self.SECRETS_TOKEN},
            )
            if response.status_code != 200:
                return (
                    f"Error getting data from secrets response - {response.status_code}"
                )
        except Exception as e:
            return f"Error getting data from secrets - {e}"

        try:
            self.secrets_data = response.json()["content"]
            return ""
        except Exception:
            return "Error getting secrets from response"

    async def load_secrets_async(self) -> str:
        try:
            async with httpx.AsyncClient(
                base_url=self.SECRETS_DOMAIN,
                headers={self.SECRETS_HEADER: self.SECRETS_TOKEN},
            ) as ac:
                response = await ac.get("/api/secrets")
                if response.status_code != 200:
                    return f"Error getting data from secrets response - {response.status_code}"
        except Exception as e:
            return f"Error getting data from secrets - {e}"

        try:
            self.secrets_data = response.json()["content"]
            return ""
        except Exception:
            return "Error getting secrets from response"

    def check_secrets(self, get_db: bool) -> list[str]:
        no_secrets = []

        # database: need to get only at startup
        if get_db:
            db_data = self.secrets_data.get(f"{self.ENV}/db")
            try:
                db_data["connection string"]
            except Exception:
                no_secrets.append(f"{self.ENV}/db")

        # owner
        owner_data = self.secrets_data.get(f"{self.ENV}/owner")
        try:
            owner_data["login"]
            owner_data["id"]
        except Exception:
            no_secrets.append(f"{self.ENV}/owner")

        # domain
        domain_data = self.secrets_data.get(f"{self.ENV}/domain")
        try:
            domain_data["domain"]
        except Exception:
            no_secrets.append(f"{self.ENV}/domain")

        # twitch
        twitch_data = self.secrets_data.get(f"{self.ENV}/twitch")
        try:
            twitch_data["client_id"]
            twitch_data["client_secret"]
            twitch_data["subscription_secret"]
        except Exception:
            no_secrets.append(f"{self.ENV}/twitch")

        # telegram
        telegram_data = self.secrets_data.get(f"{self.ENV}/telegram")
        try:
            telegram_data["token"]
            telegram_data["secret"]
            ALLOWED = telegram_data["allowed"]
            if not isinstance(ALLOWED, list):
                raise
        except Exception:
            no_secrets.append(f"{self.ENV}/telegram")

        return no_secrets

    def apply_secrets(self, get_db: bool) -> None:
        # database: need to get only at startup
        if get_db:
            db_data = self.secrets_data.get(f"{self.ENV}/db")
            self.DB_CONNECTION_STRING = db_data["connection string"]

        # owner
        owner_data = self.secrets_data.get(f"{self.ENV}/owner")
        self.OWNER_LOGIN = owner_data["login"]
        self.OWNER_ID = owner_data["id"]

        # domain
        domain_data = self.secrets_data.get(f"{self.ENV}/domain")
        self.DOMAIN = domain_data["domain"]

        # twitch
        twitch_data = self.secrets_data.get(f"{self.ENV}/twitch")
        self.TWITCH_CLIENT_ID = twitch_data["client_id"]
        self.TWITCH_CLIENT_SECRET = twitch_data["client_secret"]
        self.TWITCH_SUBSCRIPTION_SECRET = twitch_data["subscription_secret"]
        self.TWITCH_BEARER = "NONE"

        # telegram
        telegram_data = self.secrets_data.get(f"{self.ENV}/telegram")
        self.TELEGRAM_TOKEN = telegram_data["token"]
        self.TELEGRAM_SECRET = telegram_data["secret"]
        self.TELEGRAM_ALLOWED = telegram_data["allowed"]


cfg = ConfigManager()
