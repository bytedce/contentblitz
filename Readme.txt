ContentBlitz

High Level Architechture

User (Streamlit UI)
        │
        ▼
Agent Orchestrator (single controller)
        │
        ├── ResearchAgent
        │     ├── FAISS RAG (CSV)
        │     ├── Tavily Web Search
        │     ├── RetrievalQA
        │     └── Guardrails
        │
        ├── BlogWriterAgent
        │     ├── Marketing Blog Creation
        │     └── Image placeholders
        │
        ├── ImageGeneratorAgent
        │     └── Marketing Images
        │
        └── LinkedInPostAgent
              ├── LinkedIn Copy
              └── Optional Posting API


Project Directory Structure

content_creator_app/
│
├── app.py                     # Streamlit UI (single page, production-grade)
│
├── agents.py                  # ALL agents + orchestration logic
│
├── rag.py                     # FAISS + CSV loader + RetrieverQA
│
├── tools.py                   # Tavily search + helper tools
│
├── storage.py                 # History persistence (last 10 topics)
│
├── config.py                  # Keys, model configs, constants
│
├── data/
│   ├── products.csv           # Beauty product dataset for RAG
│   └── faiss_index/           # Persisted FAISS index
│
├── logs/
│   └── agent.log              # Optional file logging
│
└── requirements.txt


