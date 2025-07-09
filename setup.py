from setuptools import setup, find_packages

setup(
    name="logy-desk-backend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "python-dotenv>=1.0.0",
        "sqlalchemy>=2.0.23",
        "psycopg2-binary>=2.9.9",
        "alembic>=1.12.1",
        "python-multipart>=0.0.6",
        "pydantic>=2.5.2",
        "pydantic-settings>=2.1.0",
        "httpx>=0.23.0",
    ],
    extras_require={
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "httpx>=0.23.0",
            "python-multipart>=0.0.5",
        ],
    },
    python_requires=">=3.9",
)
