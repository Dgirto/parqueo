import logging
import os
import sys

import uvicorn

# Permite ejecutar `python main.py` desde cualquier carpeta.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.api.main import crear_app
from app.core.config import HOST, PORT


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    uvicorn.run(crear_app(), host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
