import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.models.db_models import Agent as AgentModel, AgentType
from app.crud.crud_agent import agent as crud_agent
from app.crud.crud_document import document_chunk as crud_document_chunk

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Initialize embedding model (used for ChromaDB)
embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY, model="text-embedding-ada-002")

# Initialize ChromaDB client (persistent)
# This should ideally be a singleton or managed by a dependency injection system
chroma_client = Chroma(persist_directory=settings.CHROMA_DB_PATH, embedding_function=embeddings)


@tool
async def knowledge_base_query(query: str) -> str:
    """
    Queries the knowledge base for relevant information based on the user's query.
    Use this tool to retrieve factual information from the knowledge base.
    """
    logger.info(f"Knowledge base query received: {query}")
    # In a real scenario, this would involve a more sophisticated RAG chain
    # For now, we'll do a simple similarity search on completed chunks

    # Filter for COMPLETED chunks in ChromaDB (metadata filtering)
    # This assumes that 'embedding_status' is stored as metadata in ChromaDB
    # and that the status is 'COMPLETED' for ready chunks.
    # Note: ChromaDB's metadata filtering syntax might vary slightly based on version.
    # We'll assume a direct key-value filter for simplicity here.
    # The actual filtering should be done at the retriever level, not directly here.
    # This tool is a placeholder for a full RAG chain.

    # For now, we'll just do a similarity search without explicit status filtering here.
    # The filtering will be applied when creating the retriever for sub-agents.
    docs = chroma_client.similarity_search(query, k=3)
    if docs:
        return "\n---\n".join([doc.page_content for doc in docs])
    return "No relevant information found in the knowledge base."


async def create_sub_agent_tool(agent_config: AgentModel) -> tool:
    """
    Creates a LangChain Tool object from a sub-agent configuration.
    Each sub-agent will have its own RAG chain for its specific knowledge domain.
    """
    # Initialize LLM for the sub-agent
    llm = ChatOpenAI(
        model=agent_config.model,
        temperature=agent_config.temperature,
        api_key=settings.OPENAI_API_KEY,
    )

    # Create a retriever for the sub-agent's knowledge base
    # This retriever should filter for chunks with embedding_status='COMPLETED'
    # This is a conceptual filter. Actual implementation depends on ChromaDB's filtering capabilities.
    # For ChromaDB, you can pass a 'where' clause to as_retriever().
    retriever = chroma_client.as_retriever(search_kwargs={
        "filter": {"embedding_status": DocumentProcessingStatus.COMPLETED.value}
    })

    # Create a prompt template for the sub-agent
    sub_agent_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", agent_config.system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    # Create the sub-agent's RAG chain
    # This is a simplified RAG chain. A full RAG chain would involve more steps.
    # For now, we'll just use the retriever and LLM.
    # The actual RAG chain should integrate the retrieved documents into the prompt.
    # This part needs to be refined to properly use the retriever.
    # For demonstration, we'll just make a simple tool that uses the LLM.

    # Define the function that the tool will execute
    async def _run_sub_agent_rag(query: str) -> str:
        # Retrieve relevant documents
        retrieved_docs = retriever.get_relevant_documents(query)
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])

        # Construct the prompt with context
        formatted_prompt = sub_agent_prompt.format_messages(
            input=query,
            chat_history=[], # Chat history will be managed by the main agent
            agent_scratchpad=[],
            system_prompt=agent_config.system_prompt + "\n\nRelevant Context:\n" + context
        )
        response = await llm.ainvoke(formatted_prompt)
        return response.content

    # Create a LangChain tool from the async function
    # The tool name should be unique and descriptive
    sub_tool = tool(_run_sub_agent_rag, name=agent_config.name.replace(" ", "_").lower())
    sub_tool.description = f"Tool for {agent_config.name}. Use this tool when the user's query is related to {agent_config.system_prompt.split('.')[0]}.
    Input should be the user's query."

    return sub_tool


async def run_main_agent(
    user_message: str, session_id: UUID, db: AsyncSession
) -> Dict[str, Any]:
    """
    Runs the main agent pipeline.
    """
    logger.info(f"Running main agent for session {session_id} with message: {user_message}")

    # Fetch main agent configuration
    main_agent_config = await crud_agent.get_by_type(db, agent_type=AgentType.MAIN)
    if not main_agent_config:
        raise HTTPException(status_code=404, detail="Main agent not found.")

    # Fetch all sub-agent configurations and create tools dynamically
    sub_agent_configs = await crud_agent.get_multi_by_type(db, agent_type=AgentType.SUB)
    dynamic_tools = [await create_sub_agent_tool(config) for config in sub_agent_configs]

    # Add the general knowledge base query tool
    all_tools = dynamic_tools + [knowledge_base_query]

    # Initialize LLM for the main agent
    main_llm = ChatOpenAI(
        model=main_agent_config.model,
        temperature=main_agent_config.temperature,
        api_key=settings.OPENAI_API_KEY,
    )

    # Create main agent prompt
    main_agent_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", main_agent_config.system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    # Create the main agent
    main_agent = create_openai_tools_agent(main_llm, all_tools, main_agent_prompt)

    # Create the AgentExecutor
    agent_executor = AgentExecutor(
        agent=main_agent,
        tools=all_tools,
        verbose=True,  # Set to True for detailed logs
        handle_parsing_errors=True, # Handle parsing errors gracefully
    )

    # TODO: Load chat history from DB and pass to agent_executor
    chat_history = [] # Placeholder for actual chat history

    try:
        result = await agent_executor.ainvoke({"input": user_message, "chat_history": chat_history})
        assistant_message = result["output"]

        # TODO: Save chat messages to DB
        # TODO: Extract metadata (used_agents, retrieved_sources) from result

        return {
            "session_id": str(session_id),
            "assistant_message": assistant_message,
            "metadata": {
                "used_agents": [],  # Populate from result
                "retrieved_sources": [],  # Populate from result
            },
        }
    except Exception as e:
        logger.error(f"Error running main agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat: {e}")
