# backend/agents/email_agent/tools.py

# This file can be used to define LangChain tools for specific functionalities
# if the email agent were to expose them as callable tools within a larger system.
# For now, the RAG search functionality is directly integrated into the nodes.py.

# Example:
# from langchain.tools import tool
# from .nodes import EMAIL_AGENT_COMPONENTS
#
# class EmailAgentTools:
#     @tool
#     def search_rag_for_email_context(query: str) -> List[Dict[str, Any]]:
#         """Searches RAG for context relevant to drafting or analyzing an email."""
#         return EMAIL_AGENT_COMPONENTS.rag_search(query=query)

# Currently, no explicit tools are needed for the graph structure.
