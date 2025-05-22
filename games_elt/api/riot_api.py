from typing import Dict, Any, Optional, List
import os
from riotwatcher import LolWatcher
from dotenv import load_dotenv
import requests

class RiotAPIClient:
    def __init__(self, api_key: str = None, region: str = "TR1"):
        """Initialize Riot API client"""
        self.api_key = api_key or os.getenv('RIOT_API_KEY')
        if not self.api_key:
            raise ValueError("RIOT_API_KEY not found in environment variables")
        
        # Map region to correct API endpoint
        self.region_mapping = {
            "TR1": "tr1",
            "KR1": "kr1",
            "EUW1": "euw1",
            "EUN1": "eun1",
            "NA1": "na1"
        }
        
        # Map region to correct routing value
        self.routing_mapping = {
            "TR1": "EUROPE",
            "KR1": "ASIA",
            "EUW1": "EUROPE",
            "EUN1": "EUROPE",
            "NA1": "AMERICAS"
        }
        
        self.region = region
        self.api_region = self.region_mapping.get(region, "tr1")
        self.routing = self.routing_mapping.get(region, "EUROPE")
    
    def get_headers(self):
        """Get API headers"""
        return {"X-Riot-Token": self.api_key}
    
    def get_account_by_riot_id(self, game_name: str, tag_line: str) -> Dict:
        """Get account information using Riot Account API"""
        url = f"https://{self.api_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        headers = self.get_headers()
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting account info: {str(e)}")
            return None
    
    def get_summoner_by_puuid(self, puuid: str) -> Dict:
        """Get summoner information using PUUID"""
        url = f"https://{self.api_region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        headers = self.get_headers()
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting summoner info: {str(e)}")
            return None
    
    def get_match_history(self, puuid: str, count: int = 10, queue_type: str = None) -> List[str]:
        """Get match history for a summoner"""
        url = f"https://{self.routing.lower()}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {
            "start": 0,
            "count": count
        }
        if queue_type:
            params["queue"] = queue_type
        
        headers = self.get_headers()
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting match history: {str(e)}")
            return []
    
    def get_match_details(self, match_id: str) -> Dict:
        """Get detailed match information"""
        url = f"https://{self.routing.lower()}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        headers = self.get_headers()
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting match details: {str(e)}")
            return None
    
    def get_summoner_by_name(self, summoner_name: str, region: str = 'tr1') -> Dict[str, Any]:
        """
        Get summoner information by summoner name.
        
        Args:
            summoner_name (str): Name of the summoner
            region (str): Region code (default: 'tr1' for TR server)
            
        Returns:
            Dict[str, Any]: Summoner information
        """
        return self.watcher.summoner.by_name(region, summoner_name)
    
    def get_current_game(self, summoner_id: str, region: str = 'tr1') -> Optional[Dict[str, Any]]:
        """
        Get current game information for a summoner.
        
        Args:
            summoner_id (str): Summoner ID
            region (str): Region code (default: 'tr1' for TR server)
            
        Returns:
            Optional[Dict[str, Any]]: Current game information if in game, None otherwise
        """
        try:
            return self.watcher.spectator.by_summoner(region, summoner_id)
        except Exception:
            return None
    
    def get_match_history(self, puuid: str, count: int = 10) -> list:
        """
        Get match history for a summoner.
        
        Args:
            puuid (str): PUUID of the summoner
            count (int): Number of matches to retrieve
            
        Returns:
            list: List of match IDs
        """
        return self.watcher.match.matchlist_by_puuid('europe', puuid, count=count)
    
    def get_match_details(self, match_id: str) -> Dict[str, Any]:
        """
        Get detailed match information.
        
        Args:
            match_id (str): Match ID
            
        Returns:
            Dict[str, Any]: Detailed match information
        """
        return self.watcher.match.by_id('europe', match_id) 