from langchain.agents import create_agent
from prompts import SYSTEM_PROMPT


def search_articles(topic: str) -> str:
    """Searches articles for a given topic."""
    return f"Articles list in {topic}!"


agent = create_agent(
    model="openai:gpt-5.5",
    tools=[search_articles],
    system_prompt=SYSTEM_PROMPT,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What are the articles in personal expenses?"}]}
)
print(result["messages"][-1].content_blocks)
