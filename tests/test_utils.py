import pytest
import time
from datetime import datetime
import json
from pathlib import Path
from games_elt.utils.cache_manager import CacheManager
from games_elt.utils.webhook_manager import WebhookManager, WebhookConfig, WebhookEventType
from games_elt.utils.api_utils import RateLimiter, retry_with_backoff

def test_cache_manager_basic(cache_manager):
    """Test basic cache operations"""
    test_data = {"test": "data"}
    
    # Set and get
    cache_manager.set("test_key", test_data)
    cached = cache_manager.get("test_key")
    assert cached == test_data
    
    # Non-existent key
    assert cache_manager.get("non_existent") is None
    
    # Clear specific key
    cache_manager.clear("test_key")
    assert cache_manager.get("test_key") is None

def test_cache_manager_ttl(test_cache_dir):
    """Test cache TTL functionality"""
    # Create cache with 1 second TTL
    cache_manager = CacheManager(cache_dir=test_cache_dir, ttl=1)
    test_data = {"test": "data"}
    
    # Set data
    cache_manager.set("test_key", test_data)
    assert cache_manager.get("test_key") == test_data
    
    # Wait for TTL to expire
    time.sleep(1.1)
    assert cache_manager.get("test_key") is None

def test_cache_manager_persistence(test_cache_dir):
    """Test cache persistence to disk"""
    cache_manager = CacheManager(cache_dir=test_cache_dir)
    test_data = {"test": "data"}
    
    # Set data
    cache_manager.set("test_key", test_data)
    
    # Verify file exists
    cache_file = Path(test_cache_dir) / "test_key.json"
    assert cache_file.exists()
    
    # Read file directly
    with cache_file.open("r") as f:
        stored_data = json.load(f)
        assert stored_data["value"] == test_data
        assert "timestamp" in stored_data

def test_webhook_manager_basic(webhook_manager, mock_requests):
    """Test basic webhook functionality"""
    # Add webhook
    webhook_config = WebhookConfig(
        url="http://test.webhook/endpoint",
        secret="test-secret",
        events=[WebhookEventType.GAME_START, WebhookEventType.GAME_END]
    )
    webhook_manager.add_webhook(webhook_config)
    
    # Send notification
    test_data = {"game_id": "123", "status": "started"}
    webhook_manager.notify_game_start(test_data)
    
    # Verify request
    assert mock_requests.post.call_count == 1
    args, kwargs = mock_requests.post.call_args
    assert kwargs["url"] == "http://test.webhook/endpoint"
    assert kwargs["headers"]["X-Webhook-Secret"] == "test-secret"
    assert kwargs["json"]["event_type"] == "game_start"
    assert kwargs["json"]["data"] == test_data

def test_webhook_manager_filtering(webhook_manager, mock_requests):
    """Test webhook event filtering"""
    # Add webhook that only listens for game end events
    webhook_config = WebhookConfig(
        url="http://test.webhook/endpoint",
        events=[WebhookEventType.GAME_END]
    )
    webhook_manager.add_webhook(webhook_config)
    
    # Send notifications for different events
    test_data = {"game_id": "123"}
    webhook_manager.notify_game_start(test_data)  # Should not trigger
    webhook_manager.notify_game_end(test_data)    # Should trigger
    
    # Verify only game end notification was sent
    assert mock_requests.post.call_count == 1
    args, kwargs = mock_requests.post.call_args
    assert kwargs["json"]["event_type"] == "game_end"

def test_rate_limiter():
    """Test rate limiting functionality"""
    rate_limiter = RateLimiter(requests_per_second=10)
    
    start_time = time.time()
    
    # Make 20 requests (should take at least 2 seconds)
    for _ in range(20):
        rate_limiter.wait_if_needed()
        
    end_time = time.time()
    duration = end_time - start_time
    
    # Should have taken at least 2 seconds
    assert duration >= 2.0

@retry_with_backoff(max_retries=3, initial_wait=0.1)
def example_function():
    """Example function for testing retry decorator"""
    raise Exception("Test error")

def test_retry_with_backoff():
    """Test retry with backoff decorator"""
    start_time = time.time()
    
    with pytest.raises(Exception):
        example_function()
        
    end_time = time.time()
    duration = end_time - start_time
    
    # Should have attempted 3 times with increasing delays
    # Initial: 0.1s, Second: 0.2s, Third: 0.4s
    # Total should be at least 0.7s
    assert duration >= 0.7

def test_webhook_manager_error_handling(webhook_manager, mock_requests):
    """Test webhook error handling"""
    # Add webhook
    webhook_config = WebhookConfig(url="http://test.webhook/endpoint")
    webhook_manager.add_webhook(webhook_config)
    
    # Simulate webhook endpoint error
    mock_requests.post.return_value.status_code = 500
    mock_requests.post.return_value.text = "Internal Server Error"
    
    # Send notification (should not raise exception)
    test_data = {"test": "data"}
    webhook_manager.notify_error(test_data)
    
    # Verify request was attempted
    assert mock_requests.post.call_count == 1

def test_cache_manager_cleanup(test_cache_dir):
    """Test cache cleanup functionality"""
    cache_manager = CacheManager(cache_dir=test_cache_dir, ttl=1)
    
    # Add some test data
    cache_manager.set("fresh_key", {"test": "fresh"})
    time.sleep(0.5)
    cache_manager.set("stale_key", {"test": "stale"})
    time.sleep(1.0)  # Make stale_key expire
    
    # Run cleanup
    cache_manager.cleanup_expired()
    
    # Verify only fresh data remains
    assert cache_manager.get("fresh_key") is not None
    assert cache_manager.get("stale_key") is None
    
    # Verify files on disk
    cache_dir = Path(test_cache_dir)
    cache_files = list(cache_dir.glob("*.json"))
    assert len(cache_files) == 1  # Only fresh_key file should remain 