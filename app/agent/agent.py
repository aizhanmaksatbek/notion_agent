from langchain.agents import create_agent
from app.agent.prompts import SYSTEM_PROMPT
from app.schemas.schemas import AgentOutput, PromptInstruction
from app.notion_mcp.db import content
from langchain.tools import tool
from langchain_core.messages.tool import ToolMessage


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


def call_agent(prompt: str):
    execution_result = list()
    agent_output = agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]}
    )

    for output in agent_output["messages"]:
        if isinstance(output, ToolMessage):
            instruction = {
                "instruction": output.name,
                "status": output.status
                }
            PromptInstruction.model_validate(instruction)
            execution_result.append(instruction)

    return AgentOutput(prompt=prompt, instructions=execution_result)
