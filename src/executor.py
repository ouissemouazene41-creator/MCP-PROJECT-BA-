import httpx, uuid
from src.db import SessionLocal, ExecutionLog

async def execute_action(action: dict, input_params: dict, base_url: str, token: str = "") -> dict:
    """Resolve params, fire the HTTP call, log it, return the result."""
    url_path    = action["path"]
    query_params = {}
    body_data    = {}

    for p in action.get("parameters_schema", []):
        name = p["name"]
        if name not in input_params:
            continue
        loc = p.get("location", "query")
        if loc == "path":
            url_path = url_path.replace(f"{{{name}}}", str(input_params[name]))
        elif loc == "query":
            query_params[name] = input_params[name]
        elif loc == "body":
            body_data[name] = input_params[name]

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    async with httpx.AsyncClient(base_url=base_url, timeout=20.0) as client:
        resp = await client.request(
            method  = action["method"],
            url     = url_path,
            params  = query_params or None,
            json    = body_data or None,
            headers = headers
        )

    # Decide response format
    is_json = "application/json" in resp.headers.get("content-type", "")
    resp_data = resp.json() if is_json else {"text": resp.text}

    # Log to SQLite
    with SessionLocal() as session:
        session.add(ExecutionLog(
            id            = str(uuid.uuid4()),
            action_id     = action["action_id"],
            http_status   = str(resp.status_code),
            payload       = input_params,
            response_data = resp_data
        ))
        session.commit()

    return {"status": resp.status_code, "data": resp_data}
