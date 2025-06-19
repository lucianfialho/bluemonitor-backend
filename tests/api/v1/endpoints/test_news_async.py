import pytest
from httpx import AsyncClient
from app.main import app  # ou use a fixture app se preferir

@pytest.mark.asyncio
async def test_get_news_success(test_news):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        news_id = str(test_news["_id"])
        response = await ac.get(f"/api/v1/news/{news_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["_id"] == news_id
