# Agent Evaluation (SDK)

Runs batch evaluation against the Project Intelligence Agent using the Microsoft Foundry SDK. This is the scriptable equivalent of the portal evaluation described in Module 5, Section 5.5.3.

## Quick Start

```bash
# 1. Navigate to this directory
cd src/eval

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Edit .env and fill in your AZURE_AI_PROJECT_ENDPOINT

# 5. Run the evaluation
python run_evaluation.py
```

The script will:
1. Upload `eval-dataset.jsonl` to your Foundry project
2. Create an evaluation definition with 5 built-in evaluators
3. Run the evaluation against your agent
4. Print the evaluation run ID — view results in the Foundry portal

## Files

| File | Description |
|------|-------------|
| `run_evaluation.py` | Main evaluation script |
| `eval-dataset.jsonl` | 10 domain-specific test cases with ground truth |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |

## Evaluators

| Evaluator | Category | What It Measures |
|-----------|----------|-----------------|
| `task_adherence` | Agent | Does the agent follow its system instructions? |
| `intent_resolution` | Agent | Does the agent correctly identify the user's intent? |
| `tool_call_accuracy` | Agent | Did the agent call the right tools with correct parameters? |
| `coherence` | Quality | Is the response logical and well-structured? |
| `violence` | Safety | Does the response contain violent content? |
