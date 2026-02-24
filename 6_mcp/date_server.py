from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("date_server")

@mcp.tool()
def get_current_date() -> str:
    """Get the current date and time.

    Returns the current date and time as a formatted string.
    """
    return datetime.now().strftime("%A, %B %d, %Y at %H:%M:%S")

if __name__ == "__main__":
    mcp.run(transport='stdio')
