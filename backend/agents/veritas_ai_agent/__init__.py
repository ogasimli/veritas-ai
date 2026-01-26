import dotenv

dotenv.load_dotenv()

# Import app which internally handles agent mode selection
from .agent import app

__all__ = ["app"]
