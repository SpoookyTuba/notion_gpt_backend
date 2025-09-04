# Manual edit - force GitHub to recognize change
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# --- Notion config ---
NOTION_TOKEN = os.getenv("NOTION_TOKEN")  # Set in your Render env
NOTION_VERSION = '2022-06-28'
NOTION_API_BASE = "https://api.notion.com/v1"

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION
}

# ---------- Helpers ----------

def _to_number(value):
    try:
        f = float(str(value).strip())
        return int(f) if f.is_integer() else f
    except Exception:
        return None

def _to_multi_select_list(value):
    """
    Accepts:
      - string like "tag1; tag2, tag3"
      - list/tuple of strings
    Returns list of {"name": tag}
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        names = [str(v).strip() for v in value if str(v).strip()]
    else:
        text = str(value)
        parts = []
        for chunk in text.split(";"):
            parts.extend(chunk.split(","))
        names = [p.strip() for p in parts if p.strip()]
    return [{"name": n} for n in names]

def map_properties_for_create(flat_props: dict) -> dict:
    """
    Convert flat string dict to Notion property objects for page creation.
    Special handling:
      - Name     -> title
      - Status   -> status
      - Section  -> select
      - Tags     -> multi_select
      - Order    -> number
      - Source   -> select
      - Content  -> rich_text
      - others   -> rich_text
    """
    mapped = {}
    for key, value in (flat_props or {}).items():
        if key == "Name":
            mapped[key] = {"title": [{"text": {"content": str(value)}}]}
        elif key == "Status":
            mapped[key] = {"status": {"name": str(value)}}
        elif key == "Section":
            mapped[key] = {"select": {"name": str(value)}}
        elif key == "Tags":
            mapped[key] = {"multi_select": _to_multi_select_list(value)}
        elif key == "Order":
            num = _to_number(value)
            if num is not None:
                mapped[key] = {"number": num}
        elif key == "Source":
            mapped[key] = {"select": {"name": str(value)}}
        elif key == "Content":
            mapped[key] = {"rich_text": [{"text": {"content": str(value)}}]}
        else:
            mapped[key] = {"rich_text": [{"text": {"content": str(value)}}]}
    return mapped

def map_properties_for_update(flat_props: dict) -> dict:
    """
    Same mapping as create, but for updates.
    """
    mapped = {}
    for key, value in (flat_props or {}).items():
        if key == "Name":
            mapped[key] = {"title": [{"text": {"content": str(value)}}]}
        elif key == "Status":
            mapped[key] = {"status": {"name": str(value)}}
        elif key == "Section":
            mapped[key] = {"select": {"name": str(value)}}
        elif key == "Tags":
            mapped[key] = {"multi_select": _to_multi_select_list(value)}
        elif key == "Order":
            num = _to_number(value)
            if num is not None:
                mapped[key] = {"number": num}
        elif key == "Source":
            mapped[key] = {"select": {"name": str(value)}}
        elif key == "Content":
            mapped[key] = {"rich_text": [{"text": {"content": str(value)}}]}
        else:
            mapped[key] = {"rich_text": [{"text": {"content": str(value)}}]}
    return mapped

def safe_json_response(resp):
    """Return Notion's JSON (if any) with the same status code."""
    try:
        return jsonify(resp.json()), resp.status_code
    except Exception:
        return jsonify({"status": resp.status_code, "text": resp.text}), resp.status_code

# ---------- Routes ----------

@app.route('/create-page', methods=['POST'])
def create_page():
    data = request.get_json(silent=True) or {}

    # Safe field handling (optional defaults so action tests don't 500 on empty bodies)
    database_id = data.get('databaseId')
    properties = data.get('properties')

    # If a databaseId was provided but properties is missing/empty,
    # fall back to safe defaults instead of 400.
    if database_id and not properties:
        properties = {"Name": "Untitled from Action Test", "Status": "Not started"}

    if not database_id:
        return jsonify({"error": "Missing 'databaseId' in request body"}), 400
    if not properties:
        return jsonify({"error": "Missing 'properties' in request body"}), 400

    notion_props = {
        "parent": {"database_id": database_id},
        "properties": map_properties_for_create(properties)
    }

    # Debug logs
    print("📤 /create-page -> Notion payload:")
    print(notion_props)

    response = requests.post(
        f"{NOTION_API_BASE}/pages",
        headers=NOTION_HEADERS,
        json=notion_props,
        timeout=30
    )

    print("📥 /create-page <- Notion response:", response.status_code)
    print(response.text[:2000])  # trim huge logs

    return safe_json_response(response)

@app.route('/update-page', methods=['POST'])
def update_page():
    data = request.get_json(silent=True) or {}
    page_id = data.get('pageId')
    properties = data.get('properties')

    if not page_id:
        return jsonify({"error": "Missing 'pageId' in request body"}), 400
    if not properties:
        return jsonify({"error": "Missing 'properties' in request body"}), 400

    updated_props = map_properties_for_update(properties)
    payload = {"properties": updated_props}

    print("📤 /update-page -> Notion payload:")
    print({"pageId": page_id, **payload})

    response = requests.patch(
        f"{NOTION_API_BASE}/pages/{page_id}",
        headers=NOTION_HEADERS,
        json=payload,
        timeout=30
    )

    print("📥 /update-page <- Notion response:", response.status_code)
    print(response.text[:2000])

    return safe_json_response(response)

@app.route('/query-database', methods=['POST'])
def query_database():
    data = request.get_json(silent=True) or {}
    database_id = data.get('databaseId')
    if not database_id:
        return jsonify({"error": "Missing 'databaseId' in request body"}), 400

    # Optional Notion query args
    payload = {}
    if "filter" in data and data["filter"] is not None:
        payload["filter"] = data["filter"]
    if "sorts" in data and data["sorts"] is not None:
        payload["sorts"] = data["sorts"]
    if "start_cursor" in data and data["start_cursor"]:
        payload["start_cursor"] = data["start_cursor"]
    if "page_size" in data and data["page_size"]:
        payload["page_size"] = data["page_size"]

    print("📤 /query-database -> Notion payload:")
    print({"database_id": database_id, **payload})

    response = requests.post(
        f"{NOTION_API_BASE}/databases/{database_id}/query",
        headers=NOTION_HEADERS,
        json=payload if payload else {},
        timeout=30
    )

    print("📥 /query-database <- Notion response:", response.status_code)
    # Avoid dumping entire result set in logs
    return safe_json_response(response)

@app.route('/read-page', methods=['POST'])
def read_page():
    data = request.get_json(silent=True) or {}
    page_id = data.get('pageId')
    if not page_id:
        return jsonify({"error": "Missing 'pageId' in request body"}), 400

    print("📤 /read-page -> Notion GET:", page_id)

    response = requests.get(
        f"{NOTION_API_BASE}/pages/{page_id}",
        headers=NOTION_HEADERS,
        timeout=30
    )

    print("📥 /read-page <- Notion response:", response.status_code)
    return safe_json_response(response)

@app.route('/', methods=['GET'])
def home():
    return "Notion GPT Backend is running!"

if __name__ == '__main__':
    port = int(os.getenv("PORT", "5000"))
    app.run(host='0.0.0.0', port=port)
