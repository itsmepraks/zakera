# Zakera - AI Chat Agent

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A modern, intelligent AI chat agent built with conversational memory, tool integration, and optimized response generation. Inspired by advanced conversational AI systems, Zakera provides a robust foundation for building context-aware chatbot applications.

## ✨ Features

### Core Capabilities
- **🧠 Conversation Memory**: Maintains context across multi-turn conversations with efficient memory management
- **🛠️ Tool Integration**: Extensible tool system for external API calls, database queries, and custom functions
- **⚡ Optimized Responses**: Smart response caching and streaming support for improved performance
- **🔌 Flexible API**: RESTful and WebSocket endpoints for various integration scenarios
- **💾 Persistent Storage**: Conversation history and user preferences stored securely
- **🎨 Modern UI**: Clean, responsive React-based chat interface

### Advanced Features
- Multi-model support (OpenAI, Anthropic, local models)
- Conversation branching and versioning
- Real-time streaming responses
- Rate limiting and authentication
- Custom prompt templates
- Analytics and monitoring

## 🏗️ Architecture

```
zakera/
├── src/
│   ├── model/          # AI model configurations and wrappers
│   ├── api/            # FastAPI backend services
│   ├── frontend/       # React-based user interface
│   └── tools/          # Custom tool implementations
├── config/             # Configuration files
├── docs/               # Documentation
├── tests/              # Test suites
├── scripts/            # Utility scripts
└── data/               # Data storage (gitignored)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- Node.js 16 or higher
- API keys for your chosen AI provider (OpenAI, Anthropic, etc.)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/itsmepraks/zakera.git
cd zakera

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/.env.example config/.env
# Edit config/.env with your API keys

# Run the backend
python -m uvicorn src.api.main:app --reload
```

The API will be available at `http://localhost:8000`

### Frontend Setup

```bash
# Navigate to frontend directory
cd src/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The UI will be available at `http://localhost:3000`

## 📚 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Configuration Guide](docs/configuration.md)
- [Tool Development](docs/tools.md)
- [Deployment Guide](docs/deployment.md)

## 🛠️ Development

### Running Tests

```bash
# Backend tests
pytest tests/

# Frontend tests
cd src/frontend
npm test
```

### Code Quality

```bash
# Format code
black src/
isort src/

# Lint
flake8 src/
mypy src/
```

## 🔧 Configuration

Key configuration options in `config/.env`:

```env
# AI Model Configuration
MODEL_PROVIDER=openai  # openai, anthropic, local
MODEL_NAME=gpt-4-turbo-preview
OPENAI_API_KEY=your_key_here

# Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Database
DATABASE_URL=sqlite:///./data/zakera.db

# Security
SECRET_KEY=your_secret_key
ALLOWED_ORIGINS=http://localhost:3000
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by modern conversational AI systems
- Built with FastAPI, React, and modern AI technologies
- Community contributions and feedback

## 📧 Contact

Prakriti Bista - [https://praks.me](https://praks.me)

Project Link: [https://github.com/itsmepraks/zakera](https://github.com/itsmepraks/zakera)

---

**Note**: This project is under active development. Features and APIs may change as the project evolves.
