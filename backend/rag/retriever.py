"""
Vector Retriever - FAISS-based similarity search for RAG
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from rag.embeddings import EmbeddingManager


class FAISSRetriever:
    """FAISS-based vector retriever for RAG system"""
    
    def __init__(self, embeddings_dir: str = "../dataset/embeddings"):
        self.embeddings_dir = Path(embeddings_dir)
        self.embedding_manager = EmbeddingManager()
        self.indexes = {}
        self.metadata = {}
        self.texts = {}
        
        # Initialize if embeddings exist
        if self.embeddings_dir.exists():
            self._load_indexes()
    
    def _load_indexes(self):
        """Load FAISS indexes and metadata from disk"""
        print("Loading FAISS indexes...")
        
        for embeddings_file in self.embeddings_dir.glob("*_embeddings.npy"):
            category = embeddings_file.stem.replace("_embeddings", "")
            
            # Load embeddings
            embeddings = np.load(embeddings_file)
            
            # Load metadata
            metadata_file = self.embeddings_dir / f"{category}_metadata.json"
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.metadata[category] = data["metadata"]
                self.texts[category] = data["texts"]
            
            # Create FAISS index
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings.astype('float32'))
            self.indexes[category] = index
            
            print(f"✓ Loaded {category}: {len(embeddings)} vectors")
    
    def build_indexes(self):
        """Build FAISS indexes from embeddings"""
        print("Building FAISS indexes...")
        
        # Generate embeddings if not exists
        all_embeddings = self.embedding_manager.embed_all_datasets()
        
        # Create embeddings directory
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        
        # Build indexes
        for category, data in all_embeddings.items():
            embeddings = data["embeddings"]
            
            if len(embeddings) == 0:
                print(f"⚠ Skipping {category}: no embeddings")
                continue
            
            # Create FAISS index
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings.astype('float32'))
            
            # Store
            self.indexes[category] = index
            self.metadata[category] = data["metadata"]
            self.texts[category] = data["texts"]
            
            # Save to disk
            np.save(
                self.embeddings_dir / f"{category}_embeddings.npy",
                embeddings
            )
            with open(self.embeddings_dir / f"{category}_metadata.json", 'w', encoding='utf-8') as f:
                json.dump({
                    "texts": data["texts"],
                    "metadata": data["metadata"]
                }, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Built index for {category}: {len(embeddings)} vectors")
    
    def retrieve(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: Search query
            category: Specific category to search (None = search all)
            top_k: Number of results to return
        
        Returns:
            List of relevant documents with metadata
        """
        # Generate query embedding
        query_embedding = self.embedding_manager.generate_query_embedding(query)
        
        if len(query_embedding) == 0:
            return []
        
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        
        # Search in specified category or all categories
        categories = [category] if category else list(self.indexes.keys())
        
        all_results = []
        
        for cat in categories:
            if cat not in self.indexes:
                continue
            
            index = self.indexes[cat]
            
            # Search
            distances, indices = index.search(query_embedding, min(top_k, index.ntotal))
            
            # Collect results
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(self.texts[cat]):
                    all_results.append({
                        "text": self.texts[cat][idx],
                        "metadata": self.metadata[cat][idx],
                        "category": cat,
                        "distance": float(dist),
                        "score": 1 / (1 + float(dist))  # Convert distance to similarity score
                    })
        
        # Sort by score and return top_k
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k]
    
    def retrieve_by_category(
        self,
        query: str,
        categories: List[str],
        top_k: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve from multiple categories separately
        
        Args:
            query: Search query
            categories: List of categories to search
            top_k: Number of results per category
        
        Returns:
            Dictionary mapping category to results
        """
        results = {}
        
        for category in categories:
            results[category] = self.retrieve(query, category, top_k)
        
        return results


def main():
    """Main execution for testing"""
    print("=" * 60)
    print("FAISS Retriever - Build and Test")
    print("=" * 60)
    
    retriever = FAISSRetriever()
    
    # Build indexes
    retriever.build_indexes()
    
    # Test retrieval
    print("\n" + "=" * 60)
    print("Testing retrieval...")
    print("=" * 60)
    
    test_query = "BL 선하증권이 뭐야?"
    results = retriever.retrieve(test_query, top_k=3)
    
    print(f"\nQuery: {test_query}")
    print(f"Results: {len(results)}\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result['category']}] (score: {result['score']:.3f})")
        print(f"   {result['text'][:100]}...")
        print()


if __name__ == "__main__":
    main()
