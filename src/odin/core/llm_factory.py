"""LLM factory for creating language models based on configuration."""

from typing import Any

from odin.config import Settings, get_settings
from odin.logging import get_logger

logger = get_logger(__name__)


def create_llm(settings: Settings | None = None) -> Any:
    """Create LLM instance based on configuration.

    Args:
        settings: Settings instance (defaults to global settings)

    Returns:
        LangChain ChatModel instance

    Raises:
        ImportError: If required provider package is not installed
        ValueError: If configuration is incomplete
    """
    if settings is None:
        settings = get_settings()

    provider = settings.llm_provider
    logger.info("Creating LLM", provider=provider)

    if provider == "openai":
        return _create_openai_llm(settings)
    elif provider == "anthropic":
        return _create_anthropic_llm(settings)
    elif provider == "azure":
        return _create_azure_openai_llm(settings)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _create_openai_llm(settings: Settings) -> Any:
    """Create OpenAI LLM instance."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError(
            "langchain-openai is required for OpenAI provider. "
            "Install with: pip install langchain-openai"
        )

    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is required for OpenAI provider. "
            "Set it in .env file or environment variables."
        )

    llm_kwargs = {
        "model": settings.openai_model,
        "api_key": settings.openai_api_key,
    }

    if settings.openai_base_url:
        llm_kwargs["base_url"] = settings.openai_base_url

    logger.info(
        "Creating OpenAI LLM",
        model=settings.openai_model,
        base_url=settings.openai_base_url or "default",
    )

    return ChatOpenAI(**llm_kwargs)


def _create_anthropic_llm(settings: Settings) -> Any:
    """Create Anthropic LLM instance."""
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "langchain-anthropic is required for Anthropic provider. "
            "Install with: pip install langchain-anthropic"
        )

    if not settings.anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is required for Anthropic provider. "
            "Set it in .env file or environment variables."
        )

    logger.info(
        "Creating Anthropic LLM",
        model=settings.anthropic_model,
    )

    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
    )


def _create_azure_openai_llm(settings: Settings) -> Any:
    """Create Azure OpenAI LLM instance."""
    try:
        from langchain_openai import AzureChatOpenAI
    except ImportError:
        raise ImportError(
            "langchain-openai is required for Azure OpenAI provider. "
            "Install with: pip install langchain-openai"
        )

    if not settings.azure_openai_api_key:
        raise ValueError(
            "AZURE_OPENAI_API_KEY is required for Azure provider. "
            "Set it in .env file or environment variables."
        )

    if not settings.azure_openai_endpoint:
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT is required for Azure provider. "
            "Set it in .env file or environment variables."
        )

    if not settings.azure_openai_deployment:
        raise ValueError(
            "AZURE_OPENAI_DEPLOYMENT is required for Azure provider. "
            "Set it in .env file or environment variables."
        )

    logger.info(
        "Creating Azure OpenAI LLM",
        deployment=settings.azure_openai_deployment,
        endpoint=settings.azure_openai_endpoint,
    )

    return AzureChatOpenAI(
        azure_deployment=settings.azure_openai_deployment,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
    )


def create_checkpointer(settings: Settings | None = None) -> Any:
    """Create LangGraph checkpointer based on configuration.

    Args:
        settings: Settings instance (defaults to global settings)

    Returns:
        LangGraph checkpointer instance

    Raises:
        ImportError: If required package is not installed
        ValueError: If configuration is incomplete
    """
    if settings is None:
        settings = get_settings()

    checkpointer_type = settings.checkpointer_type
    logger.info("Creating checkpointer", type=checkpointer_type)

    if checkpointer_type == "memory":
        return _create_memory_checkpointer()
    elif checkpointer_type == "sqlite":
        return _create_sqlite_checkpointer(settings)
    elif checkpointer_type == "postgres":
        return _create_postgres_checkpointer(settings)
    elif checkpointer_type == "redis":
        return _create_redis_checkpointer(settings)
    else:
        raise ValueError(f"Unsupported checkpointer type: {checkpointer_type}")


def _create_memory_checkpointer() -> Any:
    """Create in-memory checkpointer (no persistence)."""
    try:
        from langgraph.checkpoint.memory import MemorySaver
    except ImportError:
        raise ImportError(
            "langgraph is required. Install with: pip install langgraph"
        )

    logger.info("Using in-memory checkpointer (no persistence)")
    return MemorySaver()


def _create_sqlite_checkpointer(settings: Settings) -> Any:
    """Create SQLite checkpointer."""
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError:
        raise ImportError(
            "langgraph-checkpoint-sqlite is required. "
            "Install with: pip install langgraph-checkpoint-sqlite"
        )

    uri = settings.checkpointer_uri or str(settings.sqlite_path)
    logger.info("Creating SQLite checkpointer", uri=uri)

    return SqliteSaver.from_conn_string(uri)


def _create_postgres_checkpointer(settings: Settings) -> Any:
    """Create Postgres checkpointer."""
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
    except ImportError:
        raise ImportError(
            "langgraph-checkpoint-postgres is required. "
            "Install with: pip install langgraph-checkpoint-postgres"
        )

    uri = settings.checkpointer_uri or settings.postgres_url
    if not uri:
        raise ValueError(
            "ODIN_CHECKPOINTER_URI or ODIN_POSTGRES_URL is required for Postgres checkpointer"
        )

    logger.info("Creating Postgres checkpointer", uri=uri.split("@")[-1])  # Hide credentials
    return PostgresSaver.from_conn_string(uri)


def _create_redis_checkpointer(settings: Settings) -> Any:
    """Create Redis checkpointer."""
    try:
        from langgraph.checkpoint.redis import RedisSaver
    except ImportError:
        raise ImportError(
            "langgraph-checkpoint-redis is required. "
            "Install with: pip install langgraph-checkpoint-redis"
        )

    uri = settings.checkpointer_uri or settings.redis_url
    logger.info("Creating Redis checkpointer", uri=uri.split("@")[-1])  # Hide credentials
    return RedisSaver.from_conn_string(uri)
