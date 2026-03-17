"""
RAG Service using Pathway for document retrieval and grounding.
Monitors the docs/ folder and provides retrieval capabilities.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logging.warning("sentence-transformers not available. RAG will be disabled.")


class RAGService:
    """
    Simple RAG service that indexes documents from docs/ folder
    and provides retrieval with confidence scoring.
    """
    
    def __init__(self, docs_dir: str = "docs", confidence_threshold: float = 0.65):
        self.docs_dir = Path(docs_dir)
        self.confidence_threshold = confidence_threshold
        self.documents = []
        self.embeddings = None  # Will be numpy array
        self.model = None
        self.enabled = False
        
        if EMBEDDINGS_AVAILABLE:
            try:
                # Use a lightweight model for local inference
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self.enabled = True
                logging.info("RAG Service initialized with all-MiniLM-L6-v2")
            except Exception as e:
                logging.error(f"Failed to load embedding model: {e}")
                self.enabled = False
        
        if self.enabled:
            self._index_documents()
    
    def _index_documents(self):
        """Index all documents in the docs directory."""
        if not self.docs_dir.exists():
            logging.warning(f"Docs directory {self.docs_dir} does not exist")
            return
        
        # Support common text formats
        supported_extensions = ['.txt', '.md', '.json', '.csv']
        doc_files = []
        
        for ext in supported_extensions:
            doc_files.extend(self.docs_dir.glob(f'**/*{ext}'))
        
        if not doc_files:
            logging.info(f"No documents found in {self.docs_dir}")
            return
        
        self.documents = []
        texts_to_embed = []
        
        for doc_path in doc_files:
            try:
                content = doc_path.read_text(encoding='utf-8')
                # Split into chunks (simple paragraph-based splitting)
                chunks = self._split_into_chunks(content, max_length=500)
                
                for i, chunk in enumerate(chunks):
                    if chunk.strip():
                        self.documents.append({
                            'source': doc_path.name,
                            'chunk_id': i,
                            'text': chunk.strip(),
                            'path': str(doc_path)
                        })
                        texts_to_embed.append(chunk.strip())
                        
            except Exception as e:
                logging.error(f"Failed to read {doc_path}: {e}")
        
        if texts_to_embed and self.model:
            try:
                # Encode all texts and ensure it's a numpy array
                embeddings_list = self.model.encode(texts_to_embed, show_progress_bar=False)
                self.embeddings = np.array(embeddings_list)
                logging.info(f"Indexed {len(self.documents)} document chunks from {len(doc_files)} files")
                print(f"[RAG] Indexed {len(self.documents)} chunks, embeddings shape: {self.embeddings.shape}")
            except Exception as e:
                logging.error(f"Failed to create embeddings: {e}")
                self.enabled = False
    
    def _split_into_chunks(self, text: str, max_length: int = 500) -> List[str]:
        """Split text into chunks by paragraphs or sentences."""
        # Split by double newlines (paragraphs)
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            if len(current_chunk) + len(para) < max_length:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If no double newlines, try splitting by single newlines
        if not chunks and text.strip():
            lines = text.split('\n')
            current_chunk = ""
            for line in lines:
                if len(current_chunk) + len(line) < max_length:
                    current_chunk += line + "\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = line + "\n"
            if current_chunk:
                chunks.append(current_chunk.strip())
        
        # If still no chunks, just return the whole text
        if not chunks and text.strip():
            chunks = [text.strip()]
        
        return chunks
    
    def retrieve(self, query: str, top_k: int = 3) -> Optional[Dict]:
        """
        Retrieve relevant documents for a query.
        
        Returns:
            Dict with 'passages', 'sources', 'confidence', and 'used' flag
            or None if RAG is disabled or confidence is too low
        """
        if not self.enabled or not self.documents or self.model is None:
            return {
                'used': False,
                'reason': 'RAG service not available or no documents indexed',
                'passages': [],
                'sources': [],
                'confidence': 0.0
            }
        
        if self.embeddings is None or len(self.embeddings) == 0:
            return {
                'used': False,
                'reason': 'No embeddings available',
                'passages': [],
                'sources': [],
                'confidence': 0.0
            }
        
        try:
            # Encode query
            query_embedding = self.model.encode([query], show_progress_bar=False)[0]
            
            # Compute cosine similarities using vectorized operations
            # Normalize query embedding
            query_norm = query_embedding / np.linalg.norm(query_embedding)
            
            # Normalize document embeddings
            doc_norms = self.embeddings / np.linalg.norm(self.embeddings, axis=1, keepdims=True)
            
            # Compute similarities (dot product of normalized vectors = cosine similarity)
            similarities = np.dot(doc_norms, query_norm)
            
            # Get top-k results
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            top_scores = similarities[top_indices]
            
            print(f"[RAG] Query: '{query[:50]}...'")
            print(f"[RAG] Top scores: {top_scores}")
            print(f"[RAG] Threshold: {self.confidence_threshold}")
            
            # Check if best match exceeds threshold
            if len(top_scores) == 0 or top_scores[0] < self.confidence_threshold:
                return {
                    'used': False,
                    'reason': f'Low confidence (max: {float(top_scores[0]) if len(top_scores) > 0 else 0.0:.3f}, threshold: {self.confidence_threshold})',
                    'passages': [],
                    'sources': [],
                    'confidence': float(top_scores[0]) if len(top_scores) > 0 else 0.0
                }
            
            # Collect results
            passages = []
            sources = set()
            
            for idx, score in zip(top_indices, top_scores):
                doc = self.documents[idx]
                passages.append({
                    'text': doc['text'],
                    'source': doc['source'],
                    'confidence': float(score)
                })
                sources.add(doc['source'])
                print(f"[RAG] Match: {doc['source']} (score: {score:.3f})")
            
            context = '\n\n'.join([p['text'] for p in passages])
            
            return {
                'used': True,
                'passages': passages,
                'sources': list(sources),
                'confidence': float(top_scores[0]),
                'context': context
            }
            
        except Exception as e:
            logging.error(f"Retrieval failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                'used': False,
                'reason': f'Error during retrieval: {str(e)}',
                'passages': [],
                'sources': [],
                'confidence': 0.0
            }
    
    def is_available(self) -> bool:
        """Check if RAG service is available and has documents."""
        available = self.enabled and len(self.documents) > 0 and self.embeddings is not None
        print(f"[RAG] is_available: {available} (enabled: {self.enabled}, docs: {len(self.documents)}, embeddings: {self.embeddings is not None})")
        return available