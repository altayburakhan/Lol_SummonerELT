import time
from typing import Callable, Any, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class APIVersion(str, Enum):
    V4 = "v4"
    V5 = "v5"

class RateLimiter:
    def __init__(self, requests_per_second: int = 20):
        self.requests_per_second = requests_per_second
        self.last_request_time = 0
        self.request_count = 0
        self.window_start = time.time()
        
    def wait_if_needed(self):
        current_time = time.time()
        
        # Reset window if needed
        if current_time - self.window_start >= 1:
            self.window_start = current_time
            self.request_count = 0
            
        # Check if we need to wait
        if self.request_count >= self.requests_per_second:
            wait_time = 1 - (current_time - self.window_start)
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                self.window_start = time.time()
                self.request_count = 0
                
        self.request_count += 1
        self.last_request_time = current_time

def retry_with_backoff(max_retries: int = 3, initial_wait: float = 1.0):
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            wait_time = initial_wait
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:  # Last attempt
                        raise  # Re-raise the last exception
                        
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                        f"Retrying in {wait_time:.2f} seconds..."
                    )
                    
                    time.sleep(wait_time)
                    wait_time *= 2  # Exponential backoff
                    
            return None  # Should never reach here
            
        return wrapper
    return decorator 