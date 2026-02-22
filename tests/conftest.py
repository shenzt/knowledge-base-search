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


def pytest_configure(config):
    """注册自定义 markers。"""
    config.addinivalue_line("markers", "integration: 需要 Qdrant + BGE-M3 的集成测试")
    config.addinivalue_line("markers", "e2e: 需要 Agent SDK + LLM API 的端到端测试")


def _qdrant_reachable(url: str) -> bool:
    """检查 Qdrant 是否可达。"""
    import urllib.request
    try:
        urllib.request.urlopen(f"{url}/healthz", timeout=3)
        return True
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    """对 integration/e2e 测试自动添加 marker 并在基础设施不可达时 skip。"""
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_ok = _qdrant_reachable(qdrant_url)

    skip_qdrant = pytest.mark.skip(reason=f"Qdrant 不可达: {qdrant_url}")

    for item in items:
        # 按目录自动打 marker
        rel = Path(item.fspath).relative_to(PROJECT_ROOT / "tests")
        parts = rel.parts
        if parts and parts[0] == "integration":
            item.add_marker(pytest.mark.integration)
            if not qdrant_ok:
                item.add_marker(skip_qdrant)
        elif parts and parts[0] == "e2e":
            item.add_marker(pytest.mark.e2e)
            if not qdrant_ok:
                item.add_marker(skip_qdrant)


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
