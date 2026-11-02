
# Vehicle Telemetry Pipeline: Build Plan

Nov 2, 2026 · @David

## Goal and the story it tells

Build a small but production-shaped Python pipeline that ingests simulated vehicle telemetry, validates it, stores it on Google Cloud, and proves its own health with metrics. The target is GM's *Software Engineer, AV Logging and Observability* role (JR-202619953).

The interview story in one line: **"I built message ingestion for healthcare systems (HL7 Lab), then built the same pattern for vehicle telemetry, with the observability and reliability tooling this role owns."**

What each piece proves to the hiring team:

| Piece | Gap it closes on your resume |
| --- | --- |
| Python services with tests | Production Python (their main language) |
| Protobuf messages from a simulated vehicle, plus a public robotics dataset | Robotics / automotive exposure (a basic qualification) |
| Validation, retries, dead-letter handling | Data pipelines, data quality, distributed-system failure modes |
| Metrics, dashboards, 3 SLIs | Observability and reliability (the job title) |
| LLM failure classifier | AI/LLM applied to triage (a stated focus of the role) |
| GCS, BigQuery, GKE | Their actual cloud stack |

Two rules for the whole build:

- **You write the code.** Use Claude or Copilot to explain and review, but every line must be something you can defend in a technical interview. They will ask "why did you do it this way?"
- **Ship in working slices.** Each phase ends with something that runs and is committed. If the interview comes early, you still have a finished, presentable project.

## Architecture

&#91;embedded content: telemetry pipeline · 8 components\]

Frames flow left to right; anything that fails validation drops into dead letters, where the LLM triage tool classifies it.

| Layer | Choice | Why |
| --- | --- | --- |
| Language | Python 3.12, FastAPI | GM's main language; fast to build typed APIs |
| Message format | Protocol Buffers | Common in automotive and robotics; compact and schema-checked |
| Queue | Pub/Sub (emulator locally) | GM runs on Google Cloud; teaches at-least-once delivery |
| Storage | Cloud Storage + BigQuery | Raw data kept for replay; decoded data queryable with SQL |
| Metrics | Prometheus + Grafana | Industry standard, free, runs locally |
| LLM | Any API that supports JSON output | The evaluation matters more than the model |
| Deploy | Docker Compose, then GKE | Local first; Kubernetes once it works |

## Phased plan

Six phases of roughly one week each, at about 10–15 hours a week. **If your interview is under two weeks away, do Phases 1–3 locally plus a light Phase 5** — that alone covers Python, pipelines, observability and LLMs.

### Phase 1 — Message schema and vehicle simulator

The simulator is your fake fleet. Its fault injection is what makes everything later interesting.

- [ ] Set up the repo: Python 3.12, `pyproject.toml`, `pytest`, `ruff`, a `src/` layout
- [ ] Write a `.proto` schema: a `TelemetryFrame` (vehicle\_id, sequence number, timestamp, GPS, speed, IMU) and an `UploadBatch` that wraps many frames
- [ ] Build a CLI simulator: N vehicles, each emitting frames at a set rate along a plausible route
- [ ] Add fault injection flags: drop rate, corrupted bytes, duplicate frames, delayed uploads, clock skew, out-of-range values
- [ ] Record **ground truth**: log which faults were injected into which batches (you will use this in Phase 5)
- [ ] Unit tests for the schema round-trip and each fault type

**Learn:** Protocol Buffers, Python packaging, type hints, pytest fixtures.

### Phase 2 — Ingestion and validation service

This mirrors HL7 Lab: wire format in, typed and validated objects out.

- [ ] A FastAPI endpoint that accepts an `UploadBatch` from the simulator
- [ ] Decode, then validate: required fields, value ranges, timestamp sanity, sequence gaps per vehicle
- [ ] Deduplicate on (vehicle\_id, sequence) so retries are safe (**idempotency**)
- [ ] Route bad records to a dead-letter store with a **reason code**, never silently drop them
- [ ] Structured JSON logging with vehicle\_id and batch\_id on every line
- [ ] Store good frames locally first (DuckDB or Parquet files) so you can iterate fast
- [ ] Tests for every validation rule and the retry path

**Learn:** FastAPI, async Python, idempotency, at-least-once delivery, data-quality checks.

### Phase 3 — Observability and SLIs

The heart of the job title. Spend real time here.

- [ ] Add `prometheus_client` metrics: counters for frames accepted and rejected (labelled by reason), a histogram of end-to-end latency (vehicle timestamp to stored), a gauge of last-seen time per vehicle
- [ ] `docker compose` with the simulator, the service, Prometheus and Grafana
- [ ] Define three SLIs with targets, e.g. **freshness** (99% of frames stored within 60 s), **validity** (≥ 99.5% of frames pass validation), **completeness** (≥ 99% of expected sequence numbers arrive per vehicle per hour)
- [ ] One Grafana dashboard per question: Is the fleet healthy? Which vehicles are failing? Why?
- [ ] One alert rule, and a one-page runbook for it
- [ ] Turn up the fault rates and watch the dashboard catch it; take screenshots

**Learn:** metric types, PromQL, SLIs vs SLOs, alerting on symptoms not causes.

### Phase 4 — Google Cloud

Move the pipeline onto GM's stack.

- [ ] Put Pub/Sub between ingestion and a separate writer worker (decouples receiving from storing)
- [ ] Write raw batches to Cloud Storage, partitioned by date and vehicle
- [ ] Load decoded frames into a BigQuery table partitioned by date; rejected records into a quality table
- [ ] Write 3–4 SQL queries you can demo: gaps per vehicle, rejection rate by reason, latency percentiles
- [ ] Optional: Terraform for the bucket, topic and dataset

**Learn:** Pub/Sub delivery semantics, BigQuery partitioning and cost, service accounts and IAM.

### Phase 5 — LLM failure triage

The standout piece. Keep it small and measurable.

- [ ] Group dead-letter records and error logs by signature (reason code + message pattern)
- [ ] Send a sample from each group to an LLM with a fixed set of labels (corrupt payload, clock skew, dropped sequence, upload delay, schema mismatch, unknown) and require JSON output
- [ ] **Score it against the Phase 1 ground truth** and report accuracy — this is what most candidates never do
- [ ] Generate a short markdown incident summary: what failed, which vehicles, likely cause, suggested next step

**Learn:** structured LLM output, prompt design, evaluating an LLM against labelled data.

### Phase 6 (bonus) — Real robotics data, Kubernetes, CI

- [ ] Write an adapter that reads a public driving or robotics log (an MCAP file or a public dataset) and replays it through your pipeline as telemetry
- [ ] Deploy the service and worker to GKE with Deployments and a Service; add readiness and liveness probes
- [ ] GitHub Actions: lint, tests and a container build on every push
- [ ] Record a 3–5 minute demo video, then **tear the cluster down**

**Learn:** Kubernetes basics, health probes, CI pipelines, robotics log formats.

## Cost and setup

Phases 1–3 run entirely on your laptop and cost nothing. Phases 4–6 should stay in the low tens of dollars if you clean up after yourself.

- **Set a billing budget alert first** (e.g. $20) in the Google Cloud console before creating anything.
- Pub/Sub, Cloud Storage and BigQuery all have free usage tiers that a project this size should fit inside. Check current limits on Google's pricing pages, since they change.
- **GKE is the one real cost.** Nodes bill by the hour. Spin the cluster up, record your demo, and delete it the same day.
- LLM API calls for Phase 5 should cost a few dollars at most. Cache responses while you iterate so you are not paying for the same prompt twice.
- Keep secrets out of the repo: use a `.env` file listed in `.gitignore`, and a service account with only the roles it needs.
- Local tools: Docker Desktop, the `gcloud` CLI, and the Pub/Sub emulator so you can test Phase 4 without touching the cloud.

## Presenting it

The repo is only half the value; the other half is being able to talk about the decisions.

**README, in this order:** one-paragraph summary, the architecture diagram, a dashboard screenshot, the three SLIs with their targets, how to run it in one command, design decisions and tradeoffs, what you would do next at fleet scale. Link the demo video at the top.

**Write a short design doc** (`docs/design.md`): the problem, the alternatives you rejected and why. GM explicitly asks for people who lead design reviews; this is your evidence.

**Questions to rehearse answers for, using your own project:**

1. A vehicle's data stops showing up in BigQuery. Walk me through how you would find out why.
2. Why did you deduplicate on (vehicle\_id, sequence)? What happens if a vehicle reboots and resets its counter?
3. Why these three SLIs? What would you alert on, and what would you only show on a dashboard?
4. Pub/Sub delivers at least once. Where does that matter in your pipeline?
5. How would this design change at 10,000 vehicles uploading terabytes a day?
6. How do you know your LLM classifier is any good? When would you not trust it?
7. What privacy issues does GPS telemetry raise, and how would you handle them? (Tie this to your healthcare compliance background.)

**Draft resume entry** (edit once it is real):

*Vehicle Telemetry Pipeline* — Python, Protobuf, FastAPI, Pub/Sub, BigQuery, Prometheus, Grafana, GKE

- Built a fault-tolerant ingestion pipeline for simulated vehicle telemetry with validation, deduplication and dead-letter routing.
- Defined freshness, validity and completeness SLIs with Prometheus and Grafana dashboards and alerting.
- Built an LLM failure classifier for pipeline errors, scored at X% accuracy against injected-fault ground truth.

## Learning resources

Read these alongside the phase that needs them, not all up front.

| Phase | Resource | Why |
| --- | --- | --- |
| 1 | [Protocol Buffers Python tutorial](https://protobuf.dev/getting-started/pythontutorial/) | Schema, code generation, serialization |
| 2 | [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/) | Your ingestion endpoint |
| 2, 4 | *Designing Data-Intensive Applications* (Kleppmann), chapters on encoding and stream processing | The distributed-systems vocabulary interviewers use |
| 3 | [Google SRE book: Service Level Objectives](https://sre.google/sre-book/service-level-objectives/) | How Google itself defines SLIs and SLOs |
| 3 | [Prometheus Python client](https://github.com/prometheus/client_python) | Counters, histograms, gauges |
| 4 | Google Cloud quickstarts for Pub/Sub, Cloud Storage and BigQuery | Setup and IAM basics |
| 6 | [MCAP](https://mcap.dev/) | The log format widely used for robotics data |

**Checkpoints:** at the end of each phase, explain what you built out loud in two minutes, as if to an interviewer. If you stumble on a "why," that is the thing to study before moving on.
