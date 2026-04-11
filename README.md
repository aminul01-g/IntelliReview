---
title: IntelliReview
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
---

# IntelliReview - AI-Powered Code Review Assistant

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2-blue.svg)](https://react.dev)

**Automated code review powered by AI with multi-language support**

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [API Docs](#-api-documentation) • [Contributing](#-contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
  - [CLI](#-cli-usage)
  - [API](#-api-usage)
  - [Dashboard](#-dashboard-usage)
- [Development](#-development)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Configuration](#-configuration)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**IntelliReview** is a comprehensive AI-powered code review platform that combines static analysis, machine learning, and large language models to provide intelligent, context-aware code reviews. It helps development teams catch bugs early, detect security vulnerabilities, identify anti-patterns, and maintain high code quality standards.

### What Makes IntelliReview Unique?

- **Plan-First Architecture**: Analyzes the directory tree and configuration files first to generate a structural plan, ensuring all auto-fixes respect the project's broader architecture.
- **Entity-Centric Entity History**: Tracks and groups analyses by "Projects" instead of loose file fragments, allowing teams to visualize overall project health and AI-inferred dependency maps.
- **Elite AI Engines**: Powered by advanced HuggingFace endpoints (`DeepSeek-R1` for architectural logic and suggestions, `Qwen3-32B` for conceptual RAG context mapping and pattern deduction).
- **AI Code Vulnerability Detection**: Detects common hallucinations and AI-generated code snippets (e.g. empty try-catches, fake URLs, TODO blocks).
- **Expert SQE Format**: Generates comprehensive, professional code review reports.
- **GitHub PR Auto-Reviewer**: Integrates seamlessly into CI/CD pipelines to review GitHub PRs using Unified Diff Scanning.
- **Universal Language Support**: Native AST parsing for Python, JavaScript, Java, C/C++, with intelligent fallback logic for all other languages.

---

## ✨ Features

### Core Analysis Capabilities

#### 🔍 **Static Code Analysis**
- **Complexity Metrics**: Cyclomatic complexity, maintainability index, code duplication detection
- **Bug Detection**: Syntax errors, type mismatches, missing arguments, resource leaks, concurrency issues
- **Anti-Pattern Detection**: God classes, long methods, magic numbers, deep nesting, callback hell
- **Security Scanning**: OWASP vulnerabilities, unsafe function usage, buffer overflows, SQL injection risks

#### 🤖 **AI-Powered Features**
- **Smart Suggestions (`DeepSeek-R1`)**: Context-aware code improvement and automated diff patch generation capable of highly logical refactoring.
- **Semantic Context Mapping (`Qwen3-32B`)**: Zero-dependency context analyzer that deduces structural and imported file relationships across the workspace, feeding global context to local code edits.
- **AI Pattern Detections**: Specialized detector identifies hallmarks of AI-generated stubs, hallucinated code, or dead placeholder logic code.
- **Zero-Shot Code Smells (`DeepSeek-R1`)**: Analyzes abstract syntax patterns on the fly to detect deep-rooted "god classes" and "spaghetti logic" far beyond simplistic linters.
- **Telemetry Pattern Learning (`Qwen3-32B`)**: Automatically ingests historical accepted/rejected AI suggestions to deduce and document human-readable team coding standards.

#### 🌐 **Universal Language Support**
- Native AST parsing for **Python, JavaScript, Java, C/C++**.
- Intelligent fallback for **All Other Languages** via Custom Rule evaluations, AI Pattern checks, duplication scanning, and LLM-driven inference.

### Integration Options

#### 🖥️ **Command Line Interface (CLI)**
```bash
# Analyze a single file
intellireview analyze app.py

# Analyze entire directory
intellireview analyze-dir src/ --recursive

# View statistics
intellireview stats
```

#### 🌐 **REST API**
- Full-featured FastAPI backend with OpenAPI documentation
- JWT authentication with secure token management
- Rate limiting and CORS support
- WebSocket support for real-time analysis updates

#### 📊 **Web Dashboard**
- Modern React + TypeScript interface
- Real-time code analysis with syntax highlighting
- Interactive charts and metrics visualization (Recharts)
- Analysis history and team collaboration features
- Feedback system for AI suggestions

#### 🔌 **MCP Server (Model Context Protocol)**
- Exposes dual commands `analyze_code` and `analyze_project`.
- Allows Claude Desktop, Cursor, and agentic workflows to autonomously run, evaluate, and iteratively fix the codebase!

#### 🤖 **GitHub PR Auto-Reviewer**
- Configurable webhook (`/api/v1/webhooks/github`) to automatically consume Pull Request Git events.
- Evaluates Git Unified Diffs to apply static analysis only against changed lines, ensuring ultra-low latency reviews directly as PR comments.

#### 🛠️ **VS Code Extension**
- Complete TypeScript extension located in `vscode-extension/`
- Command-triggered REST API integration paints IDEs with native VS Code Diagnostics (red squiggly warnings) generated by IntelliReview!

### Advanced Features

- **Team Analytics**: Track code quality trends across teams
- **Feedback Loop**: ML model improvement through user feedback
- **Docker Support**: Complete containerization with PostgreSQL, MongoDB, Redis, and Nginx
- **Scalable Architecture**: Async processing ready (Celery support built-in)
- **Comprehensive Testing**: E2E test suite with multi-language coverage

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│   │   CLI    │  │   Web    │  │ REST API │  │   Git    │     │
│   │   Tool   │  │Dashboard │  │  Clients │  │  Hooks   │     │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                       API Gateway Layer                         │
│         FastAPI + JWT Auth + Rate Limiting + CORS              │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                     Analysis Engine                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Language   │  │    Static    │  │      AI      │         │
│  │   Parsers    │  │   Analysis   │  │  Suggestion  │         │
│  │  (AST/Tree)  │  │   Detectors  │  │  Generator   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
│  • Python Parser   • CI/CD Filters   • DeepSeek-R1 (Logic)     │
│  • JS Parser       • Security        • Qwen3-32B (Semantic)    │
│  • Java Parser     • Anti-patterns   • Pattern Learning        │
│  • C/C++ Parser    • Unified Diffs   • Dependency Context Map  │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                        Data Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  PostgreSQL  │  │   MongoDB    │  │    Redis     │         │
│  │ (User data,  │  │  (Analysis   │  │   (Cache,    │         │
│  │  Analytics)  │  │   Results)   │  │   Session)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- **Framework**: FastAPI 0.104+ (Python 3.11+)
- **Authentication**: JWT with python-jose
- **Rate Limiting**: SlowAPI
- **Async Support**: Celery + Redis (optional)

**Analysis Tools:**
- **Python**: AST, Pylint (Fatal/Error filtering), Bandit, Radon
- **JavaScript**: Esprima
- **AI/ML**: Hugging Face Inference API (`DeepSeek-R1`, `Qwen3-32B`)

**Databases:**
- **PostgreSQL**: User management, authentication
- **MongoDB**: Analysis results storage
- **Redis**: Caching, session management

**Frontend:**
- **Framework**: React 18.2 + TypeScript
- **Build Tool**: Vite
- **Styling**: TailwindCSS + Typography plugin
- **Charts**: Recharts
- **Icons**: Lucide React
- **Markdown**: React Markdown + Remark GFM

**DevOps:**
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx
- **Orchestration**: Kubernetes ready

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose (recommended)
- OR Python 3.11+ (for local development)
- Node.js 18+ (for dashboard development)
- Hugging Face API key (for AI features)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/intelliReview.git
cd intelliReview/intellireview
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Hugging Face API key
nano .env
```

Required environment variables:
```env
HUGGINGFACE_API_KEY=your_huggingface_api_key_here
SECRET_KEY=your_secret_key_here  # Generate with scripts/generate_secret_key.py
```

### 3. Start with Docker Compose

```bash
# Start all services (API, Dashboard, Databases)
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f api
```

### 4. Access the Application

- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Dashboard**: http://localhost:3000
- **Nginx Proxy**: http://localhost:80

### 5. Quick Test

```bash
# Create a demo user (or use dashboard to register)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","email":"demo@example.com","password":"demo123"}'

# Login and get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=demo&password=demo123"

# Analyze some Python code
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code":"def test():\n    x = input()\n    if x > 10:\n        print(\"large\")","language":"python"}'
```

---

## 📦 Installation

### Option 1: Docker (Recommended)

Fastest way to get started with all services:

```bash
cd intellireview
docker-compose up -d
```

This starts:
- API server (port 8000)
- PostgreSQL database
- MongoDB for analysis storage
- Redis for caching
- React dashboard (port 3000)
- Nginx reverse proxy (port 80)

### Option 2: Local Development

#### Backend Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Optional, for development

# Set up databases (requires PostgreSQL, MongoDB, Redis running locally)
# Update .env with your local database URLs

# Generate secret key
python scripts/generate_secret_key.py

# Run the API server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd dashboard

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### Option 3: CLI Only

For quick code analysis without backend setup:

```bash
# Install the package
pip install -e .

# Configure API endpoint
intellireview config-set --key api_url --value http://localhost:8000

# Login
intellireview login

# Analyze code
intellireview analyze myfile.py
```

---

## 💻 Usage

### 🖥️ CLI Usage

The IntelliReview CLI provides a powerful terminal interface for code analysis.

#### Installation

```bash
pip install -e .
```

#### Commands

```bash
# Login to IntelliReview
intellireview login

# Analyze a single file
intellireview analyze src/main.py

# Analyze with specific language
intellireview analyze -l javascript script.js

# Analyze entire directory
intellireview analyze-dir src/ --recursive

# Filter by language
intellireview analyze-dir src/ -r -l python

# View your statistics
intellireview stats

# Configuration management
intellireview config-set --key api_url --value http://localhost:8000
intellireview config-get

# Initialize project configuration
intellireview init
```

#### Output Formats

```bash
# Default terminal output (pretty formatted)
intellireview analyze app.py

# JSON output
intellireview analyze app.py --output json > results.json
```

### 🌐 API Usage

#### Authentication

```python
import requests

API_URL = "http://localhost:8000/api/v1"

# Register
response = requests.post(f"{API_URL}/auth/register", json={
    "username": "developer",
    "email": "dev@example.com",
    "password": "securepass123"
})

# Login
response = requests.post(f"{API_URL}/auth/login", data={
    "username": "developer",
    "password": "securepass123"
})

token = response.json()["access_token"]
headers = {authorization": f"Bearer {token}"}
```

#### Code Analysis

```python
# Analyze Python code
code = """
def calculate_total(items):
    total = 0
    for item in items:
        total = total + item
    return total
"""

response = requests.post(
    f"{API_URL}/analysis/analyze",
    headers=headers,
    json={
        "code": code,
        "language": "python",
        "file_path": "calculator.py"
    }
)

result = response.json()

# Access results
print(f"Analysis ID: {result['analysis_id']}")
print(f"Status: {result['status']}")
print(f"Issues found: {len(result['issues'])}")

# View metrics
metrics = result['metrics']
print(f"Lines of Code: {metrics['lines_of_code']}")
print(f"Complexity: {metrics['complexity']}")
print(f"Maintainability Index: {metrics.get('maintainability_index')}")

# Review issues
for issue in result['issues']:
    print(f"\nLine {issue['line']}: {issue['message']}")
    print(f"Severity: {issue['severity']}")
    print(f"Type: {issue['type']}")
    if issue.get('suggestion'):
        print(f"AI Suggestion:\n{issue['suggestion']}")
```

#### History and Feedback

```python
# Get analysis history
history = requests.get(f"{API_URL}/analysis/history", headers=headers).json()

# Submit feedback on AI suggestions
requests.post(
    f"{API_URL}/feedback/submit",
    headers=headers,
    json={
        "suggestion_id": "suggestion_123",
        "accepted": True,
        "issue_type": "bug",
        "comment": "Very helpful suggestion!"
    }
)

# Get user metrics
metrics = requests.get(f"{API_URL}/metrics/user", headers=headers).json()
print(f"Total analyses: {metrics['total_analyses']}")
print(f"This week: {metrics['weekly_analyses']}")
```

### 📊 Dashboard Usage

Access the web dashboard at http://localhost:3000

**Features:**
- **Dashboard View**: Overview of your code quality metrics
- **Analyze Code**: Interactive code editor with real-time analysis
- **History**: Browse past analyses with filtering
- **Metrics**: Team analytics and AI suggestion acceptance rates
- **Feedback**: Rate AI suggestions to improve the system

**Key Workflows:**

1. **Register/Login**: Create an account or sign in
2. **Analyze Code**: 
   - Select language
   - Paste or type code
   - Click "Analyze Code"
   - View issues with AI suggestions
3. **Review History**: Access past analyses and re-view results
4. **Track Metrics**: Monitor code quality trends over time

---

## 🛠️ Development

### Setup Development Environment

```bash
# Clone and enter directory
git clone https://github.com/yourusername/intelliReview.git
cd intelliReview/intellireview

# Backend setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Frontend setup
cd dashboard
npm install
cd ..

# Start development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Project Structure

```
intellireview/
├── api/                      # FastAPI application
│   ├── routes/              # API endpoints
│   │   ├── analysis.py      # Code analysis endpoints
│   │   ├── auth.py          # Authentication
│   │   ├── feedback.py      # User feedback
│   │   ├── metrics.py       # Analytics
│   │   └── webhooks.py      # Git integration
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic schemas
│   ├── middleware/          # Custom middleware
│   ├── database.py          # Database configuration
│   ├── auth.py              # JWT authentication
│   └── main.py              # Application entry point
│
├── analyzer/                 # Code analysis engine
│   ├── parsers/             # Language parsers
│   │   ├── python_parser.py
│   │   ├── javascript_parser.py
│   │   ├── java_parser.py
│   │   └── cpp_parser.py
│   ├── detectors/           # Issue detectors
│   │   ├── antipatterns.py  # Anti-pattern detection
│   │   ├── quality.py       # Quality & bug detection
│   │   └── security.py      # Security scanning
│   └── metrics/             # Code metrics
│       ├── complexity.py    # Complexity analysis
│       └── duplication.py   # Duplicate code detection
│
├── ml_models/               # Large Language Model Inference
│   ├── generators/
│   │   └── suggestion_generator.py  # DeepSeek-R1 Suggestions
│   ├── code_smell_detector.py       # DeepSeek-R1 Classification
│   └── pattern_learner.py           # Qwen3-32B Rule Inference
│
├── cli/                     # Command-line interface
│   └── cli.py              # CLI implementation
│
├── dashboard/               # React frontend
│   ├── src/
│   │   ├── intellireview_dashboard.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── tests/                   # Test suite
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── scripts/                 # Utility scripts
│   ├── generate_secret_key.py
│   └── seed_data.py
│
├── config/                  # Configuration
│   └── settings.py          # Application settings
│
├── hooks/                   # Git hooks
│   └── pre_commit.py
│
├── nginx/                   # Nginx configuration
│   └── nginx.conf
│
├── kubernetes/              # K8s deployment configs
│
├── docker-compose.yml       # Production compose file
├── docker-compose.dev.yml   # Development overrides
├── Dockerfile               # API container
├── requirements.txt         # Python dependencies
├── requirements-dev.txt     # Development dependencies
├── .env.example            # Environment template
└── readme.md               # This file
```

### Code Style

This project follows Python and JavaScript best practices:

- **Python**: PEP 8, Black formatter, isort for imports
- **JavaScript/TypeScript**: ESLint, Prettier
- **Type Checking**: mypy for Python, TypeScript for frontend

```bash
# Format Python code
black .
isort .

# Lint Python
flake8 .
mypy .

# Format TypeScript
cd dashboard
npm run format
```

### Adding New Language Support

1. Create parser in `analyzer/parsers/your_language_parser.py`
2. Extend `BaseParser` class
3. Add language-specific detectors in `analyzer/detectors/quality.py`
4. Update `settings.py` to include the new language
5. Add tests in `tests/`

---

## 🧪 Testing

### Test Suite

IntelliReview includes comprehensive tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_analyzer.py

# Run E2E tests (requires running server)
python test_e2e.py
```

### End-to-End Testing

The E2E test suite (`test_e2e.py`) covers:

- User registration and authentication
- Multi-language analysis (Python, Java, JavaScript, C, C++)
- Expert SQE format verification
- File size limits
- History retrieval
- Feedback submission
- Performance benchmarks

```bash
# Start services
docker-compose up -d

# Run E2E tests
python test_e2e.py
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing
- **E2E Tests**: Complete user workflows
- **Syntax Error Tests**: Language-specific error detection
- **Performance Tests**: Response time verification

---

## 🚢 Deployment

### Docker Production Deployment

```bash
# Build and start
docker-compose up -d

# Scale API servers
docker-compose up -d --scale api=3

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Environment Variables for Production

```env
# Application
DEBUG=False
APP_NAME=IntelliReview
APP_VERSION=1.0.0

# Security
SECRET_KEY=<generate-strong-key>
ALLOWED_ORIGINS=https://yourdomain.com

# Databases
POSTGRES_PASSWORD=<strong-password>
MONGO_PASSWORD=<strong-password>

# AI
HUGGINGFACE_API_KEY=<your-hf-key>
HUGGINGFACE_MODEL=deepseek-ai/DeepSeek-R1
HUGGINGFACE_CONTEXT_MODEL=Qwen/Qwen3-32B
```

### Kubernetes Deployment

```bash
# Apply configurations
kubectl apply -f kubernetes/

# Check deployment
kubectl get pods -n intellireview

# View logs
kubectl logs -f deployment/intellireview-api -n intellireview
```

### Cloud Deployment Options

**AWS:**
- ECS/EKS for container orchestration
- RDS for PostgreSQL
- DocumentDB for MongoDB
- ElastiCache for Redis

**Google Cloud:**
- GKE for container orchestration
- Cloud SQL for PostgreSQL
- Atlas MongoDB
- Memorystore for Redis

**Azure:**
- AKS for container orchestration
- Azure Database for PostgreSQL
- Cosmos DB
- Azure Cache for Redis

---

## ⚙️ Configuration

### Application Settings

Edit `.env` file or environment variables:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api/v1

# Database URLs
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=intellireview_db
MONGODB_URL=mongodb://localhost:27017
REDIS_HOST=localhost
REDIS_PORT=6379

# Analysis Settings
MAX_FILE_SIZE=10000  # lines
ANALYSIS_TIMEOUT=30  # seconds
SUPPORTED_LANGUAGES=python,javascript,java,cpp,c

# AI Settings
HUGGINGFACE_API_KEY=your_key
HUGGINGFACE_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct
ML_MODEL_CACHE_ENABLED=True
ML_DEVICE=auto  # auto, cpu, cuda

# Security
SECRET_KEY=your_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ALGORITHM=HS256
```

### Project-Specific Configuration

Create `.intellireview.yml` in your project root:

```yaml
version: 1.0

analysis:
  languages:
    - python
    - javascript
    - java
  
  ignore:
    - node_modules/
    - venv/
    - __pycache__/
    - "*.min.js"
    - dist/
    - build/
  
  rules:
    complexity_threshold: 10
    max_function_length: 50
    max_class_methods: 20
    line_length: 100

reporting:
  format: text  # text or json
  output_file: intellireview_report.txt
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes** and add tests

4. **Run tests**:
   ```bash
   pytest
   python test_e2e.py
   ```

5. **Format code**:
   ```bash
   black .
   isort .
   ```

6. **Commit changes**:
   ```bash
   git commit -m 'Add amazing feature'
   ```

7. **Push to branch**:
   ```bash
   git push origin feature/amazing-feature
   ```

8. **Open a Pull Request**

### Contribution Guidelines

- Write tests for new features (maintain >80% coverage)
- Follow PEP 8 and project code style
- Add docstrings to all public functions
- Update documentation for API/feature changes
- Ensure all tests pass before submitting PR

### Areas for Contribution

- **New Language Support**: Add parsers for Go, Rust, TypeScript, etc.
- **Analysis Rules**: Implement new detectors for specific patterns
- **UI/UX Improvements**: Enhance dashboard features
- **Performance**: Optimize analysis speed and resource usage
- **Documentation**: Improve guides and tutorials

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Hugging Face** - For providing excellent AI models and APIs
- **FastAPI** - For the amazing Python web framework
- **React Team** - For the modern frontend framework
- **Open Source Community** - For the incredible tools and libraries:
  - Pylint, Bandit, Radon (Python analysis)
  - Esprima (JavaScript parsing)
  - Recharts (Data visualization)
  - TailwindCSS (Styling)

---

## 📧 Support & Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/intelliReview/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/intelliReview/discussions)
- **Email**: support@intellireview.com

---

## 🗺️ Roadmap

### Version 1.1 (Q2 2024)
- [x] GitHub App integration (Auto-PR Webhooks)
- [x] Custom rule creation UI (`.intellireview.yml` Engine)
- [x] IDE plugins (VS Code Extension skeleton completed)
- [ ] TypeScript native AST support

### Version 1.2 (Q3 2024)
- [ ] Team workspaces and permissions
- [ ] Advanced analytics dashboard
- [ ] Automated fix suggestions (Auto-Apply)
- [ ] Multi-Agent Consensus reviews

### Version 2.0 (Q4 2024)
- [x] Support for universal programming languages programming languages
- [ ] Self-hosted local ML models
- [ ] Enterprise SSO integration
- [ ] Advanced security scanning (SAST/DAST)

---

<div align="center">

**Made with ❤️ for developers who care about code quality**

[⬆ Back to Top](#intellireview---ai-powered-code-review-assistant)

</div>
