from pathlib import Path

from telegram.constants import ParseMode
from telegram.ext import Application, Defaults, PicklePersistence

from config.constants import PERSISTENCE_UPDATE_INTERVAL
from config.envs import BOT_TOKEN, DATA_DIR

data_dir = Path(DATA_DIR)
data_dir.mkdir(parents=True, exist_ok=True)

pickle = PicklePersistence(filepath=str(data_dir / "persistence.pickle"), update_interval=PERSISTENCE_UPDATE_INTERVAL)

defaults = Defaults(parse_mode=ParseMode.HTML)

app = (
    Application.builder()
    .token(BOT_TOKEN)
    .defaults(defaults)
    .persistence(pickle)
    .concurrent_updates(False)
    .build()
)

add_handler = app.add_handler
