# Parsing Engine with RAG and Anti-Hallucination Features

An intelligent AI agent built with Google's Agent Development Kit (ADK) that uses Retrieval-Augmented Generation (RAG) to minimize hallucinations and provide grounded, factual responses.

## Quick Start

1. Ensure that ollama is installed and configured
2. `ollama pull phi4-mini`
3. create a virtual environment
   `python3 -m venv .venv` (Linux)
   `python -m venv .venv` (Windows)
4. install requirements
   `pip install -r requirements.txt`
5. run single query
   `python main.py <query>`
6. run interactive mode
   `python main.py`

## Tools and Functionalities

The parsing engine now includes:
- **search_knowledge_base** - RAG-powered semantic search over docs/ folder
- **get_system_metrics** - CPU, memory, and disk usage statistics
- **gettime** - Current date and time information

## RAG (Retrieval-Augmented Generation)

### What's New
The agent now includes a RAG system that:
- Automatically indexes documents from the `docs/` folder
- Uses semantic search to find relevant information
- Only uses retrieved information if confidence > 65%
- Cites sources in responses
- Reduces hallucinations by grounding answers in actual documents

### Adding Documents
Simply place documents in the `docs/` folder:
```bash
cp your_document.txt docs/
cp your_notes.md docs/
```

Supported formats: `.txt`, `.md`, `.json`, `.csv`

### How It Works
1. Documents are split into ~500 character chunks
2. Each chunk is embedded using sentence-transformers
3. When you ask a question, the system finds the most relevant chunks
4. If confidence is high enough (>65%), the agent uses that information
5. The agent cites the source document in its response

## Anti-Hallucination Features

The agent implements multiple strategies to reduce false information:

1. **Tool-First Approach**: Agent must call tools before answering factual questions
2. **Low Temperature (0.1)**: Reduces creative but potentially inaccurate responses
3. **Confidence Thresholding**: Retrieved info must be >65% similar to be used
4. **Source Attribution**: Agent cites sources for all factual claims
5. **Explicit Uncertainty**: States "I don't have that information" when unsure
6. **Response Length Limits**: Max 512 tokens to prevent rambling

## Configuration

### Adjust RAG Confidence Threshold
Edit `rag_service.py`:
```python
rag_service = RAGService(
    docs_dir="docs",
    confidence_threshold=0.70  # Higher = stricter matching
)
```

### Adjust Model Temperature
Edit `main.py`:
```python
llm_model = LiteLlm(
    model="ollama_chat/phi4-mini",
    api_base="http://localhost:11434",
    temperature=0.1,  # Lower = more factual, higher = more creative
    max_tokens=512
)
```

## Example Usage

```bash
# Ask about system info (uses get_system_metrics tool)
python main.py "How is the system performing?"

# Ask about time (uses gettime tool)
python main.py "What time is it?"

# Ask about documents (uses RAG search_knowledge_base tool)
python main.py "What is this system about?"

# Interactive mode
python main.py
> What capabilities does this agent have?
> What time is it?
> exit
```

## Logging

All interactions are logged to `agent_logs.json` with:
- Tool used
- Timestamp
- User input
- Agent response

## Architecture

```
User Query → Agent (ADK) → Tool Selection
                              ├─→ search_knowledge_base → RAG Service → Documents
                              ├─→ gettime → System Time
                              └─→ get_system_metrics → System Stats
                           → Grounded Response → Log
```

## Troubleshooting

**RAG not working?**
- Check if `docs/` folder has documents
- Install: `pip install sentence-transformers`
- Check logs for errors

**Ollama connection issues?**
- Verify Ollama is running: `ollama list`
- Test: `ollama run phi4-mini "Hello"`

**Low confidence scores?**
- Add more relevant documents to `docs/`
- Lower threshold in `rag_service.py`

## References

- [Google ADK](https://github.com/google/genai-adk)
- [Ollama](https://ollama.ai)
- [Sentence Transformers](https://www.sbert.net)