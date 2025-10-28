# Reference Log - Assignment 1

## External Sources and Tools

### Documentation & Tutorials
1. **LangChain Documentation**
   - URL: https://python.langchain.com/docs/
   - Used for: RAG pipeline implementation, document loaders, text splitters, vector stores
   - Sections: Retrieval, Embeddings, Chat models, Document loaders
   - Specific components: TextLoader, PyPDFLoader, RecursiveCharacterTextSplitter, Chroma, OpenAIEmbeddings

2. **Streamlit Documentation**
   - URL: https://docs.streamlit.io/
   - Used for: File uploader, chat interface, session state management
   - Sections: Chat elements, File uploader widget, Session state
   - Specific features: st.file_uploader with accept_multiple_files, st.chat_message, st.session_state

3. **ChromaDB Documentation**
   - URL: https://docs.trychroma.com/
   - Used for: Vector database setup and similarity search

4. **OpenAI API Documentation**
   - URL: https://platform.openai.com/docs/guides/conversation-state
   - URL: https://platform.openai.com/docs/api-reference/chat
   - Used for: Implementing conversation history with chat completions API
   - Specific pattern: Maintaining conversation by passing messages array with role/content structure

5. **Community Resources**
   - Stack Overflow: "How to save chat history with OpenAI API"
   - URL: https://stackoverflow.com/questions/77987824/how-to-save-chat-history-with-openai-api
   - Used for: Understanding how to implement conversation history in practice

### Class Materials
1. **Lecture Notes (Notes 1001.pdf)**
   - Topics: RAG overview, embeddings, vector search, chunking strategies
   - Used for: Understanding RAG pipeline architecture

2. **Lecture Notes (NotesOct7.pdf)**
   - Topics: LangChain implementation, LangGraph workflow, prompt templates
   - Used for: Code structure and API usage patterns

3. **Class Notebook (langgraph_chroma_retreiver.ipynb)**
   - Used as reference for: Document loading, chunking, embeddings, retrieval
   - Adapted for Streamlit integration

### Code References
- **Starter template**: `chat_with_pdf.py` (provided in assignment1 branch)
- **Reference notebook**: `langgraph_chroma_retreiver.ipynb` (assignment1 branch)

## GenAI Usage

### Claude Code (Anthropic)
- **Purpose**: Coding assistant and development support tool

- **My Development Process with AI Assistance**:
  1. **Implementation Planning**: I analyzed the rubric requirements and class materials to plan my approach; AI helped structure the implementation steps

  2. **Code Development**: I wrote the application by adapting code from class materials (lecture notebook, notes), using AI to help refine and optimize the implementation

  3. **Prompt Engineering**: I specified that answers must be grounded in documents only and structured well; AI helped me formalize these requirements into the prompt template

  4. **Problem Solving**: When I identified issues during testing (e.g., conversation history not working), I asked AI to find relevant documentation; AI located OpenAI API examples which I then implemented

  5. **Debugging**: I identified errors during testing; AI assisted in finding solutions:
     - Dependencies compatibility (pandas version)
     - Code improvements for document loading
     - Analysed the security so that API key is not exposed 

  6. **Documentation**: I outlined what needed to be documented; AI helped write comprehensive README and ref-log content 

- **Specific Examples**:
  - **Conversation history**: I identified this feature was needed after testing; asked AI to find resources; AI found OpenAI documentation; I implemented the pattern
  - **Grounding requirements**: I specified the chatbot should only answer from documents and provide structured responses; AI helped format this into detailed prompt rules
  - **Code optimization**: I wrote initial implementations based on class materials and reference notebook; AI suggested improvements for code structure and efficiency

- **Why I Used AI**:
  - Accelerated finding relevant documentation and examples
  - Optimize code and made it efficient while following best practices
  - Assisted in debugging errors I encountered during testing
  - Supported writing clear documentation
  - All AI suggestions were reviewed and tested by me before use

### My Independent Work
- **Understanding concepts**: Learned RAG, embeddings, and vector search from lectures
- **Technical decisions**: Chose chunking parameters (500/50), retriever k value (12), based on lecture discussions
- **Code foundation**: Used langgraph_chroma_retriever notebook and lecture notes as primary code references
- **Testing & validation**: Tested all functionality, identified bugs, verified features work
- **Iterative improvement**: Tested chatbot behavior, identified needed features (conversation history), requested specific improvements
- **Integration**: Combined patterns from multiple sources (LangChain, Streamlit, OpenAI) based on assignment needs
