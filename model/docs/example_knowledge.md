# Example Knowledge Base

This is a sample document to demonstrate the RAG capabilities.

## About This System

This parsing engine is an AI agent built with Google's Agent Development Kit (ADK) and uses the Phi-4-mini model running locally via Ollama. The system is designed to minimize hallucinations through:

1. Retrieval-Augmented Generation (RAG)
2. Mandatory tool usage for factual queries
3. Low temperature settings (0.1) for deterministic outputs
4. Explicit source citation requirements
5. Confidence thresholding for retrieved information

## System Capabilities

The agent has three primary tools:

- **search_knowledge_base**: Searches documents in the docs/ folder using semantic similarity
- **gettime**: Returns current date and time information
- **get_system_metrics**: Provides CPU, memory, and disk usage statistics

## Technical Stack

- Model: Phi-4-mini (Microsoft's compact language model)
- Serving: Ollama (local inference)
- Orchestration: Google ADK
- Embeddings: sentence-transformers (all-MiniLM-L6-v2)
- RAG: Custom implementation with cosine similarity

## Anti-Hallucination Measures

The system implements multiple layers of protection:

1. Tool-first approach: Agent must call tools before answering factual questions
2. Confidence scoring: Retrieved information must exceed 0.65 similarity threshold
3. Source attribution: All factual claims must cite sources
4. Explicit uncertainty: Agent states when information is unavailable
5. Low temperature: Reduces creative but potentially inaccurate responses

## Usage

Run in interactive mode:
```bash
python main.py
```

Run single query:
```bash
python main.py "What time is it?"
```

All interactions are logged to `agent_logs.json` for analysis and improvement.
