"""Pytest configuration and shared fixtures for knowledge-base-search tests."""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def test_data_dir():
    """Return the test data directory."""
    return PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture(scope="session")
def qdrant_url():
    """Return Qdrant URL from environment."""
    return os.getenv("QDRANT_URL", "http://localhost:6333")


@pytest.fixture(scope="session")
def collection_name():
    """Return collection name from environment."""
    return os.getenv("COLLECTION_NAME", "knowledge-base")


@pytest.fixture(scope="session")
def anthropic_api_key():
    """Return Anthropic API key from environment."""
    return os.getenv("ANTHROPIC_AUTH_TOKEN")


@pytest.fixture(scope="session")
def worker_model():
    """Return worker model from environment."""
    return os.getenv("WORKER_MODEL", "claude-sonnet-4-5-20250929")


@pytest.fixture
def sample_query_en():
    """Sample English query for testing."""
    return "What is a Pod in Kubernetes?"


@pytest.fixture
def sample_query_zh():
    """Sample Chinese query for testing."""
    return "Redis 管道技术如何工作？"


@pytest.fixture
def test_cases():
    """Standard test cases for E2E testing."""
    return [
        {
            "id": "test-001",
            "query": "What is a Pod in Kubernetes?",
            "language": "en",
            "category": "k8s-basic",
        },
        {
            "id": "test-002",
            "query": "Redis 管道技术如何工作？",
            "language": "zh",
            "category": "redis-pipeline",
        },
        {
            "id": "test-003",
            "query": "Kubernetes Service 是什么？",
            "language": "zh",
            "category": "k8s-service",
        },
        {
            "id": "test-004",
            "query": "What are Init Containers?",
            "language": "en",
            "category": "k8s-init",
        },
    ]
