from langchain.agents import create_agent
from app.agent.prompts import SYSTEM_PROMPT
from app.schemas.schemas import AgentOutput, PromptInstruction
from app.notion_mcp.db import content
from langchain.tools import tool
from langchain_core.messages.tool import ToolMessage
from app.config.settings import DB_URL
from langchain_core.runnables import Runnable
from langgraph.store.postgres import PostgresStore


@tool
def search_articles(articles: str) -> str:
    """Searches articles for a given topic."""
    return f"Articles list in {articles}!"


@tool
def connect_db():
    """This function loads the document for topic search"""
    return content


@tool
def extract_tool_results(agent_output: ToolMessage) -> AgentOutput:
    """This function extracts the Tool messages from agent execution result."""
    execution_result = list()
    for output in agent_output["messages"]:
        if isinstance(output, ToolMessage):
            instruction = {
                "instruction": output.name,
                "status": output.status
                }
            PromptInstruction.model_validate(instruction)
            execution_result.append(instruction)

    return AgentOutput(
        prompt=agent_output["messages"][0],
        instructions=execution_result
        )


with PostgresStore.from_conn_string(DB_URL) as store:
    store.setup()

    agent: Runnable = create_agent(
        model="gpt-5.4-nano",
        tools=[search_articles, connect_db, extract_tool_results],
        system_prompt=SYSTEM_PROMPT,
        store=store
    )


def call_agent(prompt: str):
    execution_result = list()
    with PostgresStore.from_conn_string(DB_URL) as store:
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

        store.put(
            ("prompts",),
            prompt,
            execution_result
            )
    return AgentOutput(prompt=prompt, instructions=execution_result)
