import os
import time
from typing import Dict, List, Optional, Any
import requests
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv

from utils.api_utils import APIVersion, RateLimiter, retry_with_backoff
from utils.cache_manager import CacheManager
from utils.webhook_manager import WebhookManager, WebhookEventType, WebhookConfig
from models.game_models import (
    GameData, TeamData, ParticipantData, ParticipantStats,
    ObjectiveEvent, PlayerPerformanceMetrics, TeamSide, GameMode
)

class RiotDataCollector:
    def __init__(self, api_key: str, region: str = "tr1"):
        """Initialize the Riot Data Collector with enhanced features"""
        self.api_key = api_key
        self.region = region
        self.routing = "europe" if region in ["tr1", "eun1", "euw1"] else "americas"
        
        # API URLs
        self.ACCOUNT_BASE_URL = f"https://{self.routing}.api.riotgames.com"
        self.LOL_BASE_URL = f"https://{self.region}.api.riotgames.com"
        self.MATCH_V5_BASE_URL = f"https://{self.routing}.api.riotgames.com"
        
        # Headers for API requests
        self.headers = {
            "X-Riot-Token": self.api_key
        }
        
        # Initialize utilities
        self.rate_limiter = RateLimiter(requests_per_second=20)
        self.cache = CacheManager(cache_dir=".cache/riot_api")
        self.webhook_manager = WebhookManager()
        
    @retry_with_backoff(max_retries=3)
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make an API request with rate limiting and retries"""
        self.rate_limiter.wait_if_needed()
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
        
    def get_account_by_riot_id(self, game_name: str, tag_line: str) -> Optional[Dict]:
        """Get account info by Riot ID with caching"""
        cache_key = f"account_{game_name}_{tag_line}"
        
        # Check cache first
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data
            
        # Make API request
        url = f"{self.ACCOUNT_BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        try:
            data = self._make_request(url)
            self.cache.set(cache_key, data)
            return data
        except Exception as e:
            self.webhook_manager.notify_error({
                "error": str(e),
                "endpoint": "account_by_riot_id",
                "game_name": game_name,
                "tag_line": tag_line
            })
            raise
            
    def get_summoner_by_puuid(self, puuid: str) -> Optional[Dict]:
        """Get summoner info by PUUID with caching"""
        cache_key = f"summoner_{puuid}"
        
        # Check cache first
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data
            
        # Make API request
        url = f"{self.LOL_BASE_URL}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        try:
            data = self._make_request(url)
            self.cache.set(cache_key, data)
            return data
        except Exception as e:
            self.webhook_manager.notify_error({
                "error": str(e),
                "endpoint": "summoner_by_puuid",
                "puuid": puuid
            })
            raise
            
    def get_match_history(
        self,
        puuid: str,
        count: int = 20,
        queue_type: Optional[int] = None,
        start_time: Optional[datetime] = None
    ) -> List[str]:
        """Get match history with additional filters"""
        url = f"{self.MATCH_V5_BASE_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {
            "start": 0,
            "count": count
        }
        
        if queue_type is not None:
            params["queue"] = queue_type
            
        if start_time is not None:
            params["startTime"] = int(start_time.timestamp())
            
        try:
            return self._make_request(url, params)
        except Exception as e:
            self.webhook_manager.notify_error({
                "error": str(e),
                "endpoint": "match_history",
                "puuid": puuid,
                "params": params
            })
            raise
            
    def get_match_details(self, match_id: str) -> GameData:
        """Get match details with enhanced data model"""
        cache_key = f"match_{match_id}"
        
        # Check cache first
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return GameData(**cached_data)
            
        # Make API request
        url = f"{self.MATCH_V5_BASE_URL}/lol/match/v5/matches/{match_id}"
        try:
            raw_data = self._make_request(url)
            
            # Transform raw data into our data model
            game_data = self._transform_match_data(raw_data)
            
            # Cache the transformed data
            self.cache.set(cache_key, game_data.dict())
            
            return game_data
            
        except Exception as e:
            self.webhook_manager.notify_error({
                "error": str(e),
                "endpoint": "match_details",
                "match_id": match_id
            })
            raise
            
    def _transform_match_data(self, raw_data: Dict[str, Any]) -> GameData:
        """Transform raw match data into our data model"""
        info = raw_data.get("info", {})
        
        # Process participants by team
        teams_data = {}
        for participant in info.get("participants", []):
            team_id = participant.get("teamId")
            if team_id not in teams_data:
                teams_data[team_id] = {
                    "side": TeamSide.BLUE if team_id == 100 else TeamSide.RED,
                    "participants": [],
                    "total_kills": 0,
                    "total_gold": 0,
                    "objectives_taken": [],
                    "is_winner": participant.get("win")
                }
                
            # Create participant stats
            stats = ParticipantStats(
                kills=participant.get("kills", 0),
                deaths=participant.get("deaths", 0),
                assists=participant.get("assists", 0),
                champion_level=participant.get("champLevel", 1),
                total_damage_dealt=participant.get("totalDamageDealt", 0),
                gold_earned=participant.get("goldEarned", 0),
                creep_score=participant.get("totalMinionsKilled", 0) + participant.get("neutralMinionsKilled", 0),
                vision_score=participant.get("visionScore", 0)
            )
            
            # Create participant data
            participant_data = ParticipantData(
                summoner_name=participant.get("summonerName", ""),
                summoner_id=participant.get("summonerId", ""),
                champion_name=participant.get("championName", ""),
                team=teams_data[team_id]["side"],
                role=participant.get("teamPosition"),
                stats=stats,
                items=[participant.get(f"item{i}", 0) for i in range(7)],
                spells=[participant.get("summoner1Id"), participant.get("summoner2Id")],
                runes=participant.get("perks")
            )
            
            teams_data[team_id]["participants"].append(participant_data)
            teams_data[team_id]["total_kills"] += stats.kills
            teams_data[team_id]["total_gold"] += stats.gold_earned
            
        # Create team data objects
        teams = [
            TeamData(**team_data)
            for team_data in teams_data.values()
        ]
        
        # Create game data
        game_data = GameData(
            game_id=str(info.get("gameId")),
            platform_id=info.get("platformId", ""),
            game_mode=GameMode(info.get("gameMode", "CLASSIC")),
            game_type=info.get("gameType", ""),
            game_version=info.get("gameVersion", ""),
            game_start_time=datetime.fromtimestamp(info.get("gameStartTimestamp", 0)/1000, UTC),
            game_duration=info.get("gameDuration", 0),
            teams=teams
        )
        
        # Notify about game completion
        self.webhook_manager.notify_game_end(game_data.dict())
        
        return game_data
        
    def collect_match_history(
        self,
        game_name: str,
        tag_line: str,
        days: int = 1,
        queue_type: Optional[int] = None
    ) -> List[GameData]:
        """Collect match history with enhanced error handling and notifications"""
        try:
            # Get account info
            account = self.get_account_by_riot_id(game_name, tag_line)
            if not account:
                raise ValueError(f"Account not found for {game_name}#{tag_line}")
                
            # Get summoner info
            summoner = self.get_summoner_by_puuid(account["puuid"])
            if not summoner:
                raise ValueError(f"Summoner not found for {game_name}#{tag_line}")
                
            # Calculate start time
            start_time = datetime.now(UTC) - timedelta(days=days)
            
            # Get match history
            match_ids = self.get_match_history(
                account["puuid"],
                count=100,
                queue_type=queue_type,
                start_time=start_time
            )
            
            if not match_ids:
                return []
                
            # Get match details for all matches
            matches = []
            for match_id in match_ids:
                try:
                    match = self.get_match_details(match_id)
                    matches.append(match)
                except Exception as e:
                    self.webhook_manager.notify_error({
                        "error": str(e),
                        "endpoint": "match_details",
                        "match_id": match_id
                    })
                    continue
                    
            return matches
            
        except Exception as e:
            self.webhook_manager.notify_error({
                "error": str(e),
                "endpoint": "collect_match_history",
                "game_name": game_name,
                "tag_line": tag_line
            })
            raise

if __name__ == "__main__":
    # Use API key directly for testing
    api_key = "RGAPI-c50d9503-b21e-4204-9222-41d3b56db98e"
    region = "tr1"
    
    # Initialize collector
    collector = RiotDataCollector(api_key, region=region)
    
    # Test data collection
    game_name = "RavixOfFourhorn"
    tag_line = "TR1"
    days = 7  # Look for matches in the last 7 days
    
    # Queue type mapping
    queue_types = {
        400: "Normal Draft",
        420: "Ranked Solo/Duo",
        430: "Normal Blind",
        440: "Ranked Flex",
        450: "Arena",
        700: "Clash",
        830: "Co-op vs AI",
        840: "Co-op vs AI (Intro)",
        850: "Co-op vs AI (Beginner)",
        860: "Co-op vs AI (Intermediate)"
    }
    
    try:
        # Get account info once
        print("\nGetting account info...")
        account = collector.get_account_by_riot_id(game_name, tag_line)
        if not account:
            print(f"Account not found for {game_name}#{tag_line}")
            exit(1)
            
        # Get summoner info
        print("\nGetting summoner info...")
        summoner = collector.get_summoner_by_puuid(account['puuid'])
        if not summoner:
            print(f"Summoner not found for {game_name}#{tag_line}")
            exit(1)
            
        # Get all matches first
        print("\nGetting match history...")
        all_matches = []
        for queue_id in queue_types.keys():
            match_ids = collector.get_match_history(account['puuid'], count=20, queue_type=queue_id)
            if match_ids:
                for match_id in match_ids:
                    try:
                        match = collector.get_match_details(match_id)
                        if match:
                            all_matches.append(match)
                            print(f"✓ Got details for match {match_id}")
                    except Exception as e:
                        print(f"Error getting match details for {match_id}: {str(e)}")
                        continue
            
        # Group matches by queue type
        matches_by_queue = {}
        for match in all_matches:
            queue_id = match.get('info', {}).get('queueId', 0)
            if queue_id in queue_types:
                if queue_id not in matches_by_queue:
                    matches_by_queue[queue_id] = []
                matches_by_queue[queue_id].append(match)
        
        # Display matches by queue type
        for queue_id, queue_name in queue_types.items():
            matches = matches_by_queue.get(queue_id, [])
            print(f"\n{'='*50}")
            print(f"{queue_name} Matches")
            print(f"{'='*50}")
            
            if matches:
                print(f"\nFound {len(matches)} matches:")
                for match in matches:
                    print("\n" + collector.format_match_details(match))
            else:
                print(f"No matches found")
                
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1) 