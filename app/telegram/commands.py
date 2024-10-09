from aiogram import types

COMMANDS = [
    types.BotCommand(command="start", description="Start bot"),
    types.BotCommand(command="info", description="Simple info"),
    types.BotCommand(command="add_channel", description="Add bot to channel"),
    types.BotCommand(command="chats", description="Show chats/channels list"),
    types.BotCommand(command="subscriptions", description="Subscriptions list"),
    types.BotCommand(
        command="subscribe", description="Subscribe to stream notification"
    ),
    types.BotCommand(command="template", description="Change notification template"),
    types.BotCommand(
        command="unsubscribe", description="Unsubscribe from stream notification"
    ),
    types.BotCommand(command="stop", description="Stop bot"),
    types.BotCommand(command="admin", description="List of admin commands"),
]


COMMANDS_ADMIN = {
    "/users": "List all users with their channels",
    "/streamers": "List subscribed streamers",
    "/costs": "Twitch API costs",
    "/pause": "(Un)Pause bot",
    "/secrets_reload": "Reload secrets",
}
