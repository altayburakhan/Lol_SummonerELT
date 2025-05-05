import os
import time
from typing import Dict, List, Optional
import requests
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv

class RiotDataCollector:
    def __init__(self, api_key: str, region: str = "tr1"):
        """Initialize the Riot Data Collector"""
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
        
    def get_account_by_riot_id(self, game_name: str, tag_line: str) -> Optional[Dict]:
        """Get account info by Riot ID"""
        url = f"{self.ACCOUNT_BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        print(f"\nCalling Account API:")
        print(f"URL: {url}")
        
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        response.raise_for_status()
        return response.json()
        
    def get_summoner_by_puuid(self, puuid: str) -> Optional[Dict]:
        """Get summoner info by PUUID"""
        url = f"{self.LOL_BASE_URL}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        print(f"\nCalling Summoner API:")
        print(f"URL: {url}")
        
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        response.raise_for_status()
        return response.json()

    def get_match_history(self, puuid: str, count: int = 20, queue_type: Optional[int] = None) -> List[Dict]:
        """Get match history for a player"""
        url = f"{self.MATCH_V5_BASE_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {
            "start": 0,
            "count": count
        }
        
        # Add queue type filter if specified
        if queue_type is not None:
            params["queue"] = queue_type
            
        print(f"\nFetching match history for {puuid}")
        print(f"URL: {url}")
        print(f"Parameters: {params}")
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        response.raise_for_status()
        match_ids = response.json()
        
        print(f"Found {len(match_ids)} matches")
        return match_ids

    def get_match_details(self, match_id: str) -> Dict:
        """Get details for a specific match"""
        url = f"{self.MATCH_V5_BASE_URL}/lol/match/v5/matches/{match_id}"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        response.raise_for_status()
        return response.json()

    def format_match_details(self, match: Dict) -> str:
        """Format match details for display"""
        info = match.get('info', {})
        
        # Basic match details
        game_start = datetime.fromtimestamp(info.get('gameStartTimestamp', 0)/1000, UTC)
        base_details = f"""
Match Details:
Start Time: {game_start}
Duration: {info.get('gameDuration', 'N/A')} seconds
Queue Type: {info.get('queueId', 'N/A')}
Game Mode: {info.get('gameMode', 'N/A')}
"""
        
        # Team details
        teams = {}
        for participant in info.get('participants', []):
            team_id = participant.get('teamId', 0)
            if team_id not in teams:
                teams[team_id] = {
                    'players': [],
                    'win': participant.get('win', False),
                    'total_points': 0  # For Arena mode
                }
            
            # Player details
            player_details = {
                'summoner': participant.get('summonerName', 'Unknown'),
                'champion': participant.get('championName', 'Unknown'),
                'kills': participant.get('kills', 0),
                'deaths': participant.get('deaths', 0),
                'assists': participant.get('assists', 0)
            }
            
            # Add points for Arena mode
            if info.get('gameMode') == 'CHERRY':
                player_details['points'] = participant.get('playerScore', 0)
                teams[team_id]['total_points'] += player_details['points']
            
            teams[team_id]['players'].append(player_details)
        
        # Format team information
        team_info = ""
        for team_id, team in teams.items():
            team_info += f"\nTeam {team_id} ({'Winner' if team['win'] else 'Loser'}):"
            if info.get('gameMode') == 'CHERRY':
                team_info += f" - Total Points: {team['total_points']}"
            
            for player in team['players']:
                if info.get('gameMode') == 'CHERRY':
                    team_info += f"\n  {player['summoner']} ({player['champion']}) - Points: {player.get('points', 0)}"
                else:
                    team_info += f"\n  {player['summoner']} ({player['champion']}) - KDA: {player['kills']}/{player['deaths']}/{player['assists']}"
        
        return f"{base_details}\n{team_info}\n\n---"

    def collect_match_history(self, game_name: str, tag_line: str, days: int = 1, queue_type: Optional[int] = None) -> List[Dict]:
        """Collect match history for a player"""
        try:
            # Get account info
            account = self.get_account_by_riot_id(game_name, tag_line)
            if not account:
                print(f"Account not found for {game_name}#{tag_line}")
                return []
                
            # Get summoner info
            summoner = self.get_summoner_by_puuid(account['puuid'])
            if not summoner:
                print(f"Summoner not found for {game_name}#{tag_line}")
                return []
                
            # Get match history
            match_ids = self.get_match_history(account['puuid'], count=100, queue_type=queue_type)
            if not match_ids:
                print("No matches found")
                return []
                
            # Get match details for all matches
            matches = []
            for match_id in match_ids:
                try:
                    match = self.get_match_details(match_id)
                    if match:
                        matches.append(match)
                except Exception as e:
                    print(f"Error getting match details for {match_id}: {str(e)}")
                    continue
                    
            print(f"\nFound {len(matches)} matches")
            return matches
            
        except Exception as e:
            print(f"Error collecting match history: {str(e)}")
            return []

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