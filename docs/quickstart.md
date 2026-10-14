# Quick Start Guide

> [!WARNING]
> **Legacy and unverified.** These commands describe the inherited prototype and are not a supported Zakera vNext installation path. Use the root README and `docs/VNEXT_PLAN.md` for current status.

Get Zakera up and running in 5 minutes! This guide covers the fastest path to a working installation.

## Prerequisites

- **Python 3.9+** ([Download](https://www.python.org/downloads/))
- **Node.js 16+** ([Download](https://nodejs.org/))
- **Git** ([Download](https://git-scm.com/))
- **Docker** (Optional, for monitoring stack)

## 🚀 Five-Minute Setup

### Step 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/itsmepraks/zakera.git
cd zakera

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your settings
# Minimum required: Set at least one model provider API key
```

**Essential Variables:**
```env
# Choose ONE of these providers to start:
OPENAI_API_KEY=sk-...              # If using OpenAI (recommended for beginners)
ANTHROPIC_API_KEY=sk-ant-...       # If using Anthropic Claude
GOOGLE_API_KEY=AIza...             # If using Google Gemini

# Or use local models (no API key needed!):
ENABLE_OLLAMA=true
DEFAULT_MODEL=llama3:8b
```

### Step 3: Initialize Database

```bash
# Run database migrations
alembic upgrade head

# Database file will be created at: data/zakera.db
```

### Step 4: Start the Server

```bash
# Start FastAPI backend
python -m uvicorn src.api.main:app --reload

# Server will start at: http://localhost:8000
# API docs available at: http://localhost:8000/api/docs
```

### Step 5: Verify Installation

Open http://localhost:8000 in your browser. You should see:

```json
{
  "message": "Zakera AI Chat Agent API",
  "version": "0.5.0",
  "status": "operational"
}
```

**🎉 Congratulations! Zakera is running!**

## 🎯 Next Steps

### Option A: Try the API

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/api/v1/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! Tell me a joke.",
    "conversation_id": null
  }'
```

### Option B: Set Up Frontend

```bash
# In a new terminal, navigate to frontend
cd src/frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Frontend will be at: http://localhost:3000
```

### Option C: Try Local Models (No API Costs!)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model (choose one):
ollama pull llama3:8b      # Recommended: Fast & capable (4.7GB)
ollama pull mistral:7b     # Alternative: Fast responses (4.1GB)
ollama pull codellama:13b  # For coding tasks (7.4GB)

# Update .env:
DEFAULT_MODEL=llama3:8b
ENABLE_OLLAMA=true

# Restart the server
```

### Option D: Enable Monitoring

```bash
# Start Prometheus, Grafana, and AlertManager
cd monitoring
docker-compose up -d

# Access dashboards:
# Grafana: http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9090
# Metrics: http://localhost:8000/api/v1/monitoring/metrics
```

## 📊 Choosing Your Model Provider

### Quick Comparison

| Provider | Best For | Cost | Setup | Quality |
|----------|----------|------|-------|--------|
| **Ollama** | Learning, privacy, cost-free | FREE | Easy | Good |
| **OpenAI** | Production, best quality | $$$ | Easiest | Excellent |
| **Anthropic** | Long contexts, analysis | $$ | Easy | Excellent |
| **Gemini** | Multimodal, free tier | $ | Easy | Very Good |
| **HuggingFace** | Custom models, research | FREE | Medium | Varies |

### Provider Setup Details

#### OpenAI (Easiest)
1. Sign up at https://platform.openai.com/
2. Create API key at https://platform.openai.com/api-keys
3. Add to `.env`: `OPENAI_API_KEY=sk-...`
4. Choose model: `DEFAULT_MODEL=gpt-4-turbo` or `gpt-3.5-turbo`

#### Ollama (Free, Local)
1. Install: `curl -fsSL https://ollama.com/install.sh | sh`
2. Pull model: `ollama pull llama3:8b`
3. Update `.env`: `ENABLE_OLLAMA=true`, `DEFAULT_MODEL=llama3:8b`
4. No API key needed!

#### Anthropic Claude
1. Sign up at https://console.anthropic.com/
2. Get API key from API Keys section
3. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
4. Choose model: `DEFAULT_MODEL=claude-3-sonnet`

#### Google Gemini
1. Get API key at https://makersuite.google.com/app/apikey
2. Add to `.env`: `GOOGLE_API_KEY=AIza...`
3. Choose model: `DEFAULT_MODEL=gemini-1.5-pro`

## 🔧 Common Configurations

### Development Setup (Recommended)
```env
# Use local model for development
DEFAULT_MODEL=llama3:8b
ENABLE_OLLAMA=true
LOG_LEVEL=DEBUG
DEBUG=true
```

### Production Setup
```env
# Use premium model with fallback
DEFAULT_MODEL=gpt-4-turbo
FALLBACK_STRATEGY=sequential
ENABLE_MODEL_FALLBACK=true
LOG_LEVEL=INFO
DEBUG=false

# Enable monitoring
ENABLE_METRICS=true
ENABLE_ALERTS=true
```

### Cost-Optimized Setup
```env
# Use free local model
DEFAULT_MODEL=llama3:8b
ENABLE_OLLAMA=true
ENABLE_OPENAI=false
ENABLE_ANTHROPIC=false
```

### Privacy-First Setup
```env
# All processing stays local
DEFAULT_MODEL=llama3:70b
ENABLE_OLLAMA=true
ENABLE_OPENAI=false
ENABLE_ANTHROPIC=false
ENABLE_GEMINI=false
```

## 🐛 Troubleshooting

### Issue: "Module not found" errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Issue: "Port 8000 already in use"
```bash
# Find process using port 8000
lsof -ti:8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or use different port
python -m uvicorn src.api.main:app --port 8001
```

### Issue: "Database locked" errors
```bash
# Stop all running instances
pkill -f uvicorn

# Remove lock file
rm data/zakera.db-journal

# Restart server
python -m uvicorn src.api.main:app --reload
```

### Issue: Ollama model not found
```bash
# Check if Ollama is running
ollama list

# Pull the model if missing
ollama pull llama3:8b

# Verify model name in .env matches exactly
# Use: ollama list to see available models
```

### Issue: Out of memory with local models
```bash
# Use smaller model
ollama pull mistral:7b  # Smaller than llama3:8b

# Or use quantized version
ollama pull llama3:8b-q4  # 4-bit quantization

# Enable 8-bit mode for HuggingFace
HUGGINGFACE_8BIT=true
```

### Issue: "API key invalid" errors
```bash
# Verify API key is set correctly
echo $OPENAI_API_KEY  # macOS/Linux
echo %OPENAI_API_KEY%  # Windows

# Ensure no extra spaces in .env file
# Correct: OPENAI_API_KEY=sk-...
# Wrong:   OPENAI_API_KEY= sk-...  (extra space)

# Test API key manually
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Issue: Slow responses
```bash
# For local models:
# 1. Use GPU if available
OLLAMA_NUM_GPU=1

# 2. Use faster model
DEFAULT_MODEL=mistral:7b  # Faster than llama3:8b

# 3. Reduce max tokens
MAX_TOKENS=1024  # Default is 2048

# For API models:
# Use faster tier model
DEFAULT_MODEL=gpt-3.5-turbo  # Much faster than gpt-4
```

## 📚 Next Steps

Now that Zakera is running, explore these features:

1. **Read the [API Documentation](http://localhost:8000/api/docs)**
   - Interactive Swagger UI
   - Try different endpoints
   - See request/response formats

2. **Set Up Monitoring**
   - Follow [Monitoring Guide](MONITORING.md)
   - View metrics in Grafana
   - Configure alerts

3. **Customize Your Setup**
   - Review [Configuration Guide](configuration.md)
   - Set up custom tools
   - Configure authentication

4. **Deploy to Production**
   - Follow [Deployment Guide](deployment.md)
   - Set up Docker containers
   - Configure Kubernetes

5. **Contribute**
   - Check [Contributing Guide](../CONTRIBUTING.md)
   - Report issues
   - Submit pull requests

## 💡 Tips

- **Start with Ollama** if you're learning or want zero API costs
- **Use GPT-3.5-turbo** for production with reasonable costs
- **Enable monitoring** from day one to track usage and costs
- **Set up fallback** to prevent failures when one provider is down
- **Check logs** in `logs/zakera.log` for debugging
- **Use Docker** for consistent environments across team

## 🆘 Getting Help

- **Documentation**: Check `docs/` folder
- **Issues**: https://github.com/itsmepraks/zakera/issues
- **Discussions**: https://github.com/itsmepraks/zakera/discussions
- **Email**: Contact via GitHub profile

---

**Welcome to Zakera!** 🎉

You're now ready to build amazing AI chat applications!
