# Advanced RAG Application with Multi-LLM Support 🚀

A powerful and flexible Retrieval-Augmented Generation (RAG) application that supports multiple Large Language Models (LLMs) including OpenAI and Groq. This application demonstrates the implementation of advanced RAG techniques with a modern tech stack.

## 🌟 Features

- **Multi-LLM Support**: Seamlessly switch between OpenAI and Groq models
- **Advanced RAG Implementation**: Enhanced retrieval and generation capabilities
- **Vector Database Integration**: Efficient document storage and retrieval using ChromaDB
- **Modern Web Interface**: Clean and intuitive user experience
- **Docker Support**: Easy deployment and scaling
- **Environment-Based Configuration**: Flexible setup for different environments

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **Database**: SQLAlchemy, ChromaDB
- **LLM Integration**: LangChain, OpenAI, Groq
- **Vector Search**: FAISS, Sentence Transformers
- **Containerization**: Docker
- **Environment Management**: Python-dotenv

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker (optional, for containerized deployment)
- API keys for your chosen LLM providers

### Installation

1. Clone the repository:
```bash
git clone [your-repository-url]
cd [repository-name]
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```
Edit `.env` with your API keys and configuration.

### Running the Application

#### Local Development
```bash
flask run
```

#### Docker Deployment
```bash
# Build the Docker image
docker build -t rag-app .

# Run the container
docker run -p 5000:5000 \
  -e GROQ_API_KEY=your_groq_api_key \
  -e OPENAI_API_KEY=your_openai_api_key \
  rag-app
```

## 📚 Usage

1. Access the web interface at `http://localhost:5000`
2. Upload your documents for processing
3. Choose your preferred LLM provider
4. Start querying your documents with natural language

## 🔧 Configuration

The application can be configured through environment variables:

- `FLASK_ENV`: Set to 'development' or 'production'
- `GROQ_API_KEY`: Your Groq API key
- `OPENAI_API_KEY`: Your OpenAI API key
- Additional configuration options in `.env`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- LangChain for the excellent RAG framework
- OpenAI and Groq for their powerful LLM APIs
- The open-source community for their invaluable contributions

## 📞 Contact

[Your Name] - [Your LinkedIn Profile]

Project Link: [https://github.com/yourusername/your-repo-name]

---

⭐ Star this repository if you find it useful!
