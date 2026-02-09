# Getting Started with Zakera

This guide will help you set up and run Zakera on your local machine.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9+**: [Download Python](https://www.python.org/downloads/)
- **Node.js 16+**: [Download Node.js](https://nodejs.org/)
- **Git**: [Download Git](https://git-scm.com/downloads/)
- **API Key**: OpenAI, Anthropic, or other AI provider

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/itsmepraks/zakera.git
cd zakera
```

### 2. Backend Setup

#### Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

#### Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### Configure Environment

```bash
# Copy example environment file
cp config/.env.example config/.env

# Edit the configuration file
# Add your API keys and settings
nano config/.env  # or use your preferred editor
```

Required environment variables:
```env
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4-turbo-preview
DATABASE_URL=sqlite:///./data/zakera.db
SECRET_KEY=your-secret-key-here
```

#### Initialize Database

```bash
python scripts/init_db.py
```

#### Run Backend Server

```bash
uvicorn src.api.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

### 3. Frontend Setup

#### Navigate to Frontend Directory

```bash
cd src/frontend
```

#### Install Node Dependencies

```bash
npm install
```

#### Configure Frontend Environment

```bash
cp .env.example .env.local
```

Edit `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Run Frontend Development Server

```bash
npm run dev
```

The UI will be available at `http://localhost:3000`

## First Conversation

1. Open your browser to `http://localhost:3000`
2. You'll see the Zakera chat interface
3. Type a message like "Hello! Tell me about yourself."
4. The AI will respond with context awareness

## Testing the Installation

### Test Backend API

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "conversation_id": null}'
```

### Run Test Suite

```bash
# Backend tests
pytest tests/ -v

# Frontend tests
cd src/frontend
npm test
```

## Common Issues

### Issue: "Module not found"
**Solution**: Ensure virtual environment is activated and dependencies are installed
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "API key not found"
**Solution**: Check that your `.env` file is in the correct location and properly formatted
```bash
cat config/.env  # Verify the file contents
```

### Issue: "Port already in use"
**Solution**: Use a different port
```bash
uvicorn src.api.main:app --reload --port 8001
```

### Issue: Database errors
**Solution**: Reinitialize the database
```bash
rm -rf data/zakera.db
python scripts/init_db.py
```

## Next Steps

- 📖 Read the [Architecture Documentation](architecture.md)
- 🔧 Explore [Configuration Options](configuration.md)
- 🛠️ Learn about [Tool Development](tools.md)
- 🚀 Check the [Deployment Guide](deployment.md)

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make your changes**
   - Write code
   - Add tests
   - Update documentation

3. **Run quality checks**
   ```bash
   black src/
   flake8 src/
   pytest tests/
   ```

4. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   git push origin feature/your-feature
   ```

5. **Create pull request**

## Getting Help

- 📧 Email: [Your contact]
- 🐛 Issues: [GitHub Issues](https://github.com/itsmepraks/zakera/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/itsmepraks/zakera/discussions)

Happy coding! 🎉
