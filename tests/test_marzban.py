import pytest
from unittest.mock import AsyncMock, patch
from app.services.marzban_api import MarzbanAPI

@pytest.mark.asyncio
async def test_marzban_auth_failure():
    with patch('aiohttp.ClientSession.post') as mocked_post:
        mocked_post.return_value.__aenter__.return_value.status = 401
        api = MarzbanAPI()
        token = await api._get_token()
        assert token is None

@pytest.mark.asyncio
async def test_marzban_create_user_success():
    api = MarzbanAPI()
    api.token = "fake_token"
    api.host = "http://fakehost"
    
    with patch('aiohttp.ClientSession.post') as mocked_post:
        mocked_post.return_value.__aenter__.return_value.status = 200
        mocked_post.return_value.__aenter__.return_value.json = AsyncMock(return_value={"username": "testuser"})
        
        res = await api.create_user("testuser", 10, 123456789)
        assert res["username"] == "testuser"
