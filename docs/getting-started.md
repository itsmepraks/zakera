# Getting Started with Zakera

Welcome to Zakera! This guide will help you set up and run the AI chat agent.

## Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- npm or yarn
- API key from OpenAI, Anthropic, or a local model setup

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/itsmepraks/zakera.git
cd zakera
```

### 2. Automated Setup

Run the setup script:

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

This will:
- Create a Python virtual environment
- Install all Python dependencies
- Create configuration files
- Install frontend dependencies

### 3. Configure Environment

Edit `config/.env` with your settings:

```env
# Choose your AI provider
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4-turbo-preview

# Add your API key
OPENAI_API_KEY=sk-...
```

### 4. Run the Application

#### Option A: Using the run script

```bash
chmod +x scripts/run_dev.sh
./scripts/run_dev.sh
```

#### Option B: Manual start

**Terminal 1 - Backend:**
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
python -m uvicorn src.api.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd src/frontend
npm run dev
```

### 5. Access the Application

- **Frontend UI**: http://localhost:3000
- **API Backend**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs

## Next Steps

- Explore the [API Reference](api-reference.md)
- Learn about [Configuration Options](configuration.md)
- Read the [Architecture Overview](architecture.md)
- Check out [Tool Development](tools.md)

## Troubleshooting

### Python Dependencies

If you encounter issues installing dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

### Frontend Issues

```bash
cd src/frontend
rm -rf node_modules package-lock.json
npm install
```

### Port Already in Use

Change ports in:
- Backend: `config/.env` → `API_PORT=8001`
- Frontend: `src/frontend/package.json` → `"dev": "next dev -p 3001"`

## Development Mode

The application runs in development mode by default with:
- Hot reloading for code changes
- Detailed error messages
- Debug logging

For production deployment, see [Deployment Guide](deployment.md).
