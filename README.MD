# 🛡️ Nexora – Self-Defending Confidential Multimodal AI Gateway

**Nexora** is a secure, enterprise-inspired **Self-Defending Multimodal AI Gateway** that protects AI interactions through **Multi-Agent Orchestration**, **Prompt Shield**, and **intelligent model routing**. Instead of directly forwarding user requests to an LLM, Nexora analyzes, verifies, and validates every request to ensure safe, confidential, and policy-compliant AI responses.

---

## ✨ Features

- 🔐 Auth0 Authentication (Google Sign-In)
- 🤖 Multi-Agent Orchestration
- 🛡️ Prompt Injection & Jailbreak Detection
- 🔒 Confidential Data & PII Protection
- 📊 Risk Score & Prompt Shield
- 💬 AI Chat & Coding Assistance
- 🖼️ Image Understanding & OCR
- 📄 PDF Analysis
- 🎤 Voice Input (Speech-to-Text)
- 🎨 AI Image Generation
- ⚡ Intelligent Model Routing
- 📱 Fully Responsive UI

---

## 🏗️ Architecture

```text
User
  │
  ▼
Auth0 Authentication
  │
  ▼
Prompt Shield
  │
  ▼
Multi-Agent Orchestration
  │
  ▼
Model Router
  ├── Groq (Chat & Coding)
  ├── OpenRouter (Reasoning & Vision)
  └── Hugging Face (OCR, STT, Embeddings, Image Generation)
  │
  ▼
Response Validation
  │
  ▼
Secure AI Response
```

---

## 🤖 AI Models Used

| Purpose | Model | Provider |
|---------|-------|----------|
| Chat & Coding | `llama-3.3-70b-versatile` | Groq |
| Reasoning | `deepseek/deepseek-r1:free` | OpenRouter |
| Vision | `qwen/qwen2.5-vl:free` | OpenRouter |
| Speech-to-Text | `openai/whisper-large-v3` | Hugging Face |
| OCR | `microsoft/trocr-base-printed` | Hugging Face |
| Embeddings | `BAAI/bge-large-en-v1.5` | Hugging Face |
| Prompt Shield | `ProtectAI/deberta-v3-base-prompt-injection-v2` | Hugging Face |
| Image Generation | `black-forest-labs/FLUX.1-dev` | Hugging Face |

---

## 🛠️ Tech Stack

**Frontend**
- HTML5
- CSS3
- JavaScript

**Backend**
- FastAPI
- Python
- LangGraph

**AI Providers**
- Groq
- OpenRouter
- Hugging Face

**Authentication**
- Auth0

**Database**
- PostgreSQL
- ChromaDB

---

## 📂 Project Structure

```text
AI_Secure_Gateway/
│
├── .gitignore
├── README.md
│
├── nexora-backend/
│   ├── main.py
│   ├── providers.py
│   ├── auth.py
│   ├── requirements.txt
│   ├── .env
│   └── pipeline/
│
└── nexora-frontend/
    ├── nexora.html
    └── nexora-app.html
```

---

## 🚀 Installation

```bash
git clone https://github.com/your-username/AI_Secure_Gateway.git

cd AI_Secure_Gateway/nexora-backend

pip install -r requirements.txt

uvicorn main:app --reload
```

Create a `.env` file inside **nexora-backend**:

```env
GROQ_API_KEY=
OPENROUTER_API_KEY=
HUGGINGFACE_API_KEY=

AUTH0_DOMAIN=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
```

Open `nexora-frontend/nexora.html` in your browser.

---

## 🔒 Security Pipeline

```
Authentication
      ↓
Prompt Shield
      ↓
Risk Analysis
      ↓
Multi-Agent Verification
      ↓
Model Routing
      ↓
Response Validation
      ↓
Secure AI Response
```

---

## ❤️ Powered By

- 🔐 Auth0
- ⚡ Groq
- 🌐 OpenRouter
- 🤗 Hugging Face
- 🚀 FastAPI
- 🧠 LangGraph
- 📦 ChromaDB
- 🐘 PostgreSQL

---

## 📜 License

This project is developed for **educational and research purposes**.

---

<div align="center">

# 🛡️ Nexora

### **Secure AI • Trusted Intelligence • Protected Conversations**

</div>