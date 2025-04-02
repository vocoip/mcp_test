import pytest
from src.models.base import VolcEngineModel
from unittest.mock import AsyncMock, patch

@pytest.fixture
def volc_engine_config():
    return {
        "api_key": "test_api_key",
        "base_url": "http://test.url",
        "model_name": "test_model"
    }

@pytest.mark.asyncio
async def test_generate(volc_engine_config):
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test response"}}]
        }
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        model = VolcEngineModel(volc_engine_config)
        response = await model.generate("test prompt")
        assert response == "test response"

@pytest.mark.asyncio
async def test_conversation(volc_engine_config):
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test conversation"}}]
        }
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        model = VolcEngineModel(volc_engine_config)
        messages = [{"role": "user", "content": "test message"}]
        response = await model.conversation(messages)
        assert response == "test conversation"