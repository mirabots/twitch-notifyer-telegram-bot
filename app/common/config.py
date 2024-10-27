import asyncio
import sys
from copy import copy
from time import sleep

import httpx
import requests
import yaml
from aiofile import async_open

from app.common.utils import (
    disable_unnecessary_loggers,
    generate_code,
    get_args,
    get_logging_config,
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

        self.logging_config = get_logging_config(
            levelDEBUG if self.ENV == "dev" else levelINFO
        )
        self.logger = self.logging_config.configure()()

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

        no_secrets = self.apply_secrets(get_db=True)
        if no_secrets:
            self.logger.error(f"No secrets found: {no_secrets}")
            sys.exit(1)
        self.logger.info("Secrets were loaded")
        self.lock = asyncio.Lock()

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

    def apply_secrets(self, get_db: bool) -> list[str]:
        no_secrets = []

        # database: need to get only at startup
        if get_db:
            db_data = self.secrets_data.get(f"{self.ENV}/db")
            try:
                self.DB_CONNECTION_STRING = db_data["connection string"]
            except Exception:
                no_secrets.append(f"{self.ENV}/db")

        # domain
        domain_data = self.secrets_data.get(f"{self.ENV}/domain")
        try:
            self.DOMAIN = domain_data["domain"]
        except Exception:
            no_secrets.append(f"{self.ENV}/domain")

        # twitch
        twitch_data = self.secrets_data.get(f"{self.ENV}/twitch")
        try:
            self.TWITCH_CLIENT_ID = twitch_data["client_id"]
            self.TWITCH_CLIENT_SECRET = twitch_data["client_secret"]
            self.TWITCH_SUBSCRIPTION_SECRET = twitch_data["subscription_secret"]
            self.TWITCH_BEARER = "NONE"
        except Exception:
            no_secrets.append(f"{self.ENV}/twitch")

        # telegram
        telegram_data = self.secrets_data.get(f"{self.ENV}/telegram")
        try:
            self.TELEGRAM_BOT_OWNER_ID = telegram_data["owner_id"]
            self.TELEGRAM_TOKEN = telegram_data["token"]
            self.TELEGRAM_SECRET = telegram_data["secret"]
            self.TELEGRAM_LIMIT_DEFAULT = int(telegram_data["limit_default"])
            self.TELEGRAM_INVITE_CODE = generate_code()
            self.TELEGRAM_USERS = []
        except Exception:
            no_secrets.append(f"{self.ENV}/telegram")

        return no_secrets

    async def check_invite_code(self, code) -> bool:
        async with self.lock:
            is_valid = False
            if self.TELEGRAM_INVITE_CODE == code:
                cfg.TELEGRAM_INVITE_CODE = generate_code()
                is_valid = True
            return is_valid

    async def update_limit_default(self, value: int) -> str:
        old_default_value = copy(self.TELEGRAM_LIMIT_DEFAULT)
        old_users_value = copy(self.TELEGRAM_USERS)

        self.TELEGRAM_LIMIT_DEFAULT = value
        self.secrets_data[f"{self.ENV}/telegram"]["limit_default"] = value
        for user in self.TELEGRAM_USERS:
            if self.TELEGRAM_USERS[user]["limit"] == old_default_value:
                self.TELEGRAM_USERS[user]["limit"] = value

        update_secrets_result = ""
        try:
            async with httpx.AsyncClient(
                base_url=self.SECRETS_DOMAIN,
                headers={self.SECRETS_HEADER: self.SECRETS_TOKEN},
            ) as ac:
                data = {"data": self.secrets_data[f"{self.ENV}/telegram"]}
                response = await ac.put(f"/api/secrets/{self.ENV}/telegram", json=data)
                if response.status_code != 200:
                    update_secrets_result = (
                        f"Error updating data in secrets - {response.status_code}"
                    )
        except Exception as e:
            update_secrets_result = f"Error updating data in secrets - {e}"

        if update_secrets_result:
            self.TELEGRAM_LIMIT_DEFAULT = old_default_value
            self.secrets_data[f"{self.ENV}/telegram"][
                "limit_default"
            ] = old_default_value
            self.TELEGRAM_USERS = old_users_value
        return update_secrets_result


cfg = ConfigManager()
