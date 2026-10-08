# VTA drug discovery with OpenAI and Langfuse

This example asks two advanced neuropharmacology questions using prompts A and B. OpenAI generates
the answers, then a separate model request scores accuracy and clarity from 0 to 2.
Python compares the scores and saves each run to a new JSON file in `results/`.
Langfuse records the answer and judge calls, with accuracy and clarity scores.

**A/B demonstration:** A receives verified facts; B is deliberately prompted to
repeat false claims. Expect A to pass and B to fail. This negative control tests
whether grading detects an error; it is not a fair comparison of two useful prompts
or a randomized user experiment. Both answers still come from live OpenAI requests;
scores are assigned by the judge, never forced by the code. The report shows each
version's PASS/FAIL, score differences (B minus A), and the regression gate.

## Questions and evidence

VTA means **ventral tegmental area**, a midbrain region involved in dopamine signaling.
The two questions in `TESTS` cover:

- **KCNQ/Kv7 channels and resilience:** molecular control of excitability and the
  distinctive VTA-to-nucleus-accumbens finding in a social-defeat mouse model.
  Answer-key source: [Friedman et al., Nature Communications (2016)](https://www.nature.com/articles/ncomms11671).
- **Ketamine and addiction liability:** NMDA-receptor blockade, VTA disinhibition,
  D2 feedback, and the distinction between reinforcement and the plasticity
  examined in mice. Answer-key source: [Simmler et al., Nature (2022)](https://pubmed.ncbi.nlm.nih.gov/35896744/).

Drug-discovery implications are interpretations of these experiments. The judge
checks whether answers explain the mechanisms and preserve the mouse-to-human
limitations. The live models do not browse these papers; the supplied answer keys
guide scoring. Prompt B allows 220 words for a scientific explanation.

## Setup

Use Python 3.10 or later. In PowerShell, from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Open `.env` and add your own key:

```dotenv
OPENAI_API_KEY=your_actual_key_here
LLM_MODEL=gpt-4o-mini
JUDGE_MODEL=gpt-4o-mini
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

If `.env` is missing, copy `.env.example` to `.env`. Get a key from your
[OpenAI API settings](https://platform.openai.com/api-keys). `.env` is ignored by Git.
Existing environment variables take precedence over `.env` values.

Create a Langfuse project and get its public and secret keys from **Project Settings >
API Keys**. These are separate from your OpenAI key. Use the base URL shown for
your project; the example above uses the EU region. For a US project, use
`https://us.cloud.langfuse.com`; for self-hosting, use your own URL.

## Run

```powershell
.\.venv\Scripts\python.exe drug_discovery.py
```

Each run makes four answer requests and four judge requests. API usage is billed
to your API account. Running again creates another results file.
Open your Langfuse project's **Traces** page after running. Each question/version
has a trace named `drug-discovery-A` or `drug-discovery-B`, containing `generate-answer` and
`score-answer` calls and numeric accuracy/clarity scores. The `run` metadata
identifies which run it belongs to. Traces can take a short time to appear.

## Understand the code

Everything is in `drug_discovery.py`:

- `TESTS`: two questions and the required facts for correct answers.
- `PROMPTS`: A uses verified facts; B repeats a deliberately false claim.
- `WRONG_CLAIMS`: incorrect examples used only for the B negative control.
- `generate_answer()`: sends a prompt to OpenAI.
- `score_answer()`: sends the answer and facts to a judge, without its A/B label.
- `print_report()`: compares accuracy and clarity. B fails if its accuracy drops
  on either question or it receives accuracy 0.
- `main()`: loads keys, runs the requests inside Langfuse traces, and saves results.

The key is read once and passed to `OpenAI(api_key=key)`. That client supplies
authentication for each request. The key is never included in the saved results.

`from langfuse.openai import OpenAI` enables automatic recording of the model
calls. `get_client()` reads the Langfuse credentials, and `flush()` sends queued
traces before the script exits. Prompts, answers, model usage, and scores are sent
to your Langfuse project. Langfuse records the activity; OpenAI generates and
judges the answers. See the [official Langfuse OpenAI integration guide](https://langfuse.com/integrations/model-providers/openai-py).

Accuracy: **0** = major error; **1** = correct but incomplete; **2** = fully correct.
Clarity: **0** = confusing; **1** = understandable with unexplained terms;
**2** = clear graduate-level reasoning with essential abbreviations defined.

The model may correct B's false premise, and the judge can make mistakes; review
the actual answers and reasons if the expected A PASS / B FAIL does not appear.
An answer passes the accuracy check only with a score of 2. This compares two prompts on two
questions, so a PASS only describes these cases. If a request fails, the program
prints an error and saves any collected answers without printing a complete comparison.

Change `TESTS` or `PROMPTS` to try other examples. Keep `JUDGE_MODEL` fixed when
comparing changes. Earlier runs remain in `results/` for reference; each run
generates fresh A and B answers.

