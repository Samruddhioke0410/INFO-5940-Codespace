import streamlit as st
import os
from openai import OpenAI
from os import environ
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate

client = OpenAI(
	api_key=os.environ["API_KEY"],
	base_url="https://api.ai.it.cornell.edu",
)

# Initialize LangChain LLM for RAG (uses OPENAI_API_KEY and OPENAI_BASE_URL from environment)
llm = ChatOpenAI(
    model="openai.gpt-4o",
    temperature=0.2
)

# RAG Prompt Template - ensures grounding while allowing quality answers
prompt_template = PromptTemplate.from_template("""You are a helpful assistant answering questions about uploaded documents.

IMPORTANT RULES:
1. Answer ONLY using information from the context below - do not use any external knowledge
2. If the context doesn't contain enough information, say "I don't have enough information in the document to answer this question" and explain what's missing
3. Provide comprehensive, well-structured answers:
   - Use bullet points for lists or multiple items
   - Use paragraphs for explanations
   - Quote relevant parts when helpful
4. Be clear, accurate, and thorough - don't artificially limit your answer length if the question requires detail

Context from document:
{context}

Question: {question}

Answer:""")

st.title("📝 RAG Chat with Documents")
uploaded_files = st.file_uploader(
    "Upload document(s)",
    type=["txt", "pdf"],
    accept_multiple_files=True
)

# Function to load documents using LangChain loaders
def load_document(uploaded_file):
    """Load document using appropriate LangChain loader based on file type"""
    temp_file = f"temp_upload.{uploaded_file.name.split('.')[-1]}"
    with open(temp_file, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if uploaded_file.name.endswith('.txt'):
        loader = TextLoader(temp_file)
    elif uploaded_file.name.endswith('.pdf'):
        loader = PyPDFLoader(temp_file)

    return loader.load()

# Initialize text splitter for chunking
# Using 500 char chunks with 50 char overlap for better context preservation
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

# Initialize session state for documents, chunks, and vectorstore
if "documents" not in st.session_state:
    st.session_state["documents"] = None
if "chunks" not in st.session_state:
    st.session_state["chunks"] = None
if "vectorstore" not in st.session_state:
    st.session_state["vectorstore"] = None

question = st.chat_input(
    "Ask something about the document(s)",
    disabled=not uploaded_files,
)

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Upload your document(s) and ask me anything about them!"}]

# Display uploaded files info
if uploaded_files:
    st.sidebar.header("Uploaded Documents")
    for file in uploaded_files:
        st.sidebar.text(f"📄 {file.name}")

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if question and uploaded_files:
    # Load all documents using LangChain if not already loaded
    if st.session_state.documents is None:
        with st.spinner("Loading and processing document(s)..."):
            # Load all uploaded documents
            all_documents = []
            for uploaded_file in uploaded_files:
                all_documents.extend(load_document(uploaded_file))

            st.session_state.documents = all_documents
            # Split all documents into chunks for efficient retrieval
            st.session_state.chunks = text_splitter.split_documents(st.session_state.documents)
            # Create vector store from all chunks
            st.session_state.vectorstore = Chroma.from_documents(
                documents=st.session_state.chunks,
                embedding=OpenAIEmbeddings(model="openai.text-embedding-3-large")
            )
            st.success(f"✅ Loaded {len(uploaded_files)} document(s) with {len(st.session_state.chunks)} chunks")

    # Append the user's question to the messages
    st.session_state.messages.append({"role": "user", "content": question})
    st.chat_message("user").write(question)

    with st.chat_message("assistant"):
        # RAG: Retrieve relevant chunks using similarity search
        retriever = st.session_state.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 12}
        )
        retrieved_docs = retriever.invoke(question)

        # Format retrieved context
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])

        # Generate prompt with retrieved context
        prompt = prompt_template.invoke({"context": context, "question": question})

        # Build message history including system prompt and conversation history
        messages = [
            {"role": "system", "content": prompt.text},
        ]

        # Add conversation history (excluding current question which is already added above)
        for msg in st.session_state.messages[:-1]:  # Exclude the question we just added
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current question
        messages.append({"role": "user", "content": question})

        # Stream response from LLM using RAG with conversation history
        stream = client.chat.completions.create(
            model="openai.gpt-4o",
            messages=messages,
            stream=True
        )
        response = st.write_stream(stream)

    # Append the assistant's response to the messages
    st.session_state.messages.append({"role": "assistant", "content": response})