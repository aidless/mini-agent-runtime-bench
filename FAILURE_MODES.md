# Failure modes

This file is the boundary of the scripted flip-rate result. The numbers live only in the README measured block, which `make check` recomputes. This page does not restate them.

## Scripted-policy ceiling

`correct`, `seed_perturbed`, and `flaky` are Python functions in `tools/scripted_policies.py`. They execute the frozen `spec` and do not read `task_text`. A zero flip count means the function returned the same verdict on the baseline and on the single repeat. For `seed_perturbed` that shared verdict is failure, because the fixed seed corrupts the answer on both runs. Nothing here is an LLM agent, and nothing here is evidence that an agent can follow the task text.

`flaky` alternates by run index by construction. Its nonzero flip count shows that the metric moves when the verdict changes. It is not a sample of stochastic decoding.

## Tiny task set

The frozen set is a handful of hand-authored arithmetic and string operations in `snapshots/w1/tasks.jsonl`. The COPY is hashed in `snapshots/w1/manifest.json`. The tasks were written in this repository. They were not copied from a public benchmark, and they are not a sample of agent work. A different task set can change both verdicts and flip counts.

## Flip-rate definition sensitivity

The recorded definition is one repeat and an exact string match against the frozen gold answer. Flip means the replay verdict differs from the baseline verdict. A tolerance, a different judge, more repeats, or a phase switch would be a different measurement. The phase-switch axis and an independent judge are still `TBD`. Exact match is not that independent judge: the gold string is produced from the same spec the policy executes.

The header-only file `results/flip_rate_empty.csv` is a zero-evidence sentinel. It must not be read as a flip rate of zero. Counts come from `results/flip_rate.csv`, and only when each row's trace ids resolve into `results/scripted_traces.jsonl`.

## Docker dependency

`R6` and the container step of `R7` run only when the local Docker daemon is up and `DEFAULT_IMAGE` in `tools/docker_sandbox.py` is already present. `make check` does not pull that image. A missing daemon or a missing image prints `SKIP` plus the reason. A skip is not a pass and is not evidence of isolation. `REQUIRE_DOCKER=1` turns the skip into a failure. The image is large and is a supply-chain dependency; this repository does not vendor it.

`results/w2_runs.jsonl` is a separate, older trace file. It includes wall-clock latencies and a digest of the `tools/` directory, so regenerating it changes bytes. `make check` does not treat it as an input to the flip rate.

## GitHub About

The GitHub About text is not in this repository, so `make check` cannot recompute it. If it still says the project is an LLM-agent runtime benchmark, it disagrees with this tree.

Replacement text:

```
Scripted-policy flip rate on a tiny frozen task set. Not an LLM-agent benchmark.
```
