import pytest
from unittest.mock import Mock
import os
from datetime import datetime, UTC
from games_elt.utils.cache_manager import CacheManager
from games_elt.utils.webhook_manager import WebhookManager, WebhookConfig
from games_elt.riot_data_collector import RiotDataCollector

@pytest.fixture
def mock_api_response():
    """Mock API response data"""
    return {
        "info": {
            "gameId": 123456789,
            "platformId": "TR1",
            "gameMode": "CLASSIC",
            "gameType": "MATCHED_GAME",
            "gameVersion": "13.10.1",
            "gameStartTimestamp": 1625097600000,
            "gameDuration": 1800,
            "participants": [
                {
                    "summonerName": "TestPlayer1",
                    "summonerId": "sum1",
                    "championName": "Ahri",
                    "teamId": 100,
                    "win": True,
                    "kills": 5,
                    "deaths": 2,
                    "assists": 10,
                    "champLevel": 18,
                    "totalDamageDealt": 15000,
                    "goldEarned": 12000,
                    "totalMinionsKilled": 180,
                    "neutralMinionsKilled": 20,
                    "visionScore": 25,
                    "teamPosition": "MIDDLE"
                },
                {
                    "summonerName": "TestPlayer2",
                    "summonerId": "sum2",
                    "championName": "Jinx",
                    "teamId": 200,
                    "win": False,
                    "kills": 3,
                    "deaths": 4,
                    "assists": 6,
                    "champLevel": 16,
                    "totalDamageDealt": 12000,
                    "goldEarned": 10000,
                    "totalMinionsKilled": 160,
                    "neutralMinionsKilled": 10,
                    "visionScore": 20,
                    "teamPosition": "BOTTOM"
                }
            ]
        }
    }

@pytest.fixture
def mock_account_response():
    """Mock account API response"""
    return {
        "puuid": "test-puuid-123",
        "gameName": "TestPlayer",
        "tagLine": "TR1"
    }

@pytest.fixture
def mock_summoner_response():
    """Mock summoner API response"""
    return {
        "id": "test-sum-123",
        "accountId": "test-acc-123",
        "puuid": "test-puuid-123",
        "name": "TestPlayer",
        "profileIconId": 1,
        "revisionDate": 1625097600000,
        "summonerLevel": 100
    }

@pytest.fixture
def mock_match_history_response():
    """Mock match history API response"""
    return ["match1", "match2", "match3"]

@pytest.fixture
def test_cache_dir(tmp_path):
    """Create a temporary cache directory"""
    cache_dir = tmp_path / "test_cache"
    cache_dir.mkdir()
    return str(cache_dir)

@pytest.fixture
def cache_manager(test_cache_dir):
    """Create a CacheManager instance with test directory"""
    return CacheManager(cache_dir=test_cache_dir, ttl=3600)

@pytest.fixture
def webhook_manager():
    """Create a WebhookManager instance"""
    return WebhookManager()

@pytest.fixture
def mock_requests(monkeypatch):
    """Mock requests library"""
    mock = Mock()
    mock.get.return_value.status_code = 200
    mock.get.return_value.json.return_value = {}
    mock.post.return_value.status_code = 200
    monkeypatch.setattr("requests.get", mock.get)
    monkeypatch.setattr("requests.post", mock.post)
    return mock

@pytest.fixture
def riot_collector(mock_requests):
    """Create a RiotDataCollector instance with mocked requests"""
    api_key = "test-api-key-123"
    return RiotDataCollector(api_key=api_key, region="tr1") 