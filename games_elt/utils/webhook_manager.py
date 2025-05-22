import requests
import json
import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

class WebhookEventType(str, Enum):
    GAME_START = "game_start"
    GAME_END = "game_end"
    OBJECTIVE_TAKEN = "objective_taken"
    ERROR = "error"
    PLAYER_PERFORMANCE = "player_performance"

@dataclass
class WebhookConfig:
    url: str
    secret: Optional[str] = None
    events: Optional[List[WebhookEventType]] = None
    
class WebhookManager:
    def __init__(self):
        self.webhooks: List[WebhookConfig] = []
        
    def add_webhook(self, config: WebhookConfig) -> None:
        """Add a new webhook configuration"""
        self.webhooks.append(config)
        
    def remove_webhook(self, url: str) -> None:
        """Remove a webhook by URL"""
        self.webhooks = [w for w in self.webhooks if w.url != url]
        
    def notify(self, event_type: WebhookEventType, data: Dict[str, Any]) -> None:
        """
        Send notification to all registered webhooks
        
        Args:
            event_type (WebhookEventType): Type of event
            data (Dict[str, Any]): Event data
        """
        payload = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        for webhook in self.webhooks:
            # Skip if webhook doesn't subscribe to this event type
            if webhook.events and event_type not in webhook.events:
                continue
                
            try:
                headers = {
                    "Content-Type": "application/json"
                }
                
                # Add secret if configured
                if webhook.secret:
                    headers["X-Webhook-Secret"] = webhook.secret
                    
                response = requests.post(
                    webhook.url,
                    headers=headers,
                    json=payload,
                    timeout=5  # 5 second timeout
                )
                
                if response.status_code not in (200, 201, 202, 204):
                    logger.warning(
                        f"Webhook notification failed for {webhook.url}: "
                        f"Status {response.status_code}, Response: {response.text}"
                    )
                    
            except Exception as e:
                logger.error(f"Error sending webhook notification to {webhook.url}: {str(e)}")
                
    def notify_game_start(self, game_data: Dict[str, Any]) -> None:
        """Notify about game start"""
        self.notify(WebhookEventType.GAME_START, game_data)
        
    def notify_game_end(self, game_data: Dict[str, Any]) -> None:
        """Notify about game end"""
        self.notify(WebhookEventType.GAME_END, game_data)
        
    def notify_objective(self, objective_data: Dict[str, Any]) -> None:
        """Notify about objective taken"""
        self.notify(WebhookEventType.OBJECTIVE_TAKEN, objective_data)
        
    def notify_error(self, error_data: Dict[str, Any]) -> None:
        """Notify about errors"""
        self.notify(WebhookEventType.ERROR, error_data)
        
    def notify_player_performance(self, performance_data: Dict[str, Any]) -> None:
        """Notify about notable player performance"""
        self.notify(WebhookEventType.PLAYER_PERFORMANCE, performance_data) 