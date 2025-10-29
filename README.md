# INFO 5940  
# Assignment 1: RAG Chat Application

## Overview

This assignment implements a **Retrieval-Augmented Generation (RAG)** chat application that allows users to upload documents in txt and pdf versions and interact with their content through a conversational AI interface.

### Key Features

**Multi-format Document Support**: Upload both `.txt` and `.pdf` files
**Multiple Document Upload**: Process and query across multiple documents simultaneously
**Conversational Interface**: Natural multi-turn conversations with chat history
**RAG Pipeline**: Semantic search retrieval combined with LLM generation
**Document Chunking**: Efficient processing of large documents
**Grounded Responses**: Answers strictly based on uploaded document content

### Technical Architecture

- **Frontend**: Streamlit web interface
- **RAG Framework**: LangChain and LangGraph
- **Vector Database**: ChromaDB for semantic search
- **Embeddings**: OpenAI text-embedding-3-large model
- **LLM**: GPT-4o via Cornell AI API
- **Document Processing**: LangChain document loaders and text splitters

---

## How to Run the Application

### Prerequisites

- GitHub Codespace environment (provided template)
- Cornell AI API key

### Step 1: Set Your API Keys

**IMPORTANT**: You need to set BOTH environment variables before running the application:

```bash
export API_KEY="your-api-key-here"
export OPENAI_API_KEY="your-api-key-here"  # Same key, required for LangChain
export OPENAI_BASE_URL="https://api.ai.it.cornell.edu"
```

**Why both keys?**
- `API_KEY`: Used by the OpenAI client for streaming responses
- `OPENAI_API_KEY`: Used by LangChain components (embeddings, LLM)
- Both should contain the same Cornell API key

**Alternative (run and set key simultaneously):**
```bash
API_KEY="your-key" OPENAI_API_KEY="your-key" OPENAI_BASE_URL="https://api.ai.it.cornell.edu" streamlit run chat_with_pdf.py
```

### Step 2: Run the Application

```bash
streamlit run chat_with_pdf.py
```

### Step 3: Use the Application

1. **Upload Documents**: Click "Browse files" and select one or more `.txt` or `.pdf` files
2. **Wait for Processing**: The app will chunk documents and create embeddings
3. **Ask Questions**: Type questions about your documents in the chat input
4. **Get Answers**: Receive AI-generated responses based solely on document content
5. **Follow-up Questions**: Continue the conversation - the bot remembers context

---

## Modifications to Provided Setup

### Changes to `requirements.txt`

**Added dependencies:**
```txt
langchain-chroma==1.0.0  # Vector database integration for LangChain
chromadb==1.2.2          # Vector storage backend
```

**Modified dependencies:**
```txt
pandas>=2.3.3  # Updated from pandas==2 to fix numpy compatibility issue
```

**Reason for changes:**
- `langchain-chroma` and `chromadb` were not in the original template but are required for the RAG vector database
- `pandas` upgrade fixes runtime error: `ValueError: numpy.dtype size changed`

### Changes to `.devcontainer/devcontainer.json`


**Security**: API keys are set at runtime via `export` commands, never committed to the repository.

---

## Implementation Details

### RAG Pipeline Components

1. **Document Loading** ([chat_with_pdf.py:49-60](chat_with_pdf.py#L49-L60))
   - TextLoader for `.txt` files
   - PyPDFLoader for `.pdf` files

2. **Chunking Strategy** ([chat_with_pdf.py:64-67](chat_with_pdf.py#L64-L67))
   - Chunk size: 500 characters
   - Chunk overlap: 50 characters
   - Method: RecursiveCharacterTextSplitter

3. **Embeddings & Vector Store** ([chat_with_pdf.py:107-110](chat_with_pdf.py#L107-L110))
   - Model: `openai.text-embedding-3-large`
   - Database: ChromaDB (in-memory)

4. **Retrieval** ([chat_with_pdf.py:119-123](chat_with_pdf.py#L119-L123))
   - Search type: Similarity search
   - Top-k: 12 most relevant chunks

5. **Generation** ([chat_with_pdf.py:144-148](chat_with_pdf.py#L144-L148))
   - Model: `openai.gpt-4o` (Cornell API format)
   - Temperature: 0.2 (for more factual responses)
   - Streaming: Real-time response generation

### Conversation History

The application maintains full conversation history and passes it to the LLM for context-aware responses ([chat_with_pdf.py:131-141](chat_with_pdf.py#L131-L141)), enabling natural follow-up questions like:
- User: "What is RAG?"
- Bot: [detailed answer]
- User: "Can you make that shorter?"
- Bot: [condensed version]

---

## Testing the Application

### Recommended Test Flow

1. **Basic upload**: Upload `data/RAG_source.txt`
2. **Simple question**: "What is Zelomax?"
3. **Multi-part question**: "What are the side effects and contraindications?"
4. **Follow-up**: "Can you summarize that in bullet points?"
5. **Out-of-scope question**: "What is the capital of France?" (should say "I don't have enough information")
6. **Multiple documents**: Upload multiple PDFs and .txt files and ask cross-document questions

### Expected Behavior

- Answers should be detailed and well-structured
- Answers should only use document content
- Should handle follow-up questions with context
- Should gracefully decline questions outside document scope
- Should process multiple documents seamlessly

---
