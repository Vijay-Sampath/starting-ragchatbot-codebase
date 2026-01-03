# RAG Chatbot Query Flow Diagram

## Complete User Query Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend as Frontend<br/>(script.js)
    participant API as FastAPI<br/>(app.py)
    participant RAG as RAG System<br/>(rag_system.py)
    participant Session as Session Manager<br/>(session_manager.py)
    participant AI as AI Generator<br/>(ai_generator.py)
    participant Claude as Claude API
    participant Tools as Tool Manager<br/>(search_tools.py)
    participant Vector as Vector Store<br/>(vector_store.py)
    participant Chroma as ChromaDB

    %% Phase 1: User Input
    User->>Frontend: Types query & clicks send
    activate Frontend
    Frontend->>Frontend: Disable input, show loading

    %% Phase 2: HTTP Request
    Frontend->>API: POST /api/query<br/>{query, session_id}
    activate API

    %% Phase 3: Session Management
    API->>RAG: query(query, session_id)
    activate RAG
    RAG->>Session: get_conversation_history(session_id)
    activate Session
    Session-->>RAG: Previous messages
    deactivate Session

    %% Phase 4: AI Generation Setup
    RAG->>AI: generate_response(query, history, tools)
    activate AI
    AI->>AI: Build system prompt + history

    %% Phase 5: First Claude API Call
    AI->>Claude: messages.create()<br/>with search tool definition
    activate Claude
    Claude->>Claude: Analyzes query<br/>Decides to use search tool
    Claude-->>AI: tool_use response<br/>{name: "search", input: {...}}
    deactivate Claude

    %% Phase 6: Tool Execution
    AI->>Tools: execute_tool("search", query, course, lesson)
    activate Tools

    %% Phase 7: Vector Search - Course Resolution
    Tools->>Vector: search(query, course_name, lesson_number)
    activate Vector
    Vector->>Chroma: query course_catalog<br/>for course name matching
    activate Chroma
    Chroma-->>Vector: Best matching course title
    deactivate Chroma

    %% Phase 8: Vector Search - Content Search
    Vector->>Vector: Build filter<br/>{course_title, lesson_number}
    Vector->>Chroma: query course_content<br/>with filter
    activate Chroma
    Chroma->>Chroma: Vector similarity search<br/>on embeddings
    Chroma-->>Vector: Top 5 relevant chunks
    deactivate Chroma
    Vector-->>Tools: SearchResults with metadata
    deactivate Vector

    %% Phase 9: Format Results
    Tools->>Tools: Format results<br/>Add course/lesson headers<br/>Track sources
    Tools-->>AI: Formatted search results
    deactivate Tools

    %% Phase 10: Second Claude API Call
    AI->>Claude: messages.create()<br/>with tool_result
    activate Claude
    Claude->>Claude: Analyzes retrieved content<br/>Synthesizes answer<br/>Cites sources
    Claude-->>AI: Final text response
    deactivate Claude
    AI-->>RAG: Generated answer
    deactivate AI

    %% Phase 11: Collect Sources & Update Session
    RAG->>Tools: get_last_sources()
    activate Tools
    Tools-->>RAG: ["Course - Lesson 1", ...]
    deactivate Tools

    RAG->>Session: add_exchange(session_id, query, answer)
    activate Session
    Session->>Session: Store in conversation history
    deactivate Session

    RAG-->>API: (answer, sources)
    deactivate RAG

    %% Phase 12: HTTP Response
    API->>API: Build QueryResponse<br/>{answer, sources, session_id}
    API-->>Frontend: JSON response
    deactivate API

    %% Phase 13: Display Response
    Frontend->>Frontend: Update session_id<br/>Remove loading animation<br/>Parse markdown<br/>Render message + sources
    Frontend->>Frontend: Re-enable input
    deactivate Frontend
    Frontend-->>User: Display answer with sources
```

## Architecture Components

### Frontend Layer
- **index.html**: UI structure with chat interface
- **script.js**: Event handling, API calls, message rendering
- **Technologies**: Vanilla JavaScript, Marked.js for markdown

### Backend API Layer
- **app.py**: FastAPI endpoints, request/response models
- **Entry point**: POST `/api/query`

### RAG Orchestration Layer
- **rag_system.py**: Main orchestrator
- **session_manager.py**: Conversation history management
- **ai_generator.py**: Claude API integration

### Tool & Search Layer
- **search_tools.py**: Tool definitions and execution
- **vector_store.py**: Vector search interface
- **ChromaDB**: Vector database with embeddings

### Document Processing Layer
- **document_processor.py**: Text chunking, metadata extraction
- **models.py**: Data models (Course, Lesson, Chunk)

## Key Data Flows

### Request Format
```json
{
  "query": "What is taught in lesson 2 of the MCP course?",
  "session_id": "session_abc123"
}
```

### Tool Call Format (Claude → Backend)
```json
{
  "name": "search",
  "input": {
    "query": "lesson 2 MCP course content",
    "course_name": "MCP",
    "lesson_number": 2
  }
}
```

### Tool Result Format (Backend → Claude)
```
[Building with MCP - Lesson 2]
Lesson 2 content: In this lesson, you'll learn about...

[Building with MCP - Lesson 2]
Course Building with MCP Lesson 2 content: The key concepts include...
```

### Response Format
```json
{
  "answer": "In lesson 2 of the Building with MCP course...",
  "sources": [
    "Building with MCP - Lesson 2"
  ],
  "session_id": "session_abc123"
}
```

## System Characteristics

### 🎯 Agentic RAG Pattern
- Claude autonomously decides when to search
- Not all queries trigger retrieval
- Tool-based retrieval instead of forced retrieval

### 💬 Stateful Conversations
- Server-side session management
- Conversation history included in each Claude call
- Enables follow-up questions and context awareness

### 🔍 Two-Stage Search
1. **Course Resolution**: Semantic search on course catalog
2. **Content Search**: Filtered vector search on course content

### ⚡ Performance Optimizations
- Single search per query (tool use limit)
- ChromaDB persistent storage (no re-embedding)
- Efficient chunking with overlaps (800 chars, 100 overlap)

### 🏗️ Dual Collection Architecture
- **course_catalog**: High-level course metadata for name matching
- **course_content**: Chunked course material for content retrieval
