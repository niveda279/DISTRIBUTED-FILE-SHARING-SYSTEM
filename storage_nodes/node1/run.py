"""Node 1 entry point."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import uvicorn
from node_server import app, HOST, PORT

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
