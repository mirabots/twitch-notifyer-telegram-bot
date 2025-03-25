from aiogram.types import BotCommand

COMMANDS = [
    BotCommand(command="info", description="Bot usage info"),
    BotCommand(command="channels", description="Manage user channels"),
    BotCommand(command="subscriptions", description="Subscriptions list and limites"),
    BotCommand(command="subscribe", description="Subscribe to stream notification"),
    BotCommand(command="template", description="Change notification template"),
    BotCommand(command="picture", description="Change notification picture mode"),
    BotCommand(
        command="restreams_links", description="Change notification restreams links"
    ),
    BotCommand(command="notification_test", description="Test notification"),
    BotCommand(
        command="online_streamers", description="Get currently online streamers"
    ),
    BotCommand(
        command="unsubscribe", description="Unsubscribe from stream notification"
    ),
    BotCommand(command="stop", description="Stop bot"),
    BotCommand(command="admin", description="List of admin commands"),
]

COMMANDS_ADMIN = {
    "pause": "(Un)Pause bot",
    "secrets_reload": "Reload secrets",
    "dump": "Manage bot db dump",
    "thumbnail": "Change thumbnail twitch size",
    "users": "List and manage users (+channels)",
    "limites": "User's limites",
    "streamers": "List subscribed streamers",
    "costs": "Twitch API costs",
    "broadcast_message": "Broadcast message to all users",
    "version": "Bot version",
}


def get_command(message_text: str) -> str:
    try:
        full_command, *args = message_text.split(maxsplit=1)
    except Exception:
        return ""

    _, (command, _, _) = full_command[0], full_command[1:].partition("@")
    return command
