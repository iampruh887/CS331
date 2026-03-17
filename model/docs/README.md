# Knowledge Base Documents

This folder contains documents that the RAG (Retrieval-Augmented Generation) system will index and use to ground the agent's responses.

## Supported Formats
- `.txt` - Plain text files
- `.md` - Markdown files
- `.json` - JSON files
- `.csv` - CSV files

## How It Works

1. The RAG service automatically indexes all documents in this folder when the agent starts
2. Documents are split into chunks (~500 characters each)
3. Each chunk is embedded using the `all-MiniLM-L6-v2` model
4. When a user asks a question, the system:
   - Embeds the query
   - Finds the most relevant document chunks using cosine similarity
   - Returns results only if confidence score > 0.65 (configurable)
   - The agent uses these grounded facts to answer

## Best Practices

- Keep documents focused and well-organized
- Use clear, factual language
- Include source attribution in documents when possible
- Update documents regularly to keep information current
- Remove outdated documents to prevent stale information

## Configuration

Edit `rag_service.py` to adjust:
- `confidence_threshold` (default: 0.65) - Minimum similarity score to use retrieved info
- `max_length` (default: 500) - Maximum chunk size in characters
- `top_k` (default: 3) - Number of relevant chunks to retrieve

## Example Documents

Add documents like:
- Company policies
- Technical specifications
- Product documentation
- FAQ documents
- Procedure manuals
- Knowledge base articles
