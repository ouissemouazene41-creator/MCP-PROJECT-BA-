import os
from mcp.server.fastmcp import FastMCP
from src.db import SessionLocal, ActionRecord
from src.executor import execute_action
from dotenv import load_dotenv

load_dotenv()

# Initialize the FastMCP Server
mcp = FastMCP("BADIS-MCP")

@mcp.tool()
def list_actions(category: str = "") -> list:
    """List all available API actions stored in the database. Optionally filter by category."""
    with SessionLocal() as db:
        query = db.query(ActionRecord)
        if category:
            query = query.filter(ActionRecord.category == category)
        return [
            {
                "action_id": a.action_id,
                "summary": a.summary,
                "category": a.category,
                "is_mutation": a.is_mutation
            }
            for a in query.all()
        ]

@mcp.tool()
def get_action_details(action_id: str) -> dict:
    """Get endpoint details, path, method, and parameters schema for a specific action."""
    with SessionLocal() as db:
        action = db.query(ActionRecord).filter(ActionRecord.action_id == action_id).first()
        if not action:
            return {"error": f"Action '{action_id}' not found in catalog"}
        return {
            "action_id":  action.action_id,
            "category":   action.category,
            "summary":    action.summary,
            "path":       action.path,
            "method":     action.method,
            "parameters": action.parameters_schema
        }

@mcp.tool()
async def call_action(action_id: str, parameters: dict) -> dict:
    """Execute the target API action on the backend (e.g. ClickUp)."""
    with SessionLocal() as db:
        action = db.query(ActionRecord).filter(ActionRecord.action_id == action_id).first()
        if not action:
            return {"error": f"Action '{action_id}' not found in catalog"}
        
        action_dict = {
            "action_id":         action.action_id,
            "path":              action.path,
            "method":            action.method,
            "parameters_schema": action.parameters_schema
        }

    return await execute_action(
        action       = action_dict,
        input_params = parameters,
        base_url     = os.getenv("API_BASE_URL", "https://api.clickup.com/api/v2"),
        token        = os.getenv("API_BEARER_TOKEN", "")
    )
