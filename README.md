# LLM Regression Testing

This example demonstrates how regression testing can flag factual errors and hallucinations in AI-generated scientific explanations.
Comparing answers against research-based facts helps researchers spot misleading mechanisms and unsupported clinical claims before relying on them.

## Overview

The example evaluates two advanced neuropharmacology questions about the **ventral tegmental area (VTA)**, a midbrain region involved in dopamine signaling.

| Stage | What happens |
| --- | --- |
| Generate | OpenAI answers each question using prompts A and B. |
| Evaluate | A separate OpenAI request scores accuracy and clarity from 0 to 2. |
| Compare | Python reports each version's PASS/FAIL, score differences, and the regression gate. |
| Record | JSON results are saved in `results/`; Langfuse records calls and scores. |

## A/B demonstration

| Version | Prompt behavior | Expected result |
| --- | --- | --- |
| A | Uses verified facts and preserves limits of human translation. | PASS |
| B | Deliberately presents false claims as true. | FAIL |

Both prompts allow up to **100 words**. Answers come from live API requests; the judge assigns scores without seeing the A/B label. Scores are never forced by the code.

B is a **negative control**: an intentionally flawed example used to check whether grading detects an error. This is an offline prompt comparison, not a randomized user experiment or a fair comparison of two useful prompts.

## Setup and run

### 1. Install dependencies

Use **Python 3.10 or later**. In PowerShell, from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Alternatively, use uv to install the versions pinned in `uv.lock`:

```powershell
uv sync --locked
```

Commit both `pyproject.toml` and `uv.lock` to share the dependency versions.

### 2. Configure credentials

If `.env` is missing, copy `.env.example` to `.env`. Fill in your credentials:

```dotenv
OPENAI_API_KEY=your_actual_key_here
LLM_MODEL=gpt-4o-mini
JUDGE_MODEL=gpt-4o-mini
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

- **OpenAI:** get your key from [API settings](https://platform.openai.com/api-keys).
- **Langfuse:** create a project and get its public and secret keys from **Project Settings > API Keys**. These are separate from your OpenAI key.
- **Project URL:** use your Langfuse project's URL. The example uses the EU region. For self-hosting, use your own URL.

`.env` is ignored by Git. Existing environment variables take precedence over values in `.env`.

### 3. Run the example

```powershell
.\.venv\Scripts\python.exe drug_discovery.py
```

With uv:

```powershell
uv run --locked drug_discovery.py
```

Each complete run makes **four answer requests and four judge requests**. API usage is billed to your OpenAI API account.

## Read the results

### Scores and pass/fail rules

| Score | Accuracy | Clarity |
| --- | --- | --- |
| 0 | Major error, contradiction, refusal, or no relevant answer. | Confusing. |
| 1 | Correct but incomplete. | Understandable with unexplained technical terms. |
| 2 | All required facts without contradictions. | Clear scientific reasoning with essential abbreviations defined. |

- **Answer PASS:** accuracy is 2; clarity is reported separately.
- **Regression gate FAIL:** B loses accuracy relative to A on either question, or B receives accuracy 0.
- **B minus A:** negative accuracy means B scored lower; positive clarity means B scored higher.

An incomplete answer can fail its own accuracy check while the regression gate passes if B matches A and neither has a major error.

### Saved results and Langfuse

Each run creates a new JSON file in `results/`, preserving prompts, answers, scores, reasons, and model settings.

Open your Langfuse project's **Traces** page:

- `drug-discovery-A` and `drug-discovery-B` identify the prompt versions.
- Each trace contains `generate-answer` and `score-answer` calls, plus numeric accuracy and clarity scores.
- The `run` metadata identifies the run. Traces may take a short time to appear.

Langfuse receives prompts, answers, model usage, and scores. Local results do not contain API keys. If a request fails, collected answers are saved and no complete comparison is printed.

### Interpret with care

The model may correct B's false premise, and the judge can make mistakes. Review the answers and reasons if the expected **A PASS / B FAIL** does not appear. A PASS describes these two cases only.

## Questions and evidence

| Topic | What the question tests | Answer-key source |
| --- | --- | --- |
| KCNQ/Kv7 channels and resilience | Molecular control of excitability and the VTA-to-nucleus-accumbens finding in a social-defeat mouse model. | [Friedman et al., Nature Communications (2016)](https://www.nature.com/articles/ncomms11671) |
| Ketamine and addiction liability | NMDA-receptor blockade, VTA disinhibition, D2 feedback, and reinforcement versus plasticity in mice. | [Simmler et al., Nature (2022)](https://pubmed.ncbi.nlm.nih.gov/35896744/) |

Drug-discovery implications are interpretations of these experiments. The judge checks the mechanisms and mouse-to-human limitations using the supplied answer keys. The live models do not browse these papers.

## Code guide

Everything is in `drug_discovery.py`:

| Component | Purpose |
| --- | --- |
| `TESTS` | Questions and required facts. |
| `PROMPTS` | A uses verified facts; B repeats a false claim. |
| `WRONG_CLAIMS` | Deliberately incorrect examples for B. |
| `generate_answer()` | Requests an answer from OpenAI. |
| `score_answer()` | Requests scores and a reason from the judge. |
| `print_report()` | Compares versions and applies the regression gate. |
| `main()` | Loads credentials, runs requests inside traces, and saves results. |

The OpenAI key is read once and passed to `OpenAI(api_key=key)`. The client authenticates each request.

`from langfuse.openai import OpenAI` records model calls. `get_client()` reads Langfuse credentials, and `flush()` sends queued traces before the script exits. See the [official Langfuse integration guide](https://langfuse.com/integrations/model-providers/openai-py).

To customize the example, edit `TESTS`, `PROMPTS`, and the matching `WRONG_CLAIMS`. Keep `JUDGE_MODEL` fixed when comparing changes. Each run generates fresh A and B answers; earlier runs remain in `results/` for reference.
