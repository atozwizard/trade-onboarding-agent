import json
import os
import glob
import argparse
import sys

# Ensure backend directory is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.rag.embedder import get_embedding
from backend.rag.chroma_client import get_or_create_collection, reset_collection
from backend.rag.schema import normalize_metadata

DATASET_DIR = "dataset" # Relative to project root
VECTOR_DB_DIR = "backend/vectorstore" # Relative to project root


def ingest_data(reset: bool = False):
    """
    Ingests data from JSON files in the dataset directory into the Chroma vector store.

    Args:
        reset (bool): If True, resets the Chroma collection before ingestion.
    """
    print("--- Starting Data Ingestion ---")

    # Get Chroma collection
    if reset:
        collection = reset_collection()
    else:
        collection = get_or_create_collection()

    documents_to_add = []
    embeddings_to_add = []
    metadatas_to_add = []
    ids_to_add = []
    total_inserted_count = 0

    json_files = glob.glob(os.path.join(DATASET_DIR, "*.json"))
    if not json_files:
        print(f"No JSON files found in {DATASET_DIR}. Exiting ingestion.")
        return

    for file_path in json_files:
        file_name = os.path.basename(file_path)
        print(f"\nProcessing file: {file_name}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print(f"Warning: {file_name} does not contain a list of entries. Skipping.")
            continue

        for i, entry in enumerate(data):
            content = entry.get("content")
            entry_id = f"{os.path.splitext(file_name)[0]}_{entry.get('id', i)}" # Unique ID
            
            if not content or not content.strip():
                print(f"  Skipping entry {entry_id} in {file_name}: Empty content.")
                continue
            
            # Normalize metadata
            normalized_metadata = normalize_metadata(entry, file_path) # Pass full entry and file_path
            
            # Generate embedding
            embedding = get_embedding(content)
            if embedding is None:
                print(f"  Skipping entry {entry_id} in {file_name}: Failed to generate embedding.")
                continue

            # Add to lists for batch insertion
            documents_to_add.append(content)
            embeddings_to_add.append(embedding) # Store the generated embedding
            metadatas_to_add.append(normalized_metadata)
            ids_to_add.append(entry_id)
            total_inserted_count += 1

            if total_inserted_count % 10 == 0:
                print(f"  Processed {total_inserted_count} entries...")
    
    if documents_to_add:
        print(f"\nAdding {len(documents_to_add)} documents to Chroma collection...")
        collection.add(
            embeddings=embeddings_to_add, # Use the stored embeddings
            documents=documents_to_add,
            metadatas=metadatas_to_add,
            ids=ids_to_add
        )
        print(f"  Successfully added {len(documents_to_add)} documents.")
    else:
        print("No documents to add after processing files.")

    print(f"\n--- Data Ingestion Complete ---")
    print(f"Total entries processed: {total_inserted_count}")
    print(f"Current collection count: {collection.count()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest data into Chroma vector store.")
    parser.add_argument("--reset", action="store_true", help="Reset Chroma collection before ingestion.")
    args = parser.parse_args()

    ingest_data(reset=args.reset)
#테스트완료