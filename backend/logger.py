import json
import logging
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(message)s"
)

def log_request(data: dict):
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        **data
    }
    logging.info(json.dumps(record))
