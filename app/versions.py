import yaml

APP_VERSION = "2.13.1"

APP_VERSION_DETAILS = {}
with open("config/versions.yaml", "r") as f:
    APP_VERSION_DETAILS = yaml.safe_load(f.read())

APP_COMMIT_BRANCH = APP_VERSION_DETAILS.get("APP_COMMIT_BRANCH", "")
APP_COMMIT_HASH = APP_VERSION_DETAILS.get("APP_COMMIT_HASH", "")
APP_COMMIT_TIME = APP_VERSION_DETAILS.get("APP_COMMIT_TIME", "")
APP_BUILD_TIME = APP_VERSION_DETAILS.get("APP_BUILD_TIME", "")
APP_BUILD_NUMBER = APP_VERSION_DETAILS.get("APP_BUILD_NUMBER", "")

APP_VERSION_STRING = (
    f"● VERSION: {APP_VERSION}"
    f"\n● BRANCH: {APP_COMMIT_BRANCH}"
    f"\n● COMMIT: {APP_COMMIT_HASH}"
    f"\n● COMMIT TIME: {APP_COMMIT_TIME}"
    f"\n● BUILD TIME: {APP_BUILD_TIME}"
    f"\n● BUILD NUMBER: {APP_BUILD_NUMBER}"
)
