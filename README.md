# 🧠 IntelliForge – AI Multi-Tool Platform with Multi-LLM + RAG + Local Model Support 🚀

A powerful, flexible AI platform that brings **generative AI tools**, **retrieval-augmented generation (RAG)**, and **multi-model chat experiences** into one streamlined web application — all while respecting your data privacy and giving you full control.

Run it on your machine with **Ollama**, in the cloud with **OpenAI**, or both — and switch between models on the fly with memory **fully preserved**.

---

## 🌟 Features

### 🔁 CoreChat – Multi-Model Chatbot with Seamless Switching

* Switch between GPT, Groq, Ollama (and others) **mid-conversation**
* **Persistent memory** across model changes for smooth, coherent chats
* Use your own models locally or cloud services as needed
* Use Completely Free Search Tool (DuckDuckGo + Crawl4ai + Retrieval)
* Great for **model comparison**, **cost efficiency**, and **privacy**

📖 Learn more about the memory management system in [this blog post](https://medium.com/p/c3364e21b117)

---

### 📄 RAGSmith – Retrieval-Augmented Generation on Your Data

* Upload your own documents, PDFs, or databases
* Build a smart, context-aware RAG bot with **your content**
* Supports **OpenAI**, **Groq**, and **Ollama** and **GITHUB** for RAG
* Ideal for **teams**, **creators**, or **private enterprises** who need secure document-based AI

---

### ⚙️ Additional Highlights

* **Privacy-first**: Keep everything on-device if needed (no data leakage)
* **Vector Database Integration**: Efficient storage & search using ChromaDB
* **Modern UI**: Clean web interface for chatting, configuring, and uploading data
* **Docker Support**: Easy to deploy locally or in the cloud
* **Environment-Based Configuration**: Simple setup for multiple environments

---

## 🛠️ Tech Stack

* **Backend**: Python, Flask
* **LLM Integration**: LangChain, OpenAI, Groq, Ollama
* **Vector Search**: ChromaDB, FAISS, Sentence Transformers
* **Frontend**: HTML, JavaScript (minimal UI, fully extendable)
* **Containerization**: Docker
* **Environment Management**: Python-dotenv

---

## 🚀 Getting Started

### Prerequisites

* Python 3.11+
* Docker (optional, for containerized deployment)
* API keys for OpenAI, Groq (if using cloud models)
* [Ollama](https://ollama.com/) installed for local models

---

### Installation

1. Clone the repository:

```bash
git clone https://github.com/AmirmahdiAbtl/IntelliForge
cd IntelliForge
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
cp .env.example .env
```

Edit `.env` with your API keys and config.

---

### Running the Application

#### Local Development

```bash
flask run --no-reload
```

---

## 📚 Usage

1. Open your browser: `http://localhost:5000`
2. Start chatting using CoreChat
3. Switch models at any point — context is retained
4. Upload files to RAGSmith and query your documents

---

## 🔧 Configuration

Environment variables in `.env`:

* `FLASK_ENV` – development or production
* `OPENAI_API_KEY`
* `GROQ_API_KEY`
* `OLLAMA_HOST` – if using local models
* `CHROMA_DB_PATH`, etc.

---

## 🤝 Contributing

Contributions welcome! Help improve the future of personal AI tools.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/MyFeature`)
3. Commit your changes
4. Push and open a PR

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

* LangChain – RAG + LLM magic
* OpenAI, Groq, and Ollama – for providing robust LLM APIs
* ChromaDB & FAISS – blazing-fast vector search
* The open-source community!

---

## 👤 Author

**Amirmahdi Aboutalebi**
🔗 [LinkedIn](https://www.linkedin.com/in/amirmahdi-abootalebi/)
📂 [Project Repository](https://github.com/AmirmahdiAbtl/IntelliForge)
📝 [Blog Post on Memory Handling](https://medium.com/p/c3364e21b117)

---

⭐ Star this repo if you like where this project is going — and feel free to open an issue or pull request if you have ideas!