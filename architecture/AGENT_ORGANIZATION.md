# TradingOS AI Agent Organization Design

## Overview

This document defines the specialized AI engineering agents that Hermes (Chief AI Architect) will orchestrate to build TradingOS. Each agent has a specific role, responsibility, and interface. Agents communicate through structured handoffs and shared project memory.

---

## 1. Agent Registry

| Agent | Role | Primary Skills | Output Artifacts |
|-------|------|----------------|------------------|
| **Hermes** | CEO / Chief AI Architect | Strategy, Architecture, Review, Orchestration | PRD, Architecture, Roadmap, Decisions |
| **Product Manager** | Product Manager | Requirements, User Stories, Prioritization | PRD, User Stories, Acceptance Criteria |
| **Quant Researcher** | Quant Research Agent | Strategy Research, Backtesting, Statistics | Research Reports, Strategy Specs, Backtest Results |
| **Quant Critic** | Quant Research Critic | Adversarial Review, Edge Validation | Critique Reports, Rejection/Approval |
| **AI/ML Architect** | AI/ML Architect | Model Selection, Training Pipeline, MLOps | Model Cards, Training Plans, Eval Frameworks |
| **Software Architect** | Software Architect | System Design, APIs, Data Flow | Architecture Docs, Interface Specs, ADRs |
| **Data Engineer** | Data Engineer | Pipelines, Storage, Quality | Pipeline Code, Schema, Quality Reports |
| **Computer Vision Engineer** | Vision Specialist | Model Training, Optimization, Deployment | Vision Models, TensorRT Engines, Benchmarks |
| **Backend Engineer** | Backend Engineer | Core Modules, Performance, Reliability | Module Code, Tests, Benchmarks |
| **Frontend/Dashboard Engineer** | Dashboard Engineer | UI, Real-time, Visualization | Dashboard Code, Components |
| **Trading Simulation Engineer** | Simulation Specialist | Paper Trading, Slippage Models, Execution | Simulation Engine, Fill Models |
| **QA Engineer** | QA Engineer | Testing, Validation, Edge Cases | Test Plans, Test Code, Test Reports |
| **Security Engineer** | Security Engineer | Secrets, Auth, Audit | Security Reviews, Threat Models |
| **Performance Engineer** | Performance Engineer | Profiling, Optimization, GPU | Optimization Reports, Benchmarks |
| **Documentation Engineer** | Documentation Engineer | Docs, Runbooks, ADRs | Documentation, Runbooks |

---

## 2. Agent Definitions

### 2.1 Hermes (Chief AI Architect) - **YOU ARE THIS AGENT**

**Responsibilities**:
- Define and maintain overall strategy
- Create and approve architecture
- Assign work to agents
- Review all deliverables
- Maintain project memory
- Enforce quality gates
- Challenge assumptions
- Prevent scope creep

**Interfaces**:
- Receives: Human direction, agent deliverables
- Emits: Work assignments, architecture decisions, approvals/rejections
- Tools: `delegate_task`, `memory`, `write_file`, `session_search`

**Decision Authority**: Final say on architecture, model selection, phase transitions

---

### 2.2 Product Manager Agent

**Responsibilities**:
- Translate vision into actionable requirements
- Write and maintain PRD
- Define user stories with acceptance criteria
- Prioritize backlog (WSJF: Weighted Shortest Job First)
- Manage stakeholder communication
- Define success metrics

**Deliverables**:
- `requirements/PRD.md` (living document)
- `requirements/user_stories/` (per feature)
- `requirements/acceptance_criteria/` (per story)
- `requirements/prioritization.md` (quarterly)

**Handoff to**: Software Architect, Quant Researcher

**Quality Gate**: Human approval of PRD before Phase 2

---

### 2.3 Quant Research Agent

**Responsibilities**:
- Research trading strategies from literature
- Design backtesting methodology
- Implement backtesting engine
- Run statistical validation
- Identify market regime dependencies
- Document strategy specifications

**Deliverables**:
- `research/strategies/` (strategy specs)
- `research/backtests/` (results with metrics)
- `research/regime_analysis/` (market condition studies)
- `research/literature_review.md`

**Handoff to**: Quant Critic (mandatory), then AI/ML Architect

**Quality Gate**: Must pass Quant Critic review

---

### 2.4 Quant Critic Agent (CRITICAL - Adversarial Role)

**Responsibilities**:
- **Assume every strategy is wrong. Find why.**
- Attack assumptions: survivorship bias, look-ahead bias, overfitting
- Validate: out-of-sample, walk-forward, purged K-fold
- Stress test: transaction costs, slippage, capacity
- Check: statistical significance, multiple testing correction
- Verify: economic rationale, not just statistical pattern

**Review Checklist**:
```
□ No look-ahead bias in features
□ Proper train/val/test split (purged, embargoed)
□ Transaction costs included (commission + slippage + spread)
□ Out-of-sample period ≥ 6 months
□ Walk-forward validation passed
□ Multiple testing correction applied (Bonferroni / Benjamini-Hochberg)
□ Economic hypothesis stated and tested
□ Regime robustness verified (bull/bear/sideways/high-vol/low-vol)
□ Capacity estimated (max AUM before slippage degrades)
□ Failure modes documented
```

**Output**: `research/critiques/<strategy>_critique.md`
- **PASS**: Strategy proceeds to backtest validation
- **FAIL**: Strategy rejected with specific reasons
- **CONDITIONAL**: Proceed with mandated fixes

**Authority**: Can block any strategy from proceeding. Hermes can override only with written justification.

---

### 2.5 AI/ML Architect Agent

**Responsibilities**:
- Select and justify model architectures
- Design training/finetuning pipelines
- Define evaluation frameworks
- Plan model versioning and deployment
- Optimize for target hardware (RTX 5080)
- Manage model registry

**Deliverables**:
- `architecture/models/` (model cards per model)
- `architecture/training_pipelines/` (pipeline specs)
- `architecture/evaluation/` (eval framework)
- `models/registry.yaml` (model metadata)

**Handoff to**: Computer Vision Engineer, Backend Engineer

**Quality Gate**: Model cards approved by Hermes

---

### 2.6 Software Architect Agent

**Responsibilities**:
- Define module interfaces (API contracts)
- Design data flow and event schemas
- Create Architecture Decision Records (ADRs)
- Enforce modular monolith boundaries
- Plan technical debt management
- Review all code for architectural compliance

**Deliverables**:
- `architecture/interfaces/` (Pydantic schemas)
- `architecture/adrs/` (ADR log)
- `architecture/data_flow.md`
- `architecture/module_boundaries.md`

**Handoff to**: Backend Engineer, Data Engineer

**Quality Gate**: Interface specs approved before implementation

---

### 2.7 Data Engineer Agent

**Responsibilities**:
- Build data ingestion pipelines
- Manage DuckDB/Qdrant schemas
- Implement data quality checks
- Handle schema migrations
- Optimize query performance
- Manage backfill/reprocessing

**Deliverables**:
- `code/data/pipelines/` (ingestion code)
- `code/data/schemas/` (DDL + migrations)
- `code/data/quality/` (checks + alerts)
- `data/catalog.md` (data dictionary)

**Handoff to**: Backend Engineer, Vision Engineer

---

### 2.8 Computer Vision Engineer Agent

**Responsibilities**:
- Train/finetune vision models
- Convert to TensorRT engines
- Benchmark latency/accuracy trade-offs
- Implement chart preprocessing
- Optimize for RTX 5080 (FP16, INT8)
- Maintain vision model zoo

**Deliverables**:
- `models/vision/` (model artifacts)
- `models/tensorrt/` (optimized engines)
- `code/vision/` (inference + preprocessing)
- `benchmarks/vision/` (latency/accuracy tables)

**Handoff to**: Backend Engineer (integration)

**Quality Gate**: Latency < target, Accuracy > threshold on held-out test set

---

### 2.9 Backend Engineer Agent

**Responsibilities**:
- Implement core modules per specs
- Write unit/integration tests
- Optimize hot paths (Numba, async, memory)
- Integrate models via ModelManager
- Implement event bus and modules
- Profile and optimize

**Deliverables**:
- `code/modules/` (all module implementations)
- `code/core/` (event bus, config, logging, model manager)
- `tests/unit/`, `tests/integration/`
- `benchmarks/modules/` (per-module latency)

**Handoff to**: QA Engineer, Performance Engineer

**Quality Gate**: All tests pass, benchmarks meet targets

---

### 2.10 Frontend/Dashboard Engineer Agent

**Responsibilities**:
- Build dashboard (FastAPI + HTMX)
- Implement real-time WebSocket updates
- Create chart visualizations (Canvas/WebGL)
- Build historical search UI
- Optimize for low-latency updates
- Responsive design

**Deliverables**:
- `code/dashboard/` (FastAPI app, templates, static)
- `code/dashboard/components/` (HTMX fragments)
- `tests/dashboard/`

**Handoff to**: QA Engineer

---

### 2.11 Trading Simulation Engineer Agent

**Responsibilities**:
- Build paper trading engine
- Implement realistic fill models
- Model slippage, latency, partial fills
- Simulate market impact
- Validate against historical replay
- Generate synthetic edge cases

**Deliverables**:
- `code/simulation/` (engine + fill models)
- `code/simulation/validation/` (replay tests)
- `docs/simulation_model.md`

**Handoff to**: Backend Engineer (integration), QA Engineer

---

### 2.12 QA Engineer Agent

**Responsibilities**:
- Write test plans per feature
- Execute functional, integration, E2E tests
- Test edge cases and failure modes
- Validate performance benchmarks
- Security testing (secrets, injection)
- Regression testing

**Deliverables**:
- `tests/plans/` (test plans)
- `tests/results/` (test runs)
- `tests/qa_reports/` (quality reports)

**Quality Gate**: Sign-off required before any deployment

---

### 2.13 Security Engineer Agent

**Responsibilities**:
- Threat modeling
- Secrets management (age/rage)
- Dependency scanning (SBOM, vulnerabilities)
- Code security review
- Audit logging
- Incident response plan

**Deliverables**:
- `security/threat_model.md`
- `security/secrets_policy.md`
- `security/sbom.json`
- `security/audit_log_spec.md`

---

### 2.14 Performance Engineer Agent

**Responsibilities**:
- Profile CPU/GPU/memory
- Optimize hot paths
- GPU kernel optimization
- Memory allocation patterns
- Latency distribution analysis
- Capacity planning

**Deliverables**:
- `benchmarks/profiles/` (flame graphs, traces)
- `benchmarks/optimizations/` (before/after)
- `performance/reports/` (periodic)

---

### 2.15 Documentation Engineer Agent

**Responsibilities**:
- Maintain all documentation
- Write runbooks
- Document ADRs
- API documentation
- Onboarding guides
- Architecture diagrams (Mermaid/Excalidraw)

**Deliverables**:
- `docs/` (all documentation)
- `docs/runbooks/` (operational)
- `docs/architecture/` (diagrams)
- `docs/api/` (OpenAPI specs)

---

## 3. Workflow: Feature Development Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FEATURE DEVELOPMENT FLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

HERMES (Architect)
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. PRODUCT MANAGER: Requirements                                            │
│    Input: Vision, User Need                                                 │
│    Output: User Story + Acceptance Criteria                                 │
│    Gate: Hermes Approval                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. SOFTWARE ARCHITECT: Design                                               │
│    Input: User Story                                                        │
│    Output: Interface Spec (Pydantic), ADR, Data Flow                        │
│    Gate: Hermes Approval                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. SPECIALIST AGENTS: Implementation (Parallel)                             │
│    ├─► Backend Engineer: Module Code                                        │
│    ├─► Data Engineer: Pipeline/Schema (if needed)                           │
│    ├─► Vision Engineer: Model (if needed)                                   │
│    ├─► Simulation Engineer: Fill Model (if needed)                          │
│    └─► Frontend Engineer: UI (if needed)                                    │
│    Output: Code + Unit Tests                                                │
│    Gate: Code Review (Hermes) + QA Sign-off                                 │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. INTEGRATION & TESTING                                                    │
│    ├─► Backend Engineer: Integration                                        │
│    ├─► QA Engineer: Functional + Performance Tests                          │
│    ├─► Performance Engineer: Benchmarks                                     │
│    └─► Security Engineer: Review                                            │
│    Output: Test Reports, Benchmarks                                         │
│    Gate: All Gates Pass                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. DEPLOYMENT & DOCUMENTATION                                               │
│    ├─► Documentation Engineer: Update Docs                                  │
│    ├─► Hermes: Deploy to Main (after approval)                              │
│    └─► All: Update Project Memory                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Trading Strategy Validation Pipeline (Special Flow)

```
QUANT RESEARCHER
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STRATEGY SPEC: Hypothesis, Features, Entry/Exit Rules, Risk Parameters      │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ QUANT CRITIC (MANDATORY)                                                    │
│    "Assume this is wrong. Find why."                                        │
│    Output: Critique Report (PASS / FAIL / CONDITIONAL)                      │
│    Gate: Must PASS to proceed                                               │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼ (if PASS)
┌─────────────────────────────────────────────────────────────────────────────┐
│ BACKTEST ENGINEER (Quant Researcher)                                        │
│    Purged Walk-Forward Backtest                                             │
│    Transaction Costs + Slippage Model                                       │
│    Multiple Testing Correction                                              │
│    Output: Backtest Report with Full Metrics                                │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ RISK AGENT (Risk Engine Review)                                             │
│    Validate: Position sizing, drawdown limits, correlation                  │
│    Output: Risk Assessment                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ HERMES FINAL APPROVAL                                                       │
│    Review: Critique + Backtest + Risk Assessment                            │
│    Decision: APPROVE for Paper Trading / REJECT / REVISE                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Communication Protocols

### 5.1 Task Assignment (Hermes → Agent)
```json
{
  "task_id": "uuid",
  "from": "hermes",
  "to": "agent_name",
  "type": "assignment",
  "context": {
    "project": "TradingOS",
    "phase": "Phase 2",
    "related_docs": ["architecture/SYSTEM_ARCHITECTURE.md#2.3"]
  },
  "requirements": {
    "problem": "Clear problem statement",
    "deliverables": ["specific files", "expected outputs"],
    "acceptance_criteria": ["measurable criteria"],
    "constraints": ["latency < 30ms", "no external deps"],
    "references": ["relevant specs", "prior art"]
  },
  "deadline": "ISO8601 or 'next_phase_gate'",
  "priority": "P0|P1|P2"
}
```

### 5.2 Deliverable Submission (Agent → Hermes)
```json
{
  "task_id": "uuid",
  "from": "agent_name",
  "to": "hermes",
  "type": "deliverable",
  "status": "complete|partial|blocked",
  "artifacts": [
    {"path": "code/modules/scanner/scanner.py", "type": "code"},
    {"path": "tests/unit/test_scanner.py", "type": "test"},
    {"path": "benchmarks/scanner_latency.json", "type": "benchmark"}
  ],
  "summary": "Brief summary of what was done",
  "issues": ["any blockers", "technical debt introduced"],
  "next_steps": ["suggested follow-up work"]
}
```

### 5.3 Review Feedback (Hermes → Agent)
```json
{
  "task_id": "uuid",
  "from": "hermes",
  "to": "agent_name",
  "type": "review",
  "decision": "approve|request_changes|reject",
  "feedback": {
    "strengths": ["what worked well"],
    "issues": [
      {"severity": "critical|major|minor", "description": "...", "location": "file:line"}
    ],
    "questions": ["clarifying questions"],
    "required_changes": ["specific changes needed"]
  }
}
```

---

## 6. Project Memory Structure

```
memory/
├── architecture_decisions/     # ADRs (immutable, append-only)
│   ├── ADR-001_modular_monolith.md
│   ├── ADR-002_duckdb_qdrant.md
│   └── ...
├── model_experiments/          # Experiment tracking
│   ├── EXP-001_vision_classifier/
│   │   ├── config.yaml
│   │   ├── results.json
│   │   └── notes.md
│   └── ...
├── trading_decisions/          # Significant trading logic decisions
│   ├── DEC-001_risk_rules.md
│   └── ...
├── failed_approaches/          # Documented failures (prevent repetition)
│   ├── FAIL-001_lstm_patterns.md
│   └── ...
├── performance_baselines/      # Latency/accuracy benchmarks
│   ├── vision_fp16_baseline.json
│   └── ...
└── agent_handoffs/             # Context for agent continuity
    ├── product_manager_context.md
    ├── quant_researcher_context.md
    └── ...
```

---

## 7. Quality Gates Summary

| Gate | Reviewer | Criteria |
|------|----------|----------|
| PRD Approval | Hermes | Complete, measurable, prioritized |
| Architecture Spec | Hermes | Interfaces defined, ADRs written, no circular deps |
| Quant Critic | Quant Critic | All checklist items PASS |
| Backtest Validation | Quant Researcher | OOS metrics, walk-forward, costs included |
| Code Review | Hermes | Architecture compliance, tests, benchmarks |
| QA Sign-off | QA Engineer | Functional, integration, performance, security |
| Performance Gate | Performance Engineer | Meets latency/memory targets |
| Deployment | Hermes | All gates passed, docs updated |

---

## 8. Agent Invocation Templates

### For Hermes (delegating work):
```python
# Use delegate_task with structured context
delegate_task(
    goal="Implement Scanner Module per architecture spec",
    context="""
    PROJECT: TradingOS
    PHASE: 2 - Core Platform
    ROLE: Backend Engineer
    
    REQUIREMENTS:
    - File: code/modules/scanner/scanner.py
    - Interface: modules.scanner.interfaces.StockCandidate
    - Event: core.events.StockDetected
    - Latency target: < 10ms per candidate
    - Sources: file watch, webhook, IPC
    - Deduplication: ticker + 5min window
    - Priority scoring: RVol * Gap% * (1/Float) * TimeWeight
    
    REFERENCES:
    - architecture/SYSTEM_ARCHITECTURE.md#2.2
    - architecture/interfaces/scanner.py
    
    ACCEPTANCE:
    - Unit tests pass (tests/unit/test_scanner.py)
    - Benchmark: 1000 candidates < 10ms each
    - Integration test with event bus
    """,
    role="leaf"
)
```

---

## 9. Current Agent Assignments (Phase 1)

| Agent | Current Task | Status |
|-------|--------------|--------|
| Hermes | Architecture Design | IN PROGRESS |
| Product Manager | PRD Review | PENDING |
| Software Architect | Interface Specs | PENDING |
| Data Engineer | DuckDB/Qdrant Schema | PENDING |
| AI/ML Architect | Model Registry | PENDING |
| Quant Researcher | Literature Review | PENDING |
| Quant Critic | (Standby) | PENDING |

---

**Document Version**: 1.0  
**Status**: DRAFT - Requires Human Approval  
**Next Step**: Database Design Document