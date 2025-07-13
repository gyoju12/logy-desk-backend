from setuptools import setup, find_packages
import os
from pathlib import Path

# Read requirements from pyproject.toml
base_dir = Path(__file__).parent

# Read version from _version.py if it exists, otherwise use a default
version = {}
version_path = base_dir / "app" / "_version.py"
if version_path.exists():
    with open(version_path) as f:
        exec(f.read(), version)
else:
    version['__version__'] = '0.1.0'

# Read long description from README.md
readme_path = base_dir / "README.md"
long_description = ""
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="logy-desk-backend",
    version=version['__version__'],
    packages=find_packages(include=['app*']),
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
    # These are now defined in pyproject.toml
    extras_require={},
    # Project metadata
    author="Logy Desk Team",
    author_email="dev@logydesk.com",
    description="FastAPI 기반의 멀티 에이전트 채팅 백엔드 애플리케이션",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.9,<3.13",
    # Include package data
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.json", "*.txt"]
    }
)
