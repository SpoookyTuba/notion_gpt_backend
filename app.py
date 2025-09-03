# Manual edit - force GitHub to recognize change
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)
NOTION_TOKEN = os.getenv("NOTION_TOKEN")  # Get token from environment variable
NOTION_VERSION = '2022-06-28'
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION
}

NOTION_API_BASE = "https://api.notion.com/v1"

@app.route('/create-page', methods=['POST'])
def create_page():
    data = request.json
    database_id = data['databaseId']
    properties = data['properties']
    notion_props = {
        "parent": { "database_id": database_id },
        "properties": {}
    }

    for key, value in properties.items():
        if key == "Name":
            notion_props["properties"][key] = {
                "title": [{ "text": { "content": value } }]
            }
        elif key == "Status":
            notion_props["properties"][key] = {
                "status": { "name": value }
            }
        else:
            notion_props["properties"][key] = {
                "rich_text": [{ "text": { "content": value } }]
            }

    response = requests.post(f"{NOTION_API_BASE}/pages", headers=NOTION_HEADERS, json=notion_props)
    return jsonify(response.json())

@app.route('/update-page', methods=['POST'])
def update_page():
    data = request.json
    page_id = data['pageId']
    properties = data['properties']

    updated_props = {}
    for key, value in properties.items():
        if key == "Status":
            updated_props[key] = {
                "status": { "name": value }
            }
        else:
            updated_props[key] = {
                "rich_text": [{ "text": { "content": value } }]
            }

    response = requests.patch(f"{NOTION_API_BASE}/pages/{page_id}", headers=NOTION_HEADERS, json={"properties": updated_props})
    return jsonify(response.json())

@app.route('/query-database', methods=['POST'])
def query_database():
    data = request.json
    database_id = data['databaseId']
    filter_ = data.get('filter', {})

    response = requests.post(f"{NOTION_API_BASE}/databases/{database_id}/query", headers=NOTION_HEADERS, json={"filter": filter_})
    return jsonify(response.json())

@app.route('/read-page', methods=['POST'])
def read_page():
    data = request.json
    page_id = data['pageId']

    response = requests.get(f"{NOTION_API_BASE}/pages/{page_id}", headers=NOTION_HEADERS)
    return jsonify(response.json())

@app.route('/', methods=['GET'])
def home():
    return "Notion GPT Backend is running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
