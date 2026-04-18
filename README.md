<div align="center">
  <img src="docs/assets/logo.png" alt="CrimeScope Logo" width="220"/>
  <h1>CrimeScope</h1>
  <p><b>1,000-Agent Swarm Intelligence Engine for Criminal Event Reconstruction</b></p>
  
  [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-red.svg)](https://www.gnu.org/licenses/agpl-3.0)
  [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
  [![Vue 3](https://img.shields.io/badge/vue-3.x-4FC08D.svg)](https://vuejs.org/)
  [![Powered by DeepSeek & Gemini](https://img.shields.io/badge/AI-DeepSeek_|_Gemini-black.svg)]()
</div>

<br />


---

## 👁‍🗨 The Platform

**CrimeScope** is an advanced swarm intelligence platform designed to reconstruct complex timelines and detect contradictions in criminal investigations. Rather than relying on a single LLM call, CrimeScope spins up an adversarial, 1,000-agent swarm divided into 8 distinct cognitive archetypes. 

Agents analyze parsed evidence, develop independent causal chains, cross-examine each other for contradictions, and ultimately converge on the statistical truth using a Bayesian Probable Cause Engine.

<div align="center">
  <img src="docs/assets/home.webp" alt="CrimeScope Dashboard" width="100%"/>
</div>

---

## 🔬 Core Mechanics

CrimeScope operates across 3 main ingestion modes:

1. **Photo Evidence**: Gemini 2.5 Pro conducts multi-pass forensic analysis of crime scene imagery, extracting blood spatter patterns, anomalies, and spatial relationships.
2. **Document & Video**: A 3-pass extraction pipeline processes transcripts and police reports to build a highly structured semantic timeline.
3. **Demo Case**: One-click launch simulating investigating the "Harlow Manor" locked-room mystery.

### The 1,000-Agent Swarm

A single "Agent" is rarely unbiased. CrimeScope deploys an entire precinct:

| Archetype | Count | Cognitive Role |
|-----------|-------|----------------|
| **Suspect Persona** | 200 | Maps deceptive reasoning and plausible perpetrator actions. |
| **Eyewitness Simulator** | 150 | Models observation errors, blind spots, and cognitive biases. |
| **Statistical Baseline** | 130 | Evaluates base-rate crime statistics and demographic priors. |
| **Forensic Analyst** | 120 | Focuses purely on physical evidence and trace analysis. |
| **Scene Reconstructor** | 120 | Evaluates spatial geometry and temporal action sequencing. |
| **Contradiction Detector** | 100 | Hunts exclusively for semantic inconsistencies across agent drafts. |
| **Behavioral Profiler** | 100 | Maps psychological intent, victimology, and motive. |
| **Alibi Verifier** | 80 | Cross-checks claimed timelines against physical constraints. |

Over 30 simulation rounds, the agents test hypotheses, logging contradictions and updating their beliefs.

<div align="center">
  <img src="docs/assets/graph_interaction.webp" alt="Dynamic Knowledge Graph" width="80%"/>
  <br/>
  <em>Every semantic entity and contradiction is mapped into a Neo4j Knowledge Graph in real-time.</em>
</div>

---

## 📊 Probable Cause Engine

Once the simulation rounds complete, the Bayesian **Probable Cause Engine** filters 1,000 localized causal chains down into a deterministic final report. 

<div align="center">
  <img src="docs/assets/report_demo.webp" alt="Probable Cause Report" width="100%"/>
</div>

The final report provides:
- **Consensus Score:** The swarm's overall certainty.
- **Top Hypotheses:** Weighted by supporting physical evidence and minimal contradictions.
- **Dissent Log:** Hard-coded minority opinions. Users can directly interrogate dissent streams via an integrated Chat interface to ask *why* 5% of agents believed a different timeline.

---

## 🏗 System Architecture

```text
┌─────────────────────────────────────────────────────┐
│                   Vue 3 Frontend (:3000)             │
│   Mode Selection → Simulation Panel → Report View    │
├─────────────────────────────────────────────────────┤
│                  FastAPI Backend (:5001)              │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────┐ │
│  │ Pipeline  │  │   Swarm    │  │  Probable Cause  │ │
│  │ (Vision + │→ │  Manager   │→ │     Engine       │ │
│  │  Document)│  │ 1000 agents│  │  Bayesian voting │ │
│  └──────────┘  └────────────┘  └──────────────────┘ │
│       ↕              ↕                ↕             │
│  ┌─────────┐  ┌───────────┐  ┌──────────────┐       │
│  │ ChromaDB │  │   Neo4j   │  │     mem0     │       │
│  │ Vectors  │  │   Graph   │  │ Agent Memory │       │
│  └─────────┘  └───────────┘  └──────────────┘       │
├─────────────────────────────────────────────────────┤
│            Marketing Website (:80)                   │
│         GSAP 3 · Light Theme · 10 Sections           │
└─────────────────────────────────────────────────────┘
```

### Free-Tier LLM Routing Strategy
All calls route through an OpenRouter integration, maximizing reasoning without requiring enterprise credits:
- **`deepseek/deepseek-v3:free`** — Primary volume logic and agent voting.
- **`deepseek/deepseek-r1:free`** — Deep chain-of-thought analysis for Behavioral Profilers.
- **`meta-llama/llama-3.3-70b:free`** — Ultra-fast fact-checking and contradiction detection.
- **`google/gemini-2.5-pro:free`** — Top tier multi-modal vision extraction.

---

## ⚙️ Quick Start Installation

CrimeScope utilizes a highly customized Docker-compose orchestration for its multi-service backend. 

### 1. Requirements
* Docker & Docker Compose
* An OpenRouter API Key (Free tier works perfectly)
* Node.js 18+ (for local frontend dev)

### 2. Setup

```bash
# Clone the repository
git clone https://github.com/SAICHARAN-TEJ/CRIMESCOPE.git
cd CRIMESCOPE

# Copy the environment file
cp .env.example .env
```

**Open your `.env` file** and add your OpenRouter Key:
```env
LLM_API_KEY=your_openrouter_api_key_here
```

### 3. Launch

```bash
# Boot the entire infrastructure
docker compose up -d
```

### 4. Access Services

* **CrimeScope Investigators Dashboard**: `http://localhost:3000`
* **Marketing & Landing Page**: `http://localhost:80`
* **FastAPI Backend Swagger**: `http://localhost:5001/docs`
* **Neo4j Browser**: `http://localhost:7474` *(Auth defined in .env)*

---

## 🛡️ License

CrimeScope is licensed under the **AGPL-3.0 License**.

> This software is fully open-source. Every model call, every adversarial prompt, and every inference step is entirely auditable. **There are no black boxes in criminal investigation.**
