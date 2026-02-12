# backend/agents/riskmanaging/similarity_engine.py

from typing import List, Dict, Any, Optional
from numpy.linalg import norm
import numpy as np
import os

from backend.config import get_settings
from backend.rag.embedder import get_embedding

class SimilarityEngine:
    def __init__(self):
        self.settings = get_settings()
        # Pre-define some risk types or load them from a source
        # For a full implementation, these "risk types" might come from a DB or config
        self.predefined_risk_types = [
            "재정적 손실 리스크",
            "계약 위반 및 준수 리스크",
            "프로젝트 지연 리스크",
            "공급망 차질 리스크",
            "고객 관계 손상 리스크",
            "법적 분쟁 리스크",
            "내부 규정 위반 리스크",
            "정보 보안 리스크",
            "시장 변동성 리스크",
            "기술적 문제 리스크",
        ]
        self.risk_type_embeddings = self._embed_risk_types()

    def _embed_risk_types(self) -> List[np.ndarray]:
        """
        Generates embeddings for predefined risk types.
        """
        if not self.settings.upstage_api_key:
            print("Warning: UPSTAGE_API_KEY is not set. SimilarityEngine will operate without embeddings.")
            return []
        
        embeddings = []
        for risk_type in self.predefined_risk_types:
            try:
                embedding = get_embedding(risk_type)
                if embedding:
                    embeddings.append(np.array(embedding))
            except Exception as e:
                print(f"Error embedding risk type '{risk_type}': {e}")
        return embeddings

    def calculate_cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculates the cosine similarity between two embeddings.
        """
        if norm(embedding1) == 0 or norm(embedding2) == 0:
            return 0.0 # Avoid division by zero
        return np.dot(embedding1, embedding2) / (norm(embedding1) * norm(embedding2))

    def check_similarity(self, user_input: str, threshold: float = 0.87) -> bool:
        """
        Checks if the user input is similar to any predefined risk type above a given threshold.
        """
        if not self.risk_type_embeddings:
            print("Warning: No risk type embeddings available. Similarity check skipped.")
            return False

        user_embedding_list = get_embedding(user_input)
        if not user_embedding_list:
            print("Warning: Could not get embedding for user input. Similarity check skipped.")
            return False
        user_embedding = np.array(user_embedding_list)

        for risk_type_embedding in self.risk_type_embeddings:
            similarity = self.calculate_cosine_similarity(user_embedding, risk_type_embedding)
            if similarity >= threshold:
                return True
        return False

    def get_most_similar_risk_type(self, user_input: str) -> Optional[str]:
        """
        Returns the predefined risk type most similar to the user input, if above threshold.
        """
        if not self.risk_type_embeddings:
            return None

        user_embedding_list = get_embedding(user_input)
        if not user_embedding_list:
            return None
        user_embedding = np.array(user_embedding_list)

        max_similarity = -1
        most_similar_type = None

        for i, risk_type_embedding in enumerate(self.risk_type_embeddings):
            similarity = self.calculate_cosine_similarity(user_embedding, risk_type_embedding)
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_type = self.predefined_risk_types[i]
        
        # Optionally, apply a threshold here too if only "sufficiently" similar types are desired
        from backend.agents.riskmanaging.config import SIMILARITY_THRESHOLD
        if max_similarity >= SIMILARITY_THRESHOLD:
            return most_similar_type
        return None

# Example usage
if __name__ == '__main__':
    # Ensure UPSTAGE_API_KEY is set in your .env file
    settings = get_settings()
    if not settings.upstage_api_key:
        print("UPSTAGE_API_KEY is not set. SimilarityEngine will not run with embeddings.")
        exit()

    engine = SimilarityEngine()
    
    print("\n--- Similarity Engine Test ---") # Corrected string literal

    test_queries = [
        "환율 변동으로 인한 손실이 예상됩니다.", # Should be similar to "재정적 손실 리스크"
        "납품 기한을 맞추기 어려울 것 같습니다.", # Should be similar to "프로젝트 지연 리스크"
        "고객사의 불만이 커지고 있습니다.", # Should be similar to "고객 관계 손상 리스크"
        "배송 중 문제가 발생했습니다.", # Some risk
        "오늘 날씨가 좋네요.", # Should not be similar
    ]

    from backend.agents.riskmanaging.config import SIMILARITY_THRESHOLD

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        is_similar = engine.check_similarity(query, threshold=SIMILARITY_THRESHOLD)
        most_similar = engine.get_most_similar_risk_type(query)
        print(f"  Is similar (threshold {SIMILARITY_THRESHOLD})? {is_similar}")
        print(f"  Most similar risk type: {most_similar}")