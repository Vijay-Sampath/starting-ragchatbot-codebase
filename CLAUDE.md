# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **tool-based agentic RAG system** for answering questions about course materials. It uses ChromaDB for vector storage, Anthropic's Claude API for AI generation with tool calling, and provides a web-based chat interface.

**Key architectural pattern**: Claude autonomously decides when to search using tool calling, rather than retrieving for every query. This "agentic RAG" pattern makes the system more efficient and intelligent.

## ⚠️ Critical: Package Management

**ALWAYS use `uv` for all Python operations in this project. NEVER use `pip` directly.**

This project uses `uv` as its package manager (configured in `pyproject.toml`). Using `pip` will cause dependency conflicts and break the environment.

**Correct commands:**
- **Install/sync dependencies**: `uv sync` (reads from `pyproject.toml` and `uv.lock`)
- **Add a new dependency**: `uv add <package>` (updates `pyproject.toml` and `uv.lock`)
- **Remove a dependency**: `uv remove <package>` (updates `pyproject.toml` and `uv.lock`)
- **Run Python files**: `uv run python script.py` (NOT `python script.py`)
- **Run any Python command**: `uv run <command>`
- **Run server**: `uv run uvicorn app:app --reload --port 8000`
- **Run tests** (if added): `uv run pytest`

**Dependency management workflow:**
1. To add a new package: `uv add anthropic` (not `pip install anthropic`)
2. Dependencies are tracked in `pyproject.toml` (human-readable) and `uv.lock` (exact versions)
3. After pulling changes: `uv sync` to update your environment
4. Both `pyproject.toml` and `uv.lock` should be committed to git

**Never run:**
- ❌ `pip install ...` - breaks uv's dependency resolution
- ❌ `pip freeze > requirements.txt` - this project doesn't use requirements.txt
- ❌ `python script.py` - use `uv run python script.py`
- ❌ `uvicorn app:app` - use `uv run uvicorn app:app`
- ❌ Manually edit `pyproject.toml` dependencies - use `uv add/remove`

## Setup & Running

### Installation
```bash
# Install uv package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Create .env file with your Anthropic API key
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

### Running the Application
```bash
# Option 1: Use the startup script
./run.sh

# Option 2: Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

**Access**:
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

**Important**: Python 3.13 is required (specified in `.python-version`)

## Architecture Overview

### Request Flow
```
User Query → FastAPI (app.py) → RAG System → AI Generator → Claude API
                                      ↓
                                 Tool Manager → Vector Store → ChromaDB
                                      ↓
                                Session Manager
```

### Core Components

**app.py** - FastAPI entry point
- `/api/query` - Process user queries
- `/api/courses` - Get course statistics
- Startup: Auto-loads documents from `../docs` folder

**rag_system.py** - Main orchestrator
- Coordinates all components
- Single entry point: `query(query, session_id)`
- Manages conversation flow and source tracking

**ai_generator.py** - Claude API integration
- Two-call pattern for tool use:
  1. First call: Claude decides whether to search
  2. Second call: Claude generates answer using search results
- System prompt guides agentic behavior (lines 8-30)
- Configuration: model, temperature, max_tokens (lines 38-42)

**vector_store.py** - ChromaDB interface
- **Dual collection architecture**:
  - `course_catalog`: Course metadata for name matching
  - `course_content`: Chunked course material for retrieval
- **Two-stage search** (lines 61-100):
  1. Resolve course name via semantic search
  2. Search content with course/lesson filters

**document_processor.py** - Document parsing and chunking
- Parses structured course documents (title, instructor, lessons)
- Sentence-based chunking with overlap (800 chars, 100 overlap)
- Context enrichment: adds course/lesson metadata to chunks

**search_tools.py** - Tool definitions and execution
- `CourseSearchTool`: Search with optional course/lesson filtering
- Tool manager handles registration and execution
- Tracks sources for UI display

**session_manager.py** - Conversation history
- In-memory storage (not persisted across restarts)
- Stores last `MAX_HISTORY` exchanges (default: 2)
- History provided to Claude for context

**config.py** - Configuration settings
- Model: `claude-sonnet-4-20250514`
- Embedding model: `all-MiniLM-L6-v2`
- Chunking: 800 chars with 100 char overlap
- Max results: 5 chunks per search

**models.py** - Pydantic data models
- `Course`, `Lesson`, `CourseChunk` for document structure
- `SearchResults` for vector search responses

## Key Architectural Decisions

### 1. Agentic RAG with Tool Calling

Claude decides when to search, not hardcoded retrieval. Benefits:
- General questions answered without unnecessary searches
- Reduces latency and cost
- System prompt guides tool usage: "One search per query maximum"

**Implementation**: ai_generator.py handles tool use detection (lines 79-87) and execution (lines 89-135)

### 2. Dual Collection Architecture

Separate collections for different purposes:
- **course_catalog**: Enables fuzzy course name matching ("MCP" → full title)
- **course_content**: Actual chunked material with metadata filters

**Why**: Course names need different embedding strategy than content search

### 3. Semantic Course Name Resolution

Vector search resolves partial course names to full titles:
```python
# User provides: "MCP"
# System resolves to: "MCP: Build Rich-Context AI Apps..."
# Used as filter for content search
```

**Implementation**: `_resolve_course_name()` in vector_store.py:102-116

### 4. Chunk Context Enrichment

Each chunk includes course/lesson metadata in the text:
```
"Lesson 2 content: [actual chunk text]"
"Course Building with MCP Lesson 2 content: [actual chunk text]"
```

**Why**: Improves retrieval relevance and provides context to Claude

### 5. Sentence-Based Chunking

Chunks by complete sentences rather than fixed character counts:
- Preserves semantic boundaries
- Uses regex to handle abbreviations correctly
- 100-char overlap maintains continuity

**Implementation**: `chunk_text()` in document_processor.py:25-91

## Document Format

Course documents in `docs/` folder must follow this structure:
```
Course Title: [Course Name]
Course Link: [URL]
Course Instructor: [Name]

Lesson 0: [Lesson Title]
Lesson Link: [URL]
[Lesson content...]

Lesson 1: [Lesson Title]
```

New documents placed in `docs/` are automatically processed on startup.

## Common Modification Points

### Adding a New Tool

1. Create tool class inheriting from `Tool` in search_tools.py
2. Implement `get_tool_definition()` and `execute()` methods
3. Register in RAGSystem: `self.tool_manager.register_tool(new_tool)`

### Modifying Search Behavior

- Search logic: vector_store.py `search()` method (lines 61-100)
- Filter building: `_build_filter()` (lines 118-133)
- Course resolution: `_resolve_course_name()` (lines 102-116)

### Changing AI Behavior

- System prompt: ai_generator.py lines 8-30
- Model/temperature: config.py lines 13, 39
- Token limit: ai_generator.py line 40

### Modifying Chunking

- Chunk size/overlap: config.py lines 19-20
- Chunking algorithm: document_processor.py `chunk_text()` (lines 25-91)

## Configuration Tuning

Key parameters in config.py:
- `CHUNK_SIZE` (800): Balance between context and precision
- `CHUNK_OVERLAP` (100): Ensures continuity between chunks
- `MAX_RESULTS` (5): More results = more context but longer prompts
- `MAX_HISTORY` (2): Number of conversation exchanges to remember

## Database Structure

### course_catalog Collection
- **Documents**: Course titles
- **Metadata**: `{title, instructor, course_link, lessons_json, lesson_count}`
- **IDs**: Course title (unique)

### course_content Collection
- **Documents**: Text chunks with context
- **Metadata**: `{course_title, lesson_number, chunk_index}`
- **IDs**: `{course_title}_{chunk_index}`

Stored in `backend/chroma_db/` directory (created automatically).

## API Endpoints

### POST /api/query
Process user query with conversation context.

**Request**:
```json
{
  "query": "What is taught in lesson 2?",
  "session_id": "session_abc123"  // optional
}
```

**Response**:
```json
{
  "answer": "In lesson 2, you'll learn about...",
  "sources": ["Course Name - Lesson 2"],
  "session_id": "session_abc123"
}
```

### GET /api/courses
Get course statistics.

**Response**:
```json
{
  "total_courses": 3,
  "course_titles": ["Course 1", "Course 2", "Course 3"]
}
```

## Debugging Tips

1. **Check ChromaDB**: Look for `backend/chroma_db/` folder and verify collections exist
2. **Conversation history**: Add logging in session_manager.py
3. **Tool execution**: Add logging in search_tools.py `execute_tool()`
4. **Vector search**: Add logging in vector_store.py `search()`
5. **API issues**: Check FastAPI docs at http://localhost:8000/docs

## Source Tracking Pattern

Tools track sources during execution, which are extracted after AI generation:
1. Tool executes search, stores sources in `last_sources`
2. RAG system retrieves via `get_last_sources()` after generation
3. Sources reset after each query to prevent carryover

**Implementation**: search_tools.py:25, 103-112 and rag_system.py:129-133

## Development Features

- **CORS wide open**: Allows testing from any origin (app.py:27)
- **Auto-reload**: `--reload` flag enables hot reloading
- **No-cache headers**: Static files always fresh (app.py:107-115)
- **API docs**: Auto-generated at `/docs` endpoint

## Important Notes

- **Session persistence**: In-memory only (lost on restart). For production, replace with Redis/database.
- **Startup behavior**: Automatically loads documents from `../docs`, skips existing courses.
- **Frontend**: Pure HTML/JS with marked.js for markdown rendering.
- **Embedding model**: Downloads automatically on first run (all-MiniLM-L6-v2).
