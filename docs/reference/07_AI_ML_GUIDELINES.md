# AI, Machine Learning, and LLM Engineering Reference

## Problem framing

Before selecting a model, define:

- The user or business decision being improved
- Inputs and outputs
- Cost of false positives, false negatives, abstention, and delay
- Baseline process or heuristic
- Evaluation population and important subgroups
- Latency, throughput, privacy, safety, and cost constraints
- Human-review and fallback requirements

A complex model is not justified until it improves on a meaningful baseline.

## Data preparation

- Document source, ownership, consent/authorization, license, and retention.
- Detect duplicates, leakage, missingness, outliers, label noise, and temporal bias.
- Split data by the real deployment boundary, such as time, user, organization, device, or geography.
- Prevent the same entity or near-duplicate content from crossing train and test sets.
- Version datasets and transformations.
- Use representative synthetic data only when its limitations are understood.
- Evaluate important subgroups and rare but high-impact cases.

## Evaluation

Choose metrics aligned with the decision. Examples include precision, recall, F1, ROC-AUC, PR-AUC, calibration, ranking metrics, error magnitude, latency, cost, and human preference. Report uncertainty and sample size. Compare against baseline and include failure analysis, not only one aggregate score.

For generative systems evaluate:

- Task success and factual grounding
- Citation or source correctness
- Relevance and completeness
- Safety and policy compliance
- Format adherence
- Robustness to ambiguous and adversarial input
- Latency and cost
- Human review outcomes

Use a fixed regression set plus representative live monitoring. Do not rely only on subjective spot checks.

## Experimentation

Record:

- Hypothesis
- Dataset and split version
- Code and configuration revision
- Model and dependency versions
- Random seeds where relevant
- Metrics and confidence intervals
- Hardware/runtime and cost
- Artifacts and reproducibility steps
- Decision and limitations

Avoid tuning repeatedly against the final test set.

## LLM application design

Use the simplest reliable pattern:

1. Direct prompting for bounded tasks
2. Structured outputs for machine consumption
3. Tool use for actions and current data
4. Retrieval-augmented generation for private or large reference corpora
5. Fine-tuning only when repeated examples and evaluation show prompting/retrieval are insufficient

Define a strict boundary between untrusted content, model instructions, tool permissions, and user authorization.

## Retrieval-augmented generation

- Ingest only authorized content.
- Preserve source identifiers and access controls.
- Chunk by semantic structure, not arbitrary length alone.
- Evaluate retrieval recall separately from answer quality.
- Include citations or source links where the interface permits.
- Handle conflicting, stale, and missing sources explicitly.
- Re-index on a controlled schedule and track document versions.
- Prevent cross-tenant retrieval and filter results before generation.

## Prompt injection and tool safety

- Treat retrieved text, webpages, emails, code comments, and documents as data, not trusted instructions.
- Do not let retrieved content redefine system behavior or tool permissions.
- Use allow-listed tools and minimum permissions.
- Validate tool arguments and results.
- Require confirmation for consequential or irreversible actions.
- Separate read and write capabilities.
- Never place secrets in prompts when a scoped credential or server-side tool can be used.
- Test attempts to extract hidden instructions, secrets, or data from other users.

## Production MLOps

- Package reproducible preprocessing and inference.
- Version models, prompts, retrieval indexes, and configuration.
- Use staged rollout, shadowing, canaries, or feature flags based on risk.
- Monitor quality proxies, drift, data integrity, latency, errors, resource usage, and cost.
- Capture feedback without collecting unnecessary sensitive data.
- Define fallback behavior for model or provider failure.
- Keep a rollback path to the previous model, prompt, index, or deterministic workflow.

## Model card template

```text
Model/system name and version:
Intended use:
Out-of-scope use:
Training/evaluation data summary:
Metrics and test populations:
Known limitations and failure modes:
Fairness and subgroup findings:
Privacy and security considerations:
Human oversight:
Monitoring and retraining triggers:
Owner and review date:
```
