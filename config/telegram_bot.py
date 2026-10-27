from pathlib import Path

from telegram.constants import ParseMode
from telegram.ext import Application, Defaults, PicklePersistence

from utils.polling_health import PollingHealthRequest
from utils.error_handler import on_error

from config.constants import PERSISTENCE_UPDATE_INTERVAL
from config.envs import BOT_TOKEN, DATA_DIR

data_dir = Path(DATA_DIR)
data_dir.mkdir(parents=True, exist_ok=True)

pickle = PicklePersistence(filepath=str(data_dir / "persistence.pickle"), update_interval=PERSISTENCE_UPDATE_INTERVAL)

defaults = Defaults(parse_mode=ParseMode.HTML)

app = (
    Application.builder()
    .token(BOT_TOKEN)
    .get_updates_request(PollingHealthRequest(data_dir / "bot-health.json", connection_pool_size=1))
    .defaults(defaults)
    .persistence(pickle)
    .concurrent_updates(False)
    .build()
)

app.add_error_handler(on_error)

add_handler = app.add_handler
