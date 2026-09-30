from src.db import init_db
from src.server import mcp

if __name__ == "__main__":
    init_db()
    mcp.run()
