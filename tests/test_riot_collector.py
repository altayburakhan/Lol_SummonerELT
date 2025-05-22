import pytest
from datetime import datetime, UTC, timedelta
from games_elt.models.game_models import GameData, TeamSide, GameMode

def test_get_account_by_riot_id(riot_collector, mock_requests, mock_account_response):
    """Test getting account info by Riot ID"""
    mock_requests.get.return_value.json.return_value = mock_account_response
    
    account = riot_collector.get_account_by_riot_id("TestPlayer", "TR1")
    
    assert account["puuid"] == "test-puuid-123"
    assert account["gameName"] == "TestPlayer"
    assert account["tagLine"] == "TR1"
    
    # Test caching
    riot_collector.get_account_by_riot_id("TestPlayer", "TR1")
    assert mock_requests.get.call_count == 1  # Should use cached value

def test_get_summoner_by_puuid(riot_collector, mock_requests, mock_summoner_response):
    """Test getting summoner info by PUUID"""
    mock_requests.get.return_value.json.return_value = mock_summoner_response
    
    summoner = riot_collector.get_summoner_by_puuid("test-puuid-123")
    
    assert summoner["id"] == "test-sum-123"
    assert summoner["name"] == "TestPlayer"
    assert summoner["puuid"] == "test-puuid-123"
    
    # Test caching
    riot_collector.get_summoner_by_puuid("test-puuid-123")
    assert mock_requests.get.call_count == 1  # Should use cached value

def test_get_match_history(riot_collector, mock_requests, mock_match_history_response):
    """Test getting match history"""
    mock_requests.get.return_value.json.return_value = mock_match_history_response
    
    matches = riot_collector.get_match_history(
        "test-puuid-123",
        count=3,
        queue_type=420,
        start_time=datetime.now(UTC) - timedelta(days=1)
    )
    
    assert len(matches) == 3
    assert matches == ["match1", "match2", "match3"]
    
    # Verify request parameters
    args, kwargs = mock_requests.get.call_args
    assert kwargs["params"]["count"] == 3
    assert kwargs["params"]["queue"] == 420
    assert "startTime" in kwargs["params"]

def test_get_match_details(riot_collector, mock_requests, mock_api_response):
    """Test getting and transforming match details"""
    mock_requests.get.return_value.json.return_value = mock_api_response
    
    match = riot_collector.get_match_details("match1")
    
    assert isinstance(match, GameData)
    assert match.game_id == "123456789"
    assert match.game_mode == GameMode.CLASSIC
    assert len(match.teams) == 2
    
    # Verify team data
    blue_team = next(team for team in match.teams if team.side == TeamSide.BLUE)
    red_team = next(team for team in match.teams if team.side == TeamSide.RED)
    
    assert len(blue_team.participants) == 1
    assert len(red_team.participants) == 1
    
    # Verify participant data
    blue_player = blue_team.participants[0]
    assert blue_player.summoner_name == "TestPlayer1"
    assert blue_player.champion_name == "Ahri"
    assert blue_player.stats.kills == 5
    assert blue_player.stats.deaths == 2
    assert blue_player.stats.assists == 10
    
    # Test caching
    riot_collector.get_match_details("match1")
    assert mock_requests.get.call_count == 1  # Should use cached value

def test_collect_match_history_integration(
    riot_collector,
    mock_requests,
    mock_account_response,
    mock_summoner_response,
    mock_match_history_response,
    mock_api_response
):
    """Test the complete match history collection flow"""
    # Setup mock responses
    def get_mock_response(*args, **kwargs):
        url = args[0]
        mock = Mock()
        mock.status_code = 200
        
        if "accounts/by-riot-id" in url:
            mock.json.return_value = mock_account_response
        elif "summoners/by-puuid" in url:
            mock.json.return_value = mock_summoner_response
        elif "matches/by-puuid" in url:
            mock.json.return_value = mock_match_history_response
        elif "matches/match" in url:
            mock.json.return_value = mock_api_response
        return mock
        
    mock_requests.get.side_effect = get_mock_response
    
    # Test the complete flow
    matches = riot_collector.collect_match_history(
        game_name="TestPlayer",
        tag_line="TR1",
        days=1,
        queue_type=420
    )
    
    assert len(matches) == 3
    assert all(isinstance(match, GameData) for match in matches)
    
    # Verify the first match details
    match = matches[0]
    assert match.game_mode == GameMode.CLASSIC
    assert len(match.teams) == 2
    
    # Verify webhook notifications were sent
    assert mock_requests.post.call_count >= 3  # Should have notifications for each match

def test_error_handling(riot_collector, mock_requests):
    """Test error handling and retries"""
    # Simulate API errors
    mock_requests.get.return_value.status_code = 429  # Rate limit error
    mock_requests.get.return_value.raise_for_status.side_effect = Exception("Rate limit exceeded")
    
    with pytest.raises(Exception):
        riot_collector.get_account_by_riot_id("TestPlayer", "TR1")
    
    # Should have attempted 3 retries
    assert mock_requests.get.call_count == 3
    
    # Verify error webhook was sent
    assert mock_requests.post.call_count == 1
    webhook_call = mock_requests.post.call_args
    assert "error" in webhook_call[1]["json"]["event_type"]

def test_rate_limiting(riot_collector, mock_requests, mock_account_response):
    """Test rate limiting behavior"""
    mock_requests.get.return_value.json.return_value = mock_account_response
    
    start_time = datetime.now()
    
    # Make multiple requests
    for _ in range(25):  # More than the rate limit
        riot_collector.get_account_by_riot_id("TestPlayer", "TR1")
    
    end_time = datetime.now()
    
    # Should have taken at least 1 second due to rate limiting
    assert (end_time - start_time).total_seconds() >= 1 