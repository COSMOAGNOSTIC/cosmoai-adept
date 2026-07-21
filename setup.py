from setuptools import setup, find_packages

setup(
    name="agent_core",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langchain-anthropic",
        "langgraph",
        "langgraph-checkpoint-sqlite",
        "python-dotenv",
        "pydantic",
        "requests",
        "tavily-python",
        "elevenlabs",
        "discord.py",
    ],
    extras_require={
        "dev": ["pytest"],
    },
)
