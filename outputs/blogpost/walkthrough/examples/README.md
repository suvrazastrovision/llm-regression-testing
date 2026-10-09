# Reviewed public sample

[sample_results.json](sample_results.json) is the newest local result reviewed for this publication: `20261008-162812-120623.json`, started on 8 October 2026 at 16:28:12 UTC. The original answers, prompts, AI scores, and reasons are preserved unchanged. Earlier runs remain local and are ignored by Git.

**Offline A/B prompt comparison, not a randomized A/B test.** This run uses `demo` mode: A receives reference facts; B is deliberately instructed to produce incorrect claims. The B answers are negative controls, not scientific guidance. Generation and judging both used `gpt-4o-mini`, with one trial per question/version.

| Question | Version | AI accuracy | AI clarity |
| --- | --- | --- | --- |
| KCNQ/VTA | A | 2 | 2 |
| KCNQ/VTA | B | 1 | 2 |
| Ketamine/VTA | A | 2 | 2 |
| Ketamine/VTA | B | 0 | 1 |

The original scores produce a **FAIL** regression gate: B loses accuracy on both questions and has a major error on the ketamine question.

## Review finding

The judge's KCNQ B score is inconsistent with its rubric: reversing retigabine's channel action and firing effect is a major mechanistic error, which should receive accuracy **0**, not **1**. This is documented here without changing the original AI result. The gate still fails either way.

Review covered completeness, credential exposure, and consistency with the supplied rubric and answer keys. AI judgments do not establish scientific reliability or clinical efficacy. Reference studies: [KCNQ/VTA](https://www.nature.com/articles/ncomms11671) and [ketamine/VTA](https://pubmed.ncbi.nlm.nih.gov/35896744/).
