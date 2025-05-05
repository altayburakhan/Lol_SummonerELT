from typing import Dict, Any, Optional
import os
from riotwatcher import LolWatcher
from dotenv import load_dotenv

class RiotAPIClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('RIOT_API_KEY')
        if not self.api_key:
            raise ValueError("RIOT_API_KEY environment variable is not set")
        self.watcher = LolWatcher(self.api_key)
        
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