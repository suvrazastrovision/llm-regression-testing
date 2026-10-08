# LLM Regression Testing

This tutorial demonstrates how regression testing can flag factual errors and hallucinations in AI-generated scientific explanations.
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

Use `--mode comparison` to compare two realistic prompts instead. A is a basic scientific-answer prompt; B asks explicitly for mechanisms, defined abbreviations, uncertainty, and limits of human translation. Neither receives the answer key or deliberately false claims. Edit `COMPARISON_PROMPTS` to evaluate your own baseline and candidate. The default remains `--mode demo`.

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

Each complete default run makes **four answer requests and four judge requests**. API usage is billed to your OpenAI API account. SDK retries can add attempts.

For a realistic comparison with three independent trials per question and version:

```powershell
.\.venv\Scripts\python.exe drug_discovery.py --mode comparison --repeats 3
```

This makes twelve answer requests and twelve judge requests. `--repeats` must be a positive integer; its default is 1. A/B execution order alternates across questions and trials.

## Read the results

### Scores and pass/fail rules

| Score | Accuracy | Clarity |
| --- | --- | --- |
| 0 | Major error, contradiction, refusal, or no relevant answer. | Confusing. |
| 1 | Correct but incomplete. | Understandable with unexplained technical terms. |
| 2 | All required facts without contradictions. | Clear scientific reasoning with essential abbreviations defined. |

- **Answer PASS:** accuracy is 2; clarity is reported separately.
- **Regression gate FAIL:** B's mean accuracy is lower than A's on either question, or any B trial receives accuracy 0. With one trial, this matches the original rule.
- **B minus A:** negative accuracy means B scored lower; positive clarity means B scored higher.

An incomplete answer can fail its own accuracy check while the regression gate passes if B matches A and neither has a major error.

Process exit codes are **0** for a passing gate, **2** for a failed gate, and **1** for configuration, request, response-validation, or file errors. Invalid command-line arguments also exit with 2, following Python's argument-parser convention. A failed gate exits with 2 even in the deliberate-error demo, where detecting a failure is expected. CI can use the nonzero code to reject a candidate.

### Saved results and Langfuse

The [reviewed public sample](examples/README.md) contains the latest published result and review notes. Other runs stay in the Git-ignored `results/` folder.

Each run creates a new JSON file in `results/`, preserving prompts, answers, scores, reasons, model names, mode, and trial numbers. The file remains a list of answer records.

Open your Langfuse project's **Traces** page:

- `drug-discovery-A` and `drug-discovery-B` identify the prompt versions.
- Each trace contains `generate-answer` and `score-answer` calls, plus numeric accuracy and clarity scores.
- The `run`, `mode`, and `trial` metadata identify the run and individual trials. Traces may take a short time to appear.

Langfuse receives prompts, answers, model usage, and scores. Local results do not contain API keys. If a request fails, collected answers are saved and no complete comparison is printed.

Truncated or content-filtered judge responses produce a diagnostic and exit code 1; they are not treated as valid scores.

### Interpret with care

The model may correct B's false premise, and the judge can make mistakes. Review the answers and reasons if the expected **A PASS / B FAIL** does not appear. A PASS describes these two cases only.

Repeated trials expose variation, but the mean-based gate is a policy rule, not a statistical significance test. Both modes still cover only two questions. The default answer and judge models are the same; set `JUDGE_MODEL` explicitly when evaluating an independent judge and keep it fixed across comparisons.

Before relying on the gate for scientific decisions, broaden the question set and have a qualified reviewer independently score representative correct, incomplete, and incorrect answers. Compare those human labels with the judge's scores, including individual disagreements. No human calibration or scientific validation is claimed by this repository's offline tests.

## Offline tests

The test suite uses Python's standard-library `unittest` and mocked model and tracing clients. It does not read your credentials, make API calls, or upload traces.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

It checks gate decisions and exit codes, repeated-trial aggregation, invalid and incomplete results, response validation, partial-answer preservation, judge parsing errors, and trace-flush failures.

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
| `COMPARISON_PROMPTS` | Realistic baseline and candidate prompts, without supplied answer keys. |
| `WRONG_CLAIMS` | Deliberately incorrect examples for B. |
| `generate_answer()` | Requests an answer from OpenAI. |
| `score_answer()` | Requests scores and a reason from the judge. |
| `print_report()` | Validates complete trials, reports scores, and returns a structured gate result. |
| `main()` | Loads credentials, runs requests inside traces, and saves results. |

The OpenAI key is read once and passed to `OpenAI(api_key=key)`. The client authenticates each request.

`from langfuse.openai import OpenAI` records model calls. `get_client()` reads Langfuse credentials, and `flush()` sends queued traces before the script exits. See the [official Langfuse integration guide](https://langfuse.com/integrations/model-providers/openai-py).

To customize the demo, edit `TESTS`, `PROMPTS`, and the matching `WRONG_CLAIMS`. For realistic comparisons, edit `TESTS` and `COMPARISON_PROMPTS`. Keep `JUDGE_MODEL` fixed when comparing changes. Each run generates fresh A and B answers; earlier runs remain in `results/` for reference.
