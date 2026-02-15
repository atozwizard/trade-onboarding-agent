# backend/agents/quiz_agent/tools.py

# This file can be used to define LangChain tools for specific functionalities
# if the quiz agent were to expose them as callable tools within a larger system.
# For now, the RAG search functionality is directly integrated into the nodes.py.

# Example:
# from langchain.tools import tool
# from .nodes import QUIZ_AGENT_COMPONENTS
#
# class QuizAgentTools:
#     @tool
#     def search_rag_for_quiz_topics(query: str) -> List[Dict[str, Any]]:
#         """Searches RAG for topics relevant to generating a quiz."""
#         return QUIZ_AGENT_COMPONENTS.rag_search(query=query)

# Currently, no explicit tools are needed for the graph structure.
