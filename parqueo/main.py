import sys
import os

# Ensure the package root is on sys.path when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import DB_PATH
from app.database.db_manager import DatabaseManager
from app.core.parking_logic import ParkingLogic
from app.ui.main_window import MainWindow


def main():
    db = DatabaseManager(DB_PATH)
    db.initialize()

    logic = ParkingLogic(db)

    app = MainWindow(db, logic)
    app.mainloop()


if __name__ == "__main__":
    main()
