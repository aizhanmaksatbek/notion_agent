from langchain.agents import create_agent
from prompts import SYSTEM_PROMPT, content
from langchain.tools import tool


@tool
def search_articles(articles: str) -> str:
    """Searches articles for a given topic."""
    return f"Articles list in {articles}!"


@tool
def connect_db():
    """This function loads the document for topic search"""
    return content


agent = create_agent(
    model="openai:gpt-5.5",
    tools=[search_articles, connect_db],
    system_prompt=SYSTEM_PROMPT,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Find articles related to personal expenses?"}]}
)

print(result["messages"][-1].content_blocks)
