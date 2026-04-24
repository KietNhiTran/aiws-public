# Databricks notebook source
# MAGIC %md
# MAGIC # Genie API  -  Full Capability Demo
# MAGIC
# MAGIC This notebook demonstrates **every Genie Conversation API endpoint** and pattern.
# MAGIC Use this as both a live demo and a reference for building custom integrations.
# MAGIC
# MAGIC ## API Endpoints Covered
# MAGIC
# MAGIC | # | Endpoint | Method | Purpose |
# MAGIC |---|---------|--------|---------|
# MAGIC | 1 | `/genie/spaces/{id}/start-conversation` | POST | Start conversation with initial question |
# MAGIC | 2 | `/genie/spaces/{id}/conversations/{cid}/messages/{mid}` | GET | Poll for generated SQL + status |
# MAGIC | 3 | `/genie/spaces/{id}/conversations/{cid}/messages/{mid}/attachments/{aid}/query-result` | GET | Fetch full query result data |
# MAGIC | 4 | `/genie/spaces/{id}/conversations/{cid}/messages` | POST | Follow-up question (multi-turn) |
# MAGIC | 5 | `/genie/spaces/{id}/conversations/{cid}/messages/{mid}/feedback` | POST | Submit thumbs up/down feedback |
# MAGIC | 6 | `/genie/spaces/{id}` | GET | Retrieve space config (Management API) |
# MAGIC
# MAGIC ## Limitations Demonstrated
# MAGIC
# MAGIC | Limitation | Value | Shown In |
# MAGIC |-----------|-------|----------|
# MAGIC | Rate limit | 5 questions/min/workspace (API) | Scenario 6 |
# MAGIC | Max tables per space | 30 | Discussed |
# MAGIC | Read-only queries | Cannot INSERT/UPDATE/DELETE | Scenario 5 |
# MAGIC | No cross-space joins | Each space is isolated | Discussed |
# MAGIC | Async execution | Must poll for results | All scenarios |
# MAGIC | Hallucination risk | Can generate wrong SQL if metadata is poor | Scenario 7 |

# COMMAND ----------

dbutils.widgets.text("genie_space_id", "", "Genie Space ID")
SPACE_ID = dbutils.widgets.get("genie_space_id")
assert SPACE_ID and SPACE_ID != "", "Please provide the Genie Space ID from notebook 03"

# COMMAND ----------

import requests, time, json
from pprint import pprint

host = spark.conf.get("spark.databricks.workspaceUrl")
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
BASE = f"https://{host}/api/2.0"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

def start_conversation(question):
    """API endpoint 1: Start a new conversation with an initial question."""
    resp = requests.post(f"{BASE}/genie/spaces/{SPACE_ID}/start-conversation", headers=H,
                         json={"content": question})
    resp.raise_for_status()
    data = resp.json()
    conv_id = data["conversation"]["id"]
    msg_id = data["message"]["id"]
    print(f"[SEND] Question: {question}")
    print(f"   Conversation: {conv_id[:16]}...  Message: {msg_id[:16]}...")
    return conv_id, msg_id


def poll_message(conv_id, msg_id, max_wait=90):
    """API endpoint 2: Poll until message is COMPLETED, FAILED, or timeout."""
    for attempt in range(max_wait // 3):
        time.sleep(3)
        resp = requests.get(
            f"{BASE}/genie/spaces/{SPACE_ID}/conversations/{conv_id}/messages/{msg_id}",
            headers=H
        )
        resp.raise_for_status()
        result = resp.json()
        status = result.get("status", "UNKNOWN")
        if status == "COMPLETED":
            print(f"[OK] Completed in ~{(attempt+1)*3}s")
            return result
        elif status in ("FAILED", "CANCELLED"):
            print(f"[FAIL] {status}: {result.get('error', 'unknown')}")
            return result
    print(f"[WAIT] Still processing after {max_wait}s  -  try again later")
    return None


def get_query_result(conv_id, msg_id, attachment_id):
    """API endpoint 3: Fetch the actual data rows from a query attachment."""
    resp = requests.get(
        f"{BASE}/genie/spaces/{SPACE_ID}/conversations/{conv_id}/messages/{msg_id}/attachments/{attachment_id}/query-result",
        headers=H
    )
    resp.raise_for_status()
    return resp.json()


def follow_up(conv_id, question):
    """API endpoint 4: Send a follow-up question in an existing conversation."""
    resp = requests.post(
        f"{BASE}/genie/spaces/{SPACE_ID}/conversations/{conv_id}/messages",
        headers=H, json={"content": question}
    )
    resp.raise_for_status()
    msg = resp.json()
    msg_id = msg.get("id") or msg.get("message_id")
    print(f"[SEND] Follow-up: {question}")
    return msg_id


def send_feedback(conv_id, msg_id, rating):
    """API endpoint 5: Submit feedback (POSITIVE or NEGATIVE) on a response."""
    resp = requests.post(
        f"{BASE}/genie/spaces/{SPACE_ID}/conversations/{conv_id}/messages/{msg_id}/feedback",
        headers=H, json={"rating": rating}
    )
    if resp.status_code == 200:
        print(f"[+1] Feedback '{rating}' submitted for message {msg_id[:16]}...")
    else:
        print(f"[WARN]  Feedback failed: {resp.status_code} {resp.text}")


def parse_response(result):
    """Parse a completed message response into readable output."""
    if not result or result.get("status") != "COMPLETED":
        return
    attachments = result.get("attachments", [])
    for att in attachments:
        att_type = att.get("type", "")
        if "query" in att or att_type == "QUERY":
            q = att.get("query", att)
            print(f"\n[DATA] Generated SQL:\n{q.get('query', q.get('sql', 'N/A'))}")
            print(f"[INFO] Description: {q.get('description', 'N/A')}")
            att_id = att.get("attachment_id") or att.get("id")
            if att_id:
                print(f"[KEY] Attachment ID: {att_id} (use to fetch full results)")
                return att_id
        if "text" in att or att_type == "TEXT":
            t = att.get("text", att)
            content = t.get("content", "") if isinstance(t, dict) else str(t)
            print(f"\n[MSG] Genie says: {content[:500]}")
    return None

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Scenario 1: Basic Question → SQL → Results
# MAGIC
# MAGIC The fundamental flow: ask a question, get SQL, fetch data.

# COMMAND ----------

conv_id, msg_id = start_conversation("Show me all red-status projects with their budget and cost variance")
result = poll_message(conv_id, msg_id)
att_id = parse_response(result)

# COMMAND ----------

# Fetch the actual data rows
if att_id:
    data = get_query_result(conv_id, msg_id, att_id)
    columns = [c.get("name", "?") for c in data.get("columns", data.get("manifest", {}).get("schema", {}).get("columns", []))]
    rows = data.get("data_array", data.get("result", {}).get("data_array", []))
    print(f"\n[DATA] Results: {len(rows)} rows × {len(columns)} columns")
    print(f"   Columns: {', '.join(columns)}")
    for row in rows[:5]:
        print(f"   {row}")
    if len(rows) > 5:
        print(f"   ... and {len(rows) - 5} more")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Scenario 2: Multi-Turn Conversation (Context Retained)
# MAGIC
# MAGIC Genie retains context from previous messages in the same conversation.
# MAGIC This means follow-up questions like "break that down by division" work naturally.

# COMMAND ----------

# Turn 1  -  establish context
conv_id, msg_id = start_conversation("What is the total budget across all projects?")
result = poll_message(conv_id, msg_id)
parse_response(result)

# COMMAND ----------

# Turn 2  -  follow-up (Genie knows we're talking about projects)
msg_id2 = follow_up(conv_id, "Break that down by division")
result2 = poll_message(conv_id, msg_id2)
parse_response(result2)

# COMMAND ----------

# Turn 3  -  drill deeper
msg_id3 = follow_up(conv_id, "Which division has the worst CPI?")
result3 = poll_message(conv_id, msg_id3)
parse_response(result3)

# COMMAND ----------

# Turn 4  -  pivot to a related topic (same conversation)
msg_id4 = follow_up(conv_id, "Are there any safety incidents at sites run by that division?")
result4 = poll_message(conv_id, msg_id4)
parse_response(result4)

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Scenario 3: Cross-Table Joins (Join Specs in Action)
# MAGIC
# MAGIC These questions require Genie to JOIN tables  -  enabled by the `join_specs`
# MAGIC we defined in the serialized_space.

# COMMAND ----------

conv_id, msg_id = start_conversation("Which projects have delayed critical path milestones?")
result = poll_message(conv_id, msg_id)
parse_response(result)

# COMMAND ----------

conv_id2, msg_id2 = start_conversation("What is the total maintenance cost by equipment manufacturer?")
result2 = poll_message(conv_id2, msg_id2)
parse_response(result2)

# COMMAND ----------

conv_id3, msg_id3 = start_conversation("Show me the top 5 projects by procurement spend")
result3 = poll_message(conv_id3, msg_id3)
parse_response(result3)

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Scenario 4: Business Metrics (SQL Snippets  -  Measures, Filters, Expressions)
# MAGIC
# MAGIC These questions use the reusable SQL snippets (measures, filters, expressions)
# MAGIC defined in the Genie Space.

# COMMAND ----------

# Uses the "total_budget" and "total_actual_cost" measures
conv_id, msg_id = start_conversation("What is the total budget vs total actual cost?")
result = poll_message(conv_id, msg_id)
parse_response(result)

# COMMAND ----------

# Uses the "cost_overrun_aud" expression
conv_id2, msg_id2 = start_conversation("Show me the cost overrun for each project")
result2 = poll_message(conv_id2, msg_id2)
parse_response(result2)

# COMMAND ----------

# Uses the "serious safety incidents" filter
conv_id3, msg_id3 = start_conversation("Show me all serious or critical safety incidents this year")
result3 = poll_message(conv_id3, msg_id3)
parse_response(result3)

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Scenario 5: Feedback API (Thumbs Up / Down)
# MAGIC
# MAGIC Submit quality feedback on Genie responses. This improves future accuracy
# MAGIC and is visible to space curators on the Monitoring tab.

# COMMAND ----------

conv_id, msg_id = start_conversation("What is the average CPI by division?")
result = poll_message(conv_id, msg_id)
parse_response(result)

# Rate it
send_feedback(conv_id, msg_id, "POSITIVE")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Scenario 6: Rate Limiting Demo
# MAGIC
# MAGIC **Limitation:** Genie API is rate-limited to **5 questions/minute/workspace** during preview.
# MAGIC This cell demonstrates proper error handling with exponential backoff.

# COMMAND ----------

import time

def ask_with_backoff(question, max_retries=3):
    """Ask a question with exponential backoff on rate limiting (HTTP 429)."""
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"{BASE}/genie/spaces/{SPACE_ID}/start-conversation",
                headers=H, json={"content": question}
            )
            if resp.status_code == 429:
                wait = 2 ** attempt * 15  # 15s, 30s, 60s
                print(f"[WARN]  Rate limited (429). Waiting {wait}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["conversation"]["id"], data["message"]["id"]
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
    print("[FAIL] Max retries exceeded")
    return None, None

# Demo: rapid-fire questions (will likely hit rate limit)
questions = [
    "How many projects are in NSW?",
    "What is the total maintenance downtime?",
    "Show me haul truck breakdowns",
    "Count of near-miss incidents",
    "Average fuel level across fleet",
    "Total procurement spend on concrete",
]

print("[START] Sending 6 rapid-fire questions (rate limit = 5/min)...")
for i, q in enumerate(questions):
    conv, msg = ask_with_backoff(q)
    if conv:
        print(f"  [OK] Q{i+1}: sent  -  {q[:50]}")
    else:
        print(f"  [FAIL] Q{i+1}: failed after retries")
    time.sleep(1)  # small gap

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Scenario 7: Limitations & Edge Cases
# MAGIC
# MAGIC Demonstrating what Genie **cannot** do or handles poorly.

# COMMAND ----------

# MAGIC %md
# MAGIC ### 7a: Write operations are blocked (read-only)

# COMMAND ----------

conv_id, msg_id = start_conversation("Delete all red-status projects from the financials table")
result = poll_message(conv_id, msg_id)
parse_response(result)
print("\n[NOTE] EXPECTED: Genie should refuse or generate a SELECT instead. All queries are read-only.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 7b: Ambiguous question without enough context

# COMMAND ----------

conv_id, msg_id = start_conversation("How are things going?")
result = poll_message(conv_id, msg_id)
parse_response(result)
print("\n[NOTE] EXPECTED: Genie should ask for clarification or provide a broad summary.")
print("   This is why text_instructions include clarification prompts.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 7c: Question requiring data NOT in the space

# COMMAND ----------

conv_id, msg_id = start_conversation("What is the current weather at Bowen Basin?")
result = poll_message(conv_id, msg_id)
parse_response(result)
print("\n[NOTE] EXPECTED: Genie should indicate it doesn't have weather data.")
print("   Genie is limited to tables in the space  -  no external data access.")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 7d: Cross-space query (not supported)

# COMMAND ----------

print("[WARN]  Genie spaces are isolated. You cannot query tables from Space A inside Space B.")
print("   Each space has its own table set, instructions, and SQL context.")
print("   To combine data from multiple domains, include all tables in one space (max 30)")
print("   or pre-join into views before adding to the space.")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Scenario 8: Retrieve Space Configuration (Management API)
# MAGIC
# MAGIC The Management API lets you export a space's config for version control or CI/CD.

# COMMAND ----------

resp = requests.get(f"{BASE}/genie/spaces/{SPACE_ID}", headers=H)
if resp.status_code == 200:
    space_config = resp.json()
    print(f"[INFO] Space: {space_config.get('title', 'unknown')}")
    print(f"   Description: {space_config.get('description', '')[:100]}...")
    print(f"   Warehouse: {space_config.get('warehouse_id', 'N/A')}")
    # Parse serialized_space to show structure
    ss = json.loads(space_config.get("serialized_space", "{}"))
    print(f"   Tables: {len(ss.get('data_sources', {}).get('tables', []))}")
    print(f"   Example SQLs: {len(ss.get('instructions', {}).get('example_question_sqls', []))}")
    print(f"   Benchmarks: {len(ss.get('benchmarks', {}).get('questions', []))}")
else:
    print(f"[WARN]  Could not retrieve: {resp.status_code}")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## How Foundry Orchestrates This
# MAGIC
# MAGIC When a **Microsoft Foundry agent** uses the Genie MCP tool, it performs these exact API calls
# MAGIC wrapped in the Model Context Protocol:
# MAGIC
# MAGIC ```
# MAGIC User asks question in Foundry
# MAGIC     │
# MAGIC     ▼
# MAGIC Foundry Agent (LLM decides Genie tool is relevant)
# MAGIC     │
# MAGIC     ▼ MCP tool_call → Databricks Managed MCP Server
# MAGIC     │
# MAGIC     ├─ POST /genie/spaces/{id}/start-conversation   ← Scenario 1
# MAGIC     ├─ GET  /genie/.../messages/{mid}                ← Polling
# MAGIC     ├─ GET  /genie/.../attachments/{aid}/query-result ← Fetch data
# MAGIC     │
# MAGIC     ▼ MCP tool_result ← results returned to agent
# MAGIC Foundry Agent formats and presents answer to user
# MAGIC ```
# MAGIC
# MAGIC **The MCP protocol wraps these REST calls so Foundry needs zero custom code.**
# MAGIC But understanding the raw API lets you:
# MAGIC - Build custom Genie integrations beyond Foundry
# MAGIC - Debug issues in the Foundry → Genie pipeline
# MAGIC - Create advanced routing (e.g., multiple Genie spaces per agent)
# MAGIC - Implement custom feedback loops
# MAGIC
# MAGIC ## Key Takeaways
# MAGIC
# MAGIC | Capability | Status | Notes |
# MAGIC |-----------|--------|-------|
# MAGIC | NL-to-SQL | [OK] Excellent | Best with curated instructions + example SQL |
# MAGIC | Multi-turn conversations | [OK] Works | Context retained within conversation |
# MAGIC | Cross-table joins | [OK] Works | Requires join_specs in serialized_space |
# MAGIC | Parameterised queries | [OK] Works | Parameters in example_question_sqls |
# MAGIC | Feedback loop | [OK] Works | POSITIVE/NEGATIVE via feedback API |
# MAGIC | Benchmarks | [OK] Works | Ground-truth for accuracy testing |
# MAGIC | SQL snippets (measures/filters) | [OK] Works | Reusable business logic |
# MAGIC | Write operations | [FAIL] Blocked | Read-only by design |
# MAGIC | Cross-space queries | [FAIL] Not supported | Each space is isolated |
# MAGIC | External data | [FAIL] Not supported | Limited to space tables |
# MAGIC | Rate limit | [WARN] 5 q/min (API) | Contact Databricks for higher limits |
# MAGIC | Max tables | [WARN] 30 per space | Use views to consolidate |