# CrimeScope

**AI-powered crime investigation simulation platform with multi-agent systems and graph-based evidence linking.**

---

## 🎯 Overview

CrimeScope is a next-generation platform for crime investigation analysis powered by LLM-driven multi-agent systems. It combines graph-based evidence analysis, interactive case simulations, and intelligent report generation to support investigative workflows and scenario analysis.

### Core Features

- **Case Management** — Create, track, and analyze criminal cases with rich metadata
- **Evidence Linking** — Graph-based relationship mapping between suspects, evidence, and events
- **Multi-Agent Simulation** — Simulate investigation scenarios with independent agent perspectives
- **LLM Integration** — Powered by OpenRouter (gpt-4o-mini) for intelligent analysis
- **Interactive UI** — Vue 3 frontend with real-time graph visualization
- **REST API** — Production-grade Flask backend with modular architecture

---

## 🛠 Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Frontend** | Vue 3 + Vite | 3.x |
| **Backend** | Flask | 3.x |
| **Language** | Python | 3.11–3.12 |
| **Runtime** | Node.js | 18+ |
| **LLM Provider** | OpenRouter | gpt-4o-mini |
| **Memory Store** | Zep Cloud | (optional) |
| **Package Manager** | npm / uv | Latest |

---

## 🚀 Quick Start

### Prerequisites

```bash
node -v        # Node.js 18+
python --version  # Python 3.11–3.12
uv --version   # uv package manager
```

### 1. Clone & Install

```bash
git clone https://github.com/SAICHARAN-TEJ/CRIMESCOPE.git
cd CRIMESCOPE

# Install all dependencies
npm run setup:all
```

### 2. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env with your credentials
```

**Required variables:**
```env
LLM_API_KEY=your_openrouter_key
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL_NAME=openai/gpt-4o-mini
ZEP_API_KEY=your_zep_api_key  # Optional
```

### 3. Run Services

```bash
# Start frontend + backend together
npm run dev
```

**Service URLs:**
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`
- Health Check: `GET /api/system/health`

**Start individually:**
```bash
npm run frontend   # Vue 3 dev server
npm run backend    # Flask API server
```

### 4. Verify Setup

```bash
# Check backend readiness (all configs loaded)
curl http://localhost:5001/api/system/readiness

# View service metadata
curl http://localhost:5001/api/system/info
```

---

## 📁 Project Structure

```
CRIMESCOPE/
├── backend/                  # Flask API server
│   ├── app/
│   │   ├── __init__.py      # App factory
│   │   ├── config.py        # Config management
│   │   └── api/             # Blueprint routes
│   │       ├── system.py    # Health/readiness endpoints
│   │       ├── crimescope.py # Case management
│   │       ├── graph.py     # Evidence relationships
│   │       ├── simulation.py # Agent simulations
│   │       └── report.py    # Report generation
│   ├── tests/               # Pytest suite
│   ├── run.py               # Entry point
│   └── pyproject.toml       # Dependencies
│
├── frontend/                # Vue 3 + Vite
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   └── components/
│   └── package.json
│
├── website/                 # Documentation site (optional)
├── .env.example            # Config template
└── package.json            # Root scripts
```

---

## 📋 API Reference

### System Endpoints

```bash
# Health check (liveness)
GET /api/system/health

# Service metadata
GET /api/system/info

# Environment readiness validation
GET /api/system/readiness
```

### Case Management

```bash
# List all cases
GET /api/crimescope/cases

# Create new case
POST /api/crimescope/cases

# Get case details
GET /api/crimescope/cases/<case_id>

# Update case
PUT /api/crimescope/cases/<case_id>
```

### Graph & Evidence

```bash
# Get case graph
GET /api/graph/cases/<case_id>

# Add evidence node
POST /api/graph/evidence

# Link evidence
POST /api/graph/link
```

---

## 🧪 Testing

```bash
# Run all tests
npm run test

# Run backend tests only
npm run test:backend

# Run with coverage
npm run test:coverage
```

---

## 🐳 Docker Deployment

```bash
# Build and start containers
docker compose up -d

# Check logs
docker compose logs -f
```

Services run at:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:5001`

---

## 📚 Development

### Scripts (from root)

```bash
npm run dev              # Start frontend + backend
npm run frontend         # Frontend dev server only
npm run backend          # Backend dev server only
npm run setup:all        # Install all dependencies
npm run test             # Run all tests
npm run lint             # Lint JavaScript
npm run build            # Build frontend for production
```

### Backend Development

```bash
cd backend
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv sync
python run.py
```

---

## 🔐 Environment Configuration

See `.env.example` for all available options. Key variables:

| Variable | Purpose | Example |
|----------|---------|---------|
| `LLM_API_KEY` | OpenRouter API key | `sk-or-v1-...` |
| `LLM_BASE_URL` | LLM endpoint | `https://openrouter.ai/api/v1` |
| `LLM_MODEL_NAME` | Model identifier | `openai/gpt-4o-mini` |
| `ZEP_API_KEY` | Memory store token | (optional) |
| `FLASK_DEBUG` | Debug mode | `true` / `false` |

---

## 📝 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Commit changes: `git commit -am 'Add feature'`
3. Push to branch: `git push origin feature/your-feature`
4. Open a Pull Request

---

## 📄 License

See LICENSE file for details.

---

## 🤝 Support

For issues, questions, or contributions:
- Open an issue on [GitHub](https://github.com/SAICHARAN-TEJ/CRIMESCOPE/issues)
- Check existing documentation in this README

---

**Last updated:** April 17, 2026
