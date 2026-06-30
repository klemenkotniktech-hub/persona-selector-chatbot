import logging
from datetime import datetime
from pathlib import Path

# Set up logging
from app.core.config import LOGS_DIR

log_dir = Path(LOGS_DIR)
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"api_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("chatbot_api")