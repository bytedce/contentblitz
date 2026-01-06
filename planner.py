# planner.py
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import LLM_MODEL, OPENROUTER_API_KEY

def run_query_planner(query: str, log=None) -> dict:
    """
    Semantic query planner.
    Returns:
      {
        allowed: bool,
        top_k: int,
        category: str,
        intent: str
      }
    """

    log("RESEARCH", "Running semantic query planner")

    llm = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.3,
    )

    prompt = ChatPromptTemplate.from_template(
        """
        You are a query planner for a beauty product search system.

        User query:
        "{query}"

        Decide:
        1. Is the query related to beauty, cosmetic, perfume, fragrance, or body-care products?
        2. How many products should be retrieved? (default 6)
        3. What is the main product category?
        4. What is the user intent?

        Rules:
        - If user asks "top N", use N
        - If list/comparison intent, increase results
        - Keep top_k between 1 and 20

        Return ONLY valid JSON:
        {{
        "allowed": true or false,
        "top_k": number,
        "category": "perfume | cosmetic | bodycare | mixed | unknown",
        "intent": "list | comparison | recommendation | informational"
        }}
        """
    )


    response = (prompt | llm).invoke({"query": query}).content.strip()

    try:
        plan = json.loads(response)
    except Exception:
        # Fail safe
        plan = {
            "allowed": False,
            "top_k": 5,
            "category": "unknown",
            "intent": "unknown",
        }

    log(
        "RESEARCH",
        f"Planner output → allowed={plan['allowed']}, "
        f"top_k={plan['top_k']}, "
        f"category={plan['category']}, "
        f"intent={plan['intent']}",
    )

    return plan
