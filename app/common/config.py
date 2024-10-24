import sys
from copy import copy
from time import sleep

import httpx
import requests
import yaml
from aiofile import async_open

from app.common.utils import (
    disable_unnecessary_loggers,
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

        # owner
        bot_owner_data = self.secrets_data.get(f"{self.ENV}/owner")
        try:
            self.BOT_OWNER_LOGIN = bot_owner_data["login"]
            self.BOT_OWNER_ID = bot_owner_data["id"]
        except Exception:
            no_secrets.append(f"{self.ENV}/owner")

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
            self.TELEGRAM_TOKEN = telegram_data["token"]
            self.TELEGRAM_SECRET = telegram_data["secret"]
            self.TELEGRAM_ALLOWED = [user.lower() for user in telegram_data["allowed"]]
            self.TELEGRAM_LIMIT_DEFAULT = telegram_data["limit_default"]
            self.TELEGRAM_LIMITES = telegram_data["limites"]
        except Exception:
            no_secrets.append(f"{self.ENV}/telegram")

        return no_secrets

    async def update_telegram_secrets(self) -> str:
        try:
            async with httpx.AsyncClient(
                base_url=self.SECRETS_DOMAIN,
                headers={self.SECRETS_HEADER: self.SECRETS_TOKEN},
            ) as ac:
                data = {"data": self.secrets_data[f"{self.ENV}/telegram"]}
                response = await ac.put(f"/api/secrets/{self.ENV}/telegram", json=data)
                if response.status_code != 200:
                    return f"Error updating data in secrets - {response.status_code}"
                return ""
        except Exception as e:
            return f"Error updating data in secrets - {e}"

    async def update_telegram_allowed(self, user: str, action: str) -> str:
        old_value = copy(self.TELEGRAM_ALLOWED)
        try:
            if action == "add":
                self.TELEGRAM_ALLOWED.append(user)
            elif action == "remove":
                self.TELEGRAM_ALLOWED.remove(user)
            self.secrets_data[f"{self.ENV}/telegram"]["allowed"] = self.TELEGRAM_ALLOWED
        except Exception as e:
            return f"Error updating local secrets data - {e}"

        update_result = await self.update_telegram_secrets()
        if update_result:
            self.TELEGRAM_ALLOWED = old_value
            self.secrets_data[f"{self.ENV}/telegram"]["allowed"] = old_value
        return update_result

    async def update_telegram_limit_default(self, value: int) -> str:
        old_default_value = copy(self.TELEGRAM_LIMIT_DEFAULT)
        old_limites_value = copy(self.TELEGRAM_LIMITES)
        self.TELEGRAM_LIMIT_DEFAULT = value
        self.secrets_data[f"{self.ENV}/telegram"]["limit_default"] = value
        for user in self.TELEGRAM_LIMITES:
            if self.TELEGRAM_LIMITES[user] == value:
                del self.TELEGRAM_LIMITES[user]
        self.secrets_data[f"{self.ENV}/telegram"]["limites"] = self.TELEGRAM_LIMITES

        update_result = await self.update_telegram_secrets()
        if update_result:
            self.TELEGRAM_LIMIT_DEFAULT = old_default_value
            self.secrets_data[f"{self.ENV}/telegram"][
                "limit_default"
            ] = old_default_value
            self.TELEGRAM_LIMITES = old_limites_value
            self.secrets_data[f"{self.ENV}/telegram"]["limites"] = old_limites_value
        return update_result

    async def update_telegram_user_limit(self, user_name: str, value: int | str) -> str:
        old_value = copy(self.TELEGRAM_LIMITES)

        if value == self.TELEGRAM_LIMIT_DEFAULT:
            if user_name in self.TELEGRAM_LIMITES:
                del self.TELEGRAM_LIMITES[user_name]
                self.secrets_data[f"{self.ENV}/telegram"][
                    "limites"
                ] = self.TELEGRAM_LIMITES
        else:
            self.TELEGRAM_LIMITES[user_name] = value
            self.secrets_data[f"{self.ENV}/telegram"]["limites"] = self.TELEGRAM_LIMITES

        update_result = await self.update_telegram_secrets()
        if update_result:
            self.TELEGRAM_LIMITES = old_value
            self.secrets_data[f"{self.ENV}/telegram"]["limites"] = old_value
        return update_result


cfg = ConfigManager()
