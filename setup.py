from setuptools import setup, find_packages

setup(
    name="logy-desk-backend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Core Dependencies
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "python-dotenv>=1.0.0",
        "python-multipart>=0.0.6",
        
        # Database
        "sqlalchemy[asyncio]>=2.0.23",
        "alembic>=1.13.0",
        "asyncpg>=0.29.0",
        "psycopg2-binary>=2.9.9",
        "greenlet>=3.0.0",
        
        # Pydantic
        "pydantic>=2.5.2",
        "pydantic-settings>=2.1.0",
        
        # RAG and AI
        "langchain>=0.1.0",
        "langchain-core>=0.1.0",
        "langchain-community>=0.0.10",
        "langchain-text-splitters>=0.0.1",
        "langsmith>=0.0.24",
        "chromadb>=0.4.22",
        "sentence-transformers>=2.2.2",
        
        # LLM Providers
        "openai>=1.3.5",
        "httpx>=0.25.1"
    ],
    extras_require={
        "test": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "httpx>=0.25.1"
        ],
        "dev": [
            "black>=23.11.0",
            "isort>=5.12.0",
            "mypy>=1.7.0",
            "flake8>=6.1.0"
        ]
    },
    python_requires=">=3.9",
)
