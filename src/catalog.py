"""
catalog.py — One file, one prompt, full pipeline:
  1. Read openapi.json
  2. Structure all endpoints into clean JSON
  3. Send ALL of them in ONE prompt to Gemini
  4. Get back the full catalog
  5. Save everything to SQLite DB
"""

import os, json
import google.generativeai as genai
from src.db import SessionLocal, ActionRecord, init_db
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# STEP 1 — Read & structure openapi.json
# ─────────────────────────────────────────────
def read_openapi(filepath: str) -> list:
    with open(filepath, "r", encoding="utf-8") as f:
        spec = json.load(f)

    endpoints = []
    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.lower() not in ["get", "post", "put", "patch", "delete"]:
                continue

            parameters = []
            for p in details.get("parameters", []):
                parameters.append({
                    "name":     p.get("name", ""),
                    "location": p.get("in", "query"),
                    "required": p.get("required", False),
                    "type":     p.get("schema", {}).get("type", "string")
                })

            body = (details.get("requestBody", {})
                          .get("content", {})
                          .get("application/json", {})
                          .get("schema", {}))
            for field, info in body.get("properties", {}).items():
                parameters.append({
                    "name":     field,
                    "location": "body",
                    "required": field in body.get("required", []),
                    "type":     info.get("type", "string")
                })

            endpoints.append({
                "path":       path,
                "method":     method.upper(),
                "summary":    details.get("summary", ""),
                "parameters": parameters
            })

    print(f"✅ Extracted {len(endpoints)} endpoints from {filepath}")
    return endpoints


# ─────────────────────────────────────────────
# STEP 2 — Build ONE prompt for ALL endpoints
# ─────────────────────────────────────────────
def build_prompt(endpoints: list) -> str:
    endpoints_json = json.dumps(endpoints, indent=2)
    return f"""You are an API catalog agent. I will give you a list of raw API endpoints.
Your job is to clean them up and return a structured catalog.

For EACH endpoint, create a catalog entry with:
- action_id:   unique snake_case id (e.g. "tasks_create_task")
- category:    short category name (e.g. "tasks", "users", "auth")
- summary:     one clear sentence describing what this action does
- is_mutation: true if POST/PUT/PATCH/DELETE, false if GET
- path:        keep the original path
- method:      keep the original method
- parameters:  keep the original parameters list

Return ONLY a valid JSON array of all catalog entries. No markdown, no explanation, just the JSON array.

Here are all the endpoints:
{endpoints_json}"""


# ─────────────────────────────────────────────
# STEP 3 — Send to Gemini, get catalog back
# ─────────────────────────────────────────────
def ask_gemini(prompt: str) -> list:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model    = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    response = model.generate_content(prompt)
    raw      = response.text.strip()

    # Strip markdown fences if Gemini wraps in ```json
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw   = "\n".join(lines[1:-1])

    catalog = json.loads(raw)
    print(f"✅ Gemini returned {len(catalog)} catalog entries")
    return catalog


# ─────────────────────────────────────────────
# STEP 4 — Save full catalog to SQLite
# ─────────────────────────────────────────────
def save_catalog(catalog: list):
    with SessionLocal() as db:
        for entry in catalog:
            record = ActionRecord(
                action_id         = entry.get("action_id", "unknown"),
                category          = entry.get("category", "general"),
                summary           = entry.get("summary", ""),
                path              = entry.get("path", ""),
                method            = entry.get("method", "GET"),
                is_mutation       = entry.get("is_mutation", False),
                parameters_schema = entry.get("parameters", [])
            )
            db.merge(record)
        db.commit()
    print(f"✅ Saved {len(catalog)} actions to database")


# ─────────────────────────────────────────────
# MAIN — Run full pipeline
# ─────────────────────────────────────────────
def build_catalog(openapi_path: str = "openapi.json"):
    print("\n🚀 Building catalog...\n")

    init_db()                              # create DB tables if not exist
    endpoints = read_openapi(openapi_path) # step 1: read & structure
    prompt    = build_prompt(endpoints)    # step 2: one big prompt
    catalog   = ask_gemini(prompt)         # step 3: send to Gemini, get catalog
    save_catalog(catalog)                  # step 4: save all to DB

    print("\n🎉 Catalog complete and saved to badis_mcp.db")

if __name__ == "__main__":
    build_catalog()
