# AutoAnalyst AI

**Your Autonomous Data Analyst** — *Powered by Saniya.*

AutoAnalyst AI is a full-stack, GenAI-powered SaaS platform designed to transform raw datasets into interactive dashboards and automated business insights.

This repository contains the completed **Phase 1 Foundation**:
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, and Lucide React.
- **Theme Engine**: Adaptive dark/light theme with automatic OS preference sync and persistent storage.
- **Backend API**: Python FastAPI with Pydantic Settings, dynamic CORS configuration, and health check monitoring.
- **Full-Stack Connectivity**: Real-time frontend API service monitoring FastAPI status with live status indicator.
- **Modular Architecture**: Clean separation into `components/`, `pages/`, `context/`, `hooks/`, `services/`, and `types/`.

---

## Prerequisites
- **Node.js**: v20+ (tested with v22.21.0)
- **Python**: 3.10+ (tested with 3.10.11)
- **Git**
- **PowerShell** (Windows) or Bash (macOS/Linux)

---

## Quickstart Guide

### 1. Backend Setup (FastAPI)

In a PowerShell terminal:

```powershell
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
# (If execution policies block activation: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)

# Install dependencies
pip install -r requirements.txt

# Copy environment template
Copy-Item .env.example .env

# Start FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive API Docs (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check Endpoint**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- **API Root**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

---

### 2. Frontend Setup (React + Vite)

Open a second terminal window:

```powershell
cd frontend

# Install dependencies
npm install

# Copy environment template
Copy-Item .env.example .env

# Start Vite dev server
npm run dev
```

- **Application URL**: [http://localhost:5173](http://localhost:5173)

---

### 3. Production Build & Type Checking

To verify TypeScript and generate the production bundle:

```powershell
cd frontend
npm run build
```

---

## Project Structure

```text
AutoAnalyst-AI/
├── .gitignore                      # Git ignore patterns (.env, node_modules, .venv, uploads)
├── README.md                       # Documentation & instructions
├── docs/
│   └── PHASE_1.md                  # Phase 1 scope and acceptance checklist
├── frontend/
│   ├── .env.example                # Frontend environment template
│   ├── index.html                  # HTML entry point with modern typography
│   ├── package.json                # React, Vite, Framer Motion, Lucide, Tailwind
│   ├── tailwind.config.js          # Tailwind CSS configuration
│   ├── tsconfig.json               # TypeScript configuration
│   ├── vite.config.ts              # Vite server configuration
│   └── src/
│       ├── components/
│       │   ├── common/
│       │   │   ├── BackendStatusIndicator.tsx # Live API health pill
│       │   │   ├── BrandLogo.tsx              # Logo & Powered by Saniya tag
│       │   │   └── ThemeToggle.tsx            # Light/Dark switch
│       │   ├── landing/
│       │   │   ├── AnalysisPreviewCard.tsx    # Animated preview card
│       │   │   ├── FeaturesSection.tsx        # Value propositions
│       │   │   ├── HeroSection.tsx            # Hero with CTA
│       │   │   ├── ProofBanner.tsx            # Workflow stages
│       │   │   └── WorkflowSection.tsx        # 3-step pipeline
│       │   ├── layout/
│       │   │   ├── Footer.tsx                 # Footer with branding
│       │   │   └── Navbar.tsx                 # Responsive header with status
│       │   └── workspace/
│       │       ├── MetricsSummary.tsx         # KPI summary cards
│       │       ├── RecentActivityPanel.tsx    # Empty activity feed
│       │       ├── WelcomeBanner.tsx          # Upload CTA & art
│       │       ├── WorkspaceSidebar.tsx       # Sidebar navigation
│       │       └── WorkspaceTopBar.tsx        # Workspace header
│       ├── context/
│       │   └── ThemeContext.tsx               # Theme provider & persistence
│       ├── hooks/
│       │   ├── useBackendHealth.ts            # Live API polling & status hook
│       │   └── useTheme.ts                    # Theme hook
│       ├── pages/
│       │   ├── LandingPage.tsx                # Landing page view
│       │   └── WorkspacePage.tsx              # Workspace shell view
│       ├── services/
│       │   └── api.ts                         # API client with timeout handling
│       ├── styles/
│       │   └── index.css                      # Theme tokens, glassmorphism, utilities
│       ├── types/
│       │   ├── api.ts                         # Health & API state types
│       │   ├── navigation.ts                  # View mode types
│       │   └── theme.ts                       # Theme definition types
│       ├── App.tsx                            # Root application view orchestrator
│       ├── main.tsx                           # React entry point
│       └── vite-env.d.ts                      # Vite client environment types
└── backend/
    ├── .env.example                # Backend environment template
    ├── requirements.txt            # Python dependencies
    └── app/
        ├── __init__.py
        ├── main.py                 # FastAPI app entry with CORS & routes
        ├── api/
        │   ├── __init__.py
        │   └── routes/
        │       ├── __init__.py
        │       └── health.py       # GET /api/v1/health route
        └── core/
            ├── __init__.py
            └── config.py           # Pydantic Settings configuration loader
```

---

## Roadmap

- **Phase 1 (Completed)**: UI/UX Foundation, Theme Engine, Workspace Shell, FastAPI Health API, Frontend-to-Backend Connectivity.
- **Phase 2 (Next)**: Authentication, secure dataset upload & ingestion, Pandas/NumPy profiling, schema validation.
- **Phase 3**: Automated chart recommendation, dashboard generation, and interactive data filtering.
- **Phase 4**: GenAI autonomous analysis (Gemini / OpenAI API) and natural-language dataset querying.
- **Phase 5**: Machine learning models (Scikit-learn), predictive analytics, and enterprise reporting.
