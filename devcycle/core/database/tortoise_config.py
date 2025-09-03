"""
Tortoise ORM configuration for DevCycle.

Simple, single-file configuration for all database operations.
"""

from tortoise import Tortoise

from ..config import get_config


def get_database_url() -> str:
    """Get database connection URL from configuration."""
    config = get_config().database
    if config.password:
        return (
            f"postgresql://{config.username}:{config.password}@"
            f"{config.host}:{config.port}/{config.database}"
        )
    else:
        return (
            f"postgresql://{config.username}@{config.host}:"
            f"{config.port}/{config.database}"
        )


TORTOISE_ORM = {
    "connections": {"default": get_database_url()},
    "apps": {
        "models": {
            "models": [
                "devcycle.core.models.tortoise_models",
                "devcycle.core.auth.tortoise_models",
                "aerich.models",
            ],
            "default_connection": "default",
        },
    },
}


async def init_tortoise() -> None:
    """Initialize Tortoise ORM."""
    await Tortoise.init(config=TORTOISE_ORM)
    print("✅ Tortoise ORM initialized")


async def close_tortoise() -> None:
    """Close Tortoise ORM connections."""
    await Tortoise.close_connections()
    print("✅ Tortoise ORM connections closed")
