import httpx
import requests
import yaml
from aiofile import async_open


class ConfigManager:
    def __init__(self) -> None:
        self._config_file = "config/config.yaml"
        self.BOT_ACTIVE = True

    def load_creds(self, env: str) -> None:
        self.ENV = env
        with open(self._config_file, "r") as f:
            self.data = yaml.safe_load(f.read())
            try:
                self.SECRETS_DOMAIN = self.data["secrets_domain"]
                self.SECRETS_HEADER = self.data["secrets_header"]
                self.SECRETS_TOKEN = self.data["secrets_token"]
            except Exception:
                print("Error getting secrets creds from config-file")
                raise

    async def reload_creds(self) -> None:
        async with async_open(self._config_file, "r") as f:
            self.data = yaml.safe_load(await f.read())
            try:
                self.SECRETS_DOMAIN = self.data["secrets_domain"]
                self.SECRETS_HEADER = self.data["secrets_header"]
                self.SECRETS_TOKEN = self.data["secrets_token"]
            except Exception:
                print("Error getting secrets creds from config-file")
                raise

    # async def update_creds(self, updated_creds: UpdatedCreds) -> None:
    #     self.data.update(updated_creds.model_dump(exclude_none=True))

    #     self.SECRETS_DOMAIN = self.data["secrets_domain"]
    #     self.SECRETS_HEADER = self.data["secrets_header"]
    #     self.SECRETS_TOKEN = self.data["secrets_token"]

    #     async with async_open(self._config_file, "w") as f:
    #         yaml.dump(self.data, f)

    def load_secrets(self) -> None:
        try:
            response = requests.get(
                f"{self.SECRETS_DOMAIN}/api/secrets",
                headers={self.SECRETS_HEADER: self.SECRETS_TOKEN},
            )
            if response.status_code != 200:
                print(f"Error getting data from secrets - {response.status_code}")
                raise
        except Exception as e:
            print(f"Error getting data from secrets - {e}")
            raise

        secrets_data = response.json()["content"]

        self.DB_CONNECTION_STRING = ""
        # postgres
        postgres_data = secrets_data.get(f"{self.ENV}/db/postgres")
        if postgres_data:
            self.DB_CONNECTION_STRING = "{}://{}:{}@{}:{}/{}".format(
                "postgresql+asyncpg",
                postgres_data["user"],
                postgres_data["password"],
                postgres_data["host"],
                str(postgres_data["port"]),
                postgres_data["database"],
            )
        else:
            print("No postgres data in secrets")

        sqlite_data = secrets_data.get(f"{self.ENV}/db/sqlite")
        if sqlite_data:
            self.DB_CONNECTION_STRING = f"sqlite+aiosqlite:///{sqlite_data['path']}"
        else:
            print("No sqlite data in secrets")

        if not self.DB_CONNECTION_STRING:
            raise

        # owner data
        owner_data = secrets_data.get(f"{self.ENV}/owner")
        if owner_data:
            self.OWNER_LOGIN = owner_data["login"]
            self.OWNER_ID = owner_data["id"]
        else:
            print("No owner data in secrets")
            raise

        # domain
        domain_data = secrets_data.get(f"{self.ENV}/domain")
        if domain_data:
            self.DOMAIN = domain_data["domain"]
        else:
            print("No service domain data in secrets")
            raise

        # twitch
        twitch_data = secrets_data.get(f"{self.ENV}/twitch")
        if twitch_data:
            self.TWITCH_CLIENT_ID = twitch_data["client_id"]
            self.TWITCH_CLIENT_SECRET = twitch_data["client_secret"]
            self.TWITCH_SUBSCRIPTION_SECRET = twitch_data["subscription_secret"]
            self.TWITCH_BEARER = "NONE"
        else:
            print("No twitch data in secrets")
            raise

        # telegram
        telegram_data = secrets_data.get(f"{self.ENV}/telegram")
        if telegram_data:
            self.TELEGRAM_TOKEN = telegram_data["token"]
            self.TELEGRAM_SECRET = telegram_data["secret"]
            self.TELEGRAM_ALLOWED = telegram_data["allowed"]
        else:
            print("No telegram data in secrets")
            raise

    async def reload_secrets(self) -> list[str]:
        try:
            async with httpx.AsyncClient(
                base_url=self.SECRETS_DOMAIN,
                headers={self.SECRETS_HEADER: self.SECRETS_TOKEN},
            ) as ac:
                response = await ac.get("/api/secrets")
                if response.status_code != 200:
                    return [f"Error getting data from secrets - {response.status_code}"]
        except Exception as e:
            return [f"Error getting data from secrets - {e}"]

        secrets_data = response.json()["content"]
        no_secrets = []

        # # postgres
        # postgres_data = secrets_data.get(f"{self.ENV}/db/postgres")
        # if postgres_data:
        #     self.DB_CONNECTION_STRING = "{}://{}:{}@{}:{}/{}".format(
        #         "postgresql+asyncpg",
        #         postgres_data["user"],
        #         postgres_data["password"],
        #         postgres_data["host"],
        #         str(postgres_data["port"]),
        #         postgres_data["database"],
        #     )
        # else:
        #     no_secrets.append(f"{self.ENV}/db/postgres")

        # sqlite_data = secrets_data.get(f"{self.ENV}/db/sqlite")
        # if sqlite_data:
        #     self.DB_CONNECTION_STRING = f"sqlite+aiosqlite:///{sqlite_data['path']}"
        # else:
        #     no_secrets.append(f"{self.ENV}/db/sqlite")

        # owner data
        owner_data = secrets_data.get(f"{self.ENV}/owner")
        if owner_data:
            self.OWNER_LOGIN = owner_data["login"]
            self.OWNER_ID = owner_data["id"]
        else:
            no_secrets.append(f"{self.ENV}/owner")

        # domain
        domain_data = secrets_data.get(f"{self.ENV}/domain")
        if domain_data:
            self.DOMAIN = domain_data["domain"]
        else:
            no_secrets.append(f"{self.ENV}/domain")

        # twitch
        twitch_data = secrets_data.get(f"{self.ENV}/twitch")
        if twitch_data:
            self.TWITCH_CLIENT_ID = twitch_data["client_id"]
            self.TWITCH_CLIENT_SECRET = twitch_data["client_secret"]
            # self.TWITCH_SUBSCRIPTION_SECRET = twitch_data["subscription_secret"]
            # self.TWITCH_BEARER = "NONE"
        else:
            no_secrets.append(f"{self.ENV}/twitch")

        # telegram
        telegram_data = secrets_data.get(f"{self.ENV}/telegram")
        if telegram_data:
            self.TELEGRAM_TOKEN = telegram_data["token"]
            self.TELEGRAM_SECRET = telegram_data["secret"]
            self.TELEGRAM_ALLOWED = telegram_data["allowed"]
        else:
            no_secrets.append(f"{self.ENV}/telegram")

        return no_secrets


cfg = ConfigManager()
