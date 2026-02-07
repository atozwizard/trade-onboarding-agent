"""
Embeddings Module - Generate and manage embeddings using Upstage Solar
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from langchain_upstage import UpstageEmbeddings
from dotenv import load_dotenv

load_dotenv()


class EmbeddingManager:
    """Manage embeddings for RAG system using Solar Embedding"""
    
    def __init__(self, dataset_dir: str = "../dataset"):
        self.dataset_dir = Path(dataset_dir)
        self.embeddings_model = UpstageEmbeddings(
            model="solar-embedding-1-large",
            api_key=os.getenv("UPSTAGE_API_KEY")
        )
        self.embeddings_cache = {}
    
    def load_json_data(self, filename: str) -> List[Dict[str, Any]]:
        """Load JSON data file"""
        filepath = self.dataset_dir / filename
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        try:
            embeddings = self.embeddings_model.embed_documents(texts)
            return np.array(embeddings)
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return np.array([])
    
    def generate_query_embedding(self, query: str) -> np.ndarray:
        """Generate embedding for a single query"""
        try:
            embedding = self.embeddings_model.embed_query(query)
            return np.array(embedding)
        except Exception as e:
            print(f"Error generating query embedding: {e}")
            return np.array([])
    
    def embed_dataset(self, category: str) -> Dict[str, Any]:
        """
        Generate embeddings for a specific dataset category
        
        Args:
            category: Category name (e.g., 'company_domain', 'emails')
        
        Returns:
            Dictionary with texts, embeddings, and metadata
        """
        # Load data
        filename = f"{category}.json"
        data = self.load_json_data(filename)
        
        if not data:
            print(f"No data found for category: {category}")
            return {"texts": [], "embeddings": [], "metadata": []}
        
        # Extract texts and metadata
        texts = [item["content"] for item in data]
        metadata = [
            {
                "id": item["id"],
                "category": item["category"],
                **item.get("metadata", {})
            }
            for item in data
        ]
        
        # Generate embeddings
        print(f"Generating embeddings for {category}: {len(texts)} items...")
        embeddings = self.generate_embeddings(texts)
        
        result = {
            "texts": texts,
            "embeddings": embeddings,
            "metadata": metadata
        }
        
        # Cache result
        self.embeddings_cache[category] = result
        
        print(f"✓ Generated {len(embeddings)} embeddings for {category}")
        return result
    
    def embed_all_datasets(self) -> Dict[str, Dict[str, Any]]:
        """Generate embeddings for all dataset categories"""
        categories = [
            "company_domain",
            "internal_process",
            "mistakes",
            "ceo_style",
            "emails",
            "country_rules",
            "negotiation",
            "claims",
            "document_errors",
            "trade_qa",
            "kpi",
            "quiz_samples"
        ]
        
        all_embeddings = {}
        
        print("=" * 60)
        print("Generating embeddings for all datasets...")
        print("=" * 60)
        
        for category in categories:
            try:
                result = self.embed_dataset(category)
                all_embeddings[category] = result
            except Exception as e:
                print(f"Error processing {category}: {e}")
        
        print("\n" + "=" * 60)
        print("✓ All embeddings generated successfully!")
        print("=" * 60)
        
        return all_embeddings
    
    def save_embeddings(self, output_dir: str = "../dataset/embeddings"):
        """Save embeddings to disk"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for category, data in self.embeddings_cache.items():
            # Save embeddings as numpy array
            embeddings_file = output_path / f"{category}_embeddings.npy"
            np.save(embeddings_file, data["embeddings"])
            
            # Save metadata as JSON
            metadata_file = output_path / f"{category}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "texts": data["texts"],
                    "metadata": data["metadata"]
                }, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Saved {category} embeddings and metadata")


def main():
    """Main execution for testing"""
    print("Testing Embedding Manager...")
    
    manager = EmbeddingManager()
    
    # Test with one category
    result = manager.embed_dataset("company_domain")
    print(f"\nSample result:")
    print(f"  Texts: {len(result['texts'])}")
    print(f"  Embeddings shape: {result['embeddings'].shape}")
    print(f"  Metadata: {len(result['metadata'])}")
    
    # Uncomment to generate all embeddings
    # all_embeddings = manager.embed_all_datasets()
    # manager.save_embeddings()


if __name__ == "__main__":
    main()
