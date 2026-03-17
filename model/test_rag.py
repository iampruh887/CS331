#!/usr/bin/env python3
"""
Test script for RAG functionality
"""
import asyncio
from pathlib import Path
from rag_service import RAGService

async def test_rag():
    print("=== Testing RAG Service ===\n")
    
    # Initialize RAG service
    rag = RAGService(docs_dir="docs", confidence_threshold=0.65)
    
    if not rag.is_available():
        print("❌ RAG service not available")
        print("   Reasons:")
        print("   - No documents in docs/ folder")
        print("   - sentence-transformers not installed")
        print("   - Embedding model failed to load")
        return
    
    print(f"✓ RAG service initialized")
    print(f"  Documents indexed: {len(rag.documents)}")
    print(f"  Confidence threshold: {rag.confidence_threshold}")
    print()
    
    # Test queries
    test_queries = [
        "What is this system about?",
        "What tools are available?",
        "How does RAG work?",
        "What is the capital of France?",  # Should have low confidence
    ]
    
    for query in test_queries:
        print(f"Query: {query}")
        result = rag.retrieve(query, top_k=2)
        
        if result and result.get('used'):
            print(f"  ✓ Retrieved (confidence: {result['confidence']:.2f})")
            print(f"  Sources: {', '.join(result['sources'])}")
            print(f"  Top passage: {result['passages'][0]['text'][:100]}...")
        else:
            reason = result.get('reason', 'Unknown') if result else 'No result'
            print(f"  ✗ Not used - {reason}")
        print()

if __name__ == "__main__":
    asyncio.run(test_rag())
