"""
Agent Evaluation via Microsoft Foundry SDK

Runs batch evaluation against the Project Intelligence Agent using
the OpenAI-compatible Evaluations API. Results appear in both the Foundry
portal dashboard and the API response.

Usage:
    1. Copy .env.example to .env and fill in your values
    2. pip install -r requirements.txt
    3. python run_evaluation.py

See Module 5, Section 5.5.5 for full context.
"""

import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai.types.eval_create_params import DataSourceConfigCustom
from openai.types.evals.create_eval_jsonl_run_data_source_param import (
    CreateEvalJSONLRunDataSourceParam,
    SourceFileID,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()

ENDPOINT = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT = os.environ.get("JUDGE_MODEL_DEPLOYMENT", "gpt-4o")
AGENT_NAME = os.environ.get("AGENT_NAME", "project-advisor")
AGENT_VERSION = os.environ.get("AGENT_VERSION", "")  # blank = latest
DATASET_NAME = os.environ.get("EVAL_DATASET_NAME", "agent-eval-v1")
DATASET_VERSION = os.environ.get("EVAL_DATASET_VERSION", "1")
EVAL_NAME = os.environ.get("EVAL_NAME", "agent-eval-v1")
DATASET_PATH = Path(__file__).parent / "eval-dataset.jsonl"

# ---------------------------------------------------------------------------
# Connect to Foundry
# ---------------------------------------------------------------------------
project_client = AIProjectClient(
    endpoint=ENDPOINT,
    credential=DefaultAzureCredential(),
)
client = project_client.get_openai_client()

# ---------------------------------------------------------------------------
# Upload evaluation dataset (reuse existing if already uploaded)
# ---------------------------------------------------------------------------
print(f"Uploading dataset '{DATASET_NAME}' v{DATASET_VERSION} from {DATASET_PATH} ...")
try:
    dataset = project_client.datasets.upload_file(
        name=DATASET_NAME,
        version=DATASET_VERSION,
        file_path=str(DATASET_PATH),
    )
    data_id = dataset.id
    print(f"Dataset uploaded: {data_id}")
except Exception as e:
    if "already exists" in str(e):
        print(f"Dataset already exists — reusing '{DATASET_NAME}' v{DATASET_VERSION}")
        dataset = project_client.datasets.get(name=DATASET_NAME, version=DATASET_VERSION)
        data_id = dataset.id
        print(f"Dataset reused: {data_id}")
    else:
        raise

# ---------------------------------------------------------------------------
# Data schema — query is required; agent generates response at runtime
# ---------------------------------------------------------------------------
data_source_config = DataSourceConfigCustom(
    type="custom",
    item_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "ground_truth": {"type": "string"},
        },
        "required": ["query"],
    },
    include_sample_schema=True,  # Enables {{sample.*}} variables
)

# ---------------------------------------------------------------------------
# Evaluators (testing criteria)
# ---------------------------------------------------------------------------
testing_criteria = [
    {
        "type": "azure_ai_evaluator",
        "name": "task_adherence",
        "evaluator_name": "builtin.task_adherence",
        "initialization_parameters": {"deployment_name": MODEL_DEPLOYMENT},
        "data_mapping": {
            "query": "{{item.query}}",
            "response": "{{sample.output_items}}",
        },
    },
    {
        "type": "azure_ai_evaluator",
        "name": "intent_resolution",
        "evaluator_name": "builtin.intent_resolution",
        "initialization_parameters": {"deployment_name": MODEL_DEPLOYMENT},
        "data_mapping": {
            "query": "{{item.query}}",
            "response": "{{sample.output_text}}",
        },
    },
    {
        "type": "azure_ai_evaluator",
        "name": "tool_call_accuracy",
        "evaluator_name": "builtin.tool_call_accuracy",
        "initialization_parameters": {"deployment_name": MODEL_DEPLOYMENT},
        "data_mapping": {
            "query": "{{item.query}}",
            "response": "{{sample.output_items}}",
            "tool_definitions": "{{sample.tool_definitions}}",
        },
    },
    {
        "type": "azure_ai_evaluator",
        "name": "coherence",
        "evaluator_name": "builtin.coherence",
        "initialization_parameters": {"deployment_name": MODEL_DEPLOYMENT},
        "data_mapping": {
            "query": "{{item.query}}",
            "response": "{{sample.output_text}}",
        },
    },
    {
        "type": "azure_ai_evaluator",
        "name": "violence",
        "evaluator_name": "builtin.violence",
        "data_mapping": {
            "query": "{{item.query}}",
            "response": "{{sample.output_text}}",
        },
    },
]

# ---------------------------------------------------------------------------
# Agent target and input messages
# ---------------------------------------------------------------------------
input_messages = {
    "type": "template",
    "template": [
        {
            "type": "message",
            "role": "user",
            "content": {"type": "input_text", "text": "{{item.query}}"},
        }
    ],
}

target = {"type": "azure_ai_agent", "name": AGENT_NAME}
if AGENT_VERSION:
    target["version"] = AGENT_VERSION

# ---------------------------------------------------------------------------
# Create evaluation definition and run
# ---------------------------------------------------------------------------
print(f"Creating evaluation '{EVAL_NAME}' ...")
eval_object = client.evals.create(
    name=EVAL_NAME,
    data_source_config=data_source_config,
    testing_criteria=testing_criteria,
)

print(f"Starting evaluation run against agent '{AGENT_NAME}' ...")
eval_run = client.evals.runs.create(
    eval_id=eval_object.id,
    name=f"{EVAL_NAME}-run-1",
    data_source={
        "type": "azure_ai_target_completions",
        "source": SourceFileID(type="file_id", id=data_id),
        "input_messages": input_messages,
        "target": target,
    },
)

print(f"\nEvaluation started: {eval_run.id}")
print(f"View results in the Foundry portal under Evaluation → {eval_run.id}")
