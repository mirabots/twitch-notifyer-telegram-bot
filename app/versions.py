import yaml

APP_VERSION = "2.11.11"

APP_VERSION_DETAILS = {}
with open("config/versions.yaml", "r") as f:
    APP_VERSION_DETAILS = yaml.safe_load(f.read())

APP_COMMIT_BRANCH = APP_VERSION_DETAILS.get("APP_COMMIT_BRANCH", "")
APP_COMMIT_HASH = APP_VERSION_DETAILS.get("APP_COMMIT_HASH", "")
APP_COMMIT_TIME = APP_VERSION_DETAILS.get("APP_COMMIT_TIME", "")
APP_DEPLOY_TIME = APP_VERSION_DETAILS.get("APP_DEPLOY_TIME", "")
APP_DEPLOY_NUMBER = APP_VERSION_DETAILS.get("APP_DEPLOY_NUMBER", "")

APP_VERSION_STRING = (
    f"● VERSION: {APP_VERSION}"
    f"\n● BRANCH: {APP_COMMIT_BRANCH}"
    f"\n● COMMIT: {APP_COMMIT_HASH}"
    f"\n● COMMIT TIME: {APP_COMMIT_TIME}"
    f"\n● DEPLOY TIME: {APP_DEPLOY_TIME}"
    f"\n● DEPLOY NUMBER: {APP_DEPLOY_NUMBER}"
)
