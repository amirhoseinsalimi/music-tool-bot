import os

from dotenv import load_dotenv

load_dotenv(verbose=True)


def get_env(name: str, default=None):
    value = os.getenv(name)

    return value if value not in (None, "") else default


def get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


APP_ENV = get_env("APP_ENV", "development")

BOT_USERNAME = get_env("BOT_USERNAME")
BOT_TOKEN = get_env("BOT_TOKEN")

DATA_DIR = get_env("DATA_DIR", "/data")

DB_HOST = get_env("DB_HOST", "localhost")
DB_PORT = int(get_env("DB_PORT", 5432))
DB_DATABASE = get_env("DB_DATABASE", "")
DB_USERNAME = get_env("DB_USERNAME", "")
DB_PASSWORD = get_env("DB_PASSWORD", "")

OWNER_USER_ID = get_env("OWNER_USER_ID", 0)
OWNER_USER_ID_INT = int(OWNER_USER_ID)

DEBUGGER = get_bool_env("DEBUGGER", False)
DEBUGGER_HOST = get_env("DEBUGGER_HOST")
DEBUGGER_PORT = int(get_env("DEBUGGER_PORT", 5400))
DEBUGGER_SUSPEND = get_bool_env("DEBUGGER_SUSPEND", False)

BTC_WALLET_ADDRESS = get_env("BTC_WALLET_ADDRESS", "")
ETH_WALLET_ADDRESS = get_env("ETH_WALLET_ADDRESS", "")
TRX_WALLET_ADDRESS = get_env("TRX_WALLET_ADDRESS", "")
USDT_TRC20_WALLET_ADDRESS = get_env("USDT_TRC20_WALLET_ADDRESS", "")
USDT_ERC20_WALLET_ADDRESS = get_env("USDT_ERC20_WALLET_ADDRESS", "")
SHIBA_BEP20_WALLET_ADDRESS = get_env("SHIBA_BEP20_WALLET_ADDRESS", "")
SHIBA_ERC20_WALLET_ADDRESS = get_env("SHIBA_ERC20_WALLET_ADDRESS", "")
DOGE_WALLET_ADDRESS = get_env("DOGE_WALLET_ADDRESS", "")
ZARIN_LINK_ADDRESS = get_env("ZARIN_LINK_ADDRESS", "")
