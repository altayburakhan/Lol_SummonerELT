import requests
import json
import time
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd

from api.riot_api import RiotAPIClient
from processor.data_processor import DataProcessor
from database.db_client import BigQueryClient
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("live_game_collector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LiveGameCollector")

class LiveGameCollector:
    def __init__(self):
        load_dotenv()
        self.riot_client = RiotAPIClient()
        self.data_processor = DataProcessor()
        self.db_client = BigQueryClient()
        self.base_url = "https://127.0.0.1:2999/liveclientdata"
        self.tracked_summoners = self._load_tracked_summoners()
        self.active_games = {}  # Dict to track active games by summoner ID
        
    def _load_tracked_summoners(self) -> List[Dict[str, Any]]:
        """Load the list of summoners to track from environment or config file."""
        tracked_summoners = []
        
        # Try to load from environment variable first
        summoner_names = os.getenv('TRACKED_SUMMONERS')
        if summoner_names:
            for name in summoner_names.split(','):
                tracked_summoners.append({
                    'name': name.strip(),
                    'region': os.getenv('DEFAULT_REGION', 'tr1')
                })
        
        # If not found or empty, load from summoners.txt
        summoners_file = 'summoners.txt'
        if not tracked_summoners and os.path.exists(summoners_file):
            with open(summoners_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(',')
                        if len(parts) >= 1:
                            summoner = {
                                'name': parts[0].strip(),
                                'region': parts[1].strip() if len(parts) > 1 else 'tr1'
                            }
                            tracked_summoners.append(summoner)
        
        # If still not found, use default
        if not tracked_summoners:
            default_summoner = os.getenv('SUMMONER_NAME')
            if default_summoner:
                tracked_summoners.append({
                    'name': default_summoner,
                    'region': os.getenv('DEFAULT_REGION', 'tr1')
                })
                logger.info(f"Using default summoner: {default_summoner}")
            else:
                logger.warning("No tracked summoners found. Please create 'summoners.txt' or set TRACKED_SUMMONERS env var.")
        else:
            logger.info(f"Tracking {len(tracked_summoners)} summoners")
            
        return tracked_summoners
    
    def get_live_game_data(self, local_client: bool = False) -> Optional[Dict[str, Any]]:
        """
        Collect live game data either from the local client or by checking tracked summoners
        
        Args:
            local_client (bool): Whether to use the local client data API
            
        Returns:
            Optional[Dict[str, Any]]: Game data if found
        """
        if local_client:
            return self._get_local_client_data()
        else:
            # Check all tracked summoners for active games
            for summoner_info in self.tracked_summoners:
                try:
                    summoner = self.riot_client.get_summoner_by_name(
                        summoner_info['name'], 
                        region=summoner_info['region']
                    )
                    
                    # Check if summoner is in game
                    current_game = self.riot_client.get_current_game(
                        summoner['id'], 
                        region=summoner_info['region']
                    )
                    
                    if current_game:
                        logger.info(f"Found active game for {summoner_info['name']}")
                        
                        # Store active game info
                        self.active_games[summoner['id']] = {
                            'game_id': current_game['gameId'],
                            'platform_id': current_game['platformId'],
                            'summoner': summoner,
                            'region': summoner_info['region'],
                            'start_time': current_game['gameStartTime'] / 1000 if 'gameStartTime' in current_game else int(time.time())
                        }
                        
                        return current_game
                    
                except Exception as e:
                    logger.error(f"Error checking game for {summoner_info['name']}: {str(e)}")
            
            return None
    
    def _get_local_client_data(self) -> Optional[Dict[str, Any]]:
        """
        Get game data from the local client API
        
        Returns:
            Optional[Dict[str, Any]]: Game data if found
        """
        try:
            response = requests.get(f"{self.base_url}/allgamedata", verify=False)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Local client returned status code: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Live Client Data API: {str(e)}")
            return None
    
    def process_game_data(self, game_data: Dict[str, Any], local_client: bool = False) -> Optional[pd.DataFrame]:
        """
        Process game data into a structured format
        
        Args:
            game_data (Dict[str, Any]): Raw game data
            local_client (bool): Whether data is from local client
            
        Returns:
            Optional[pd.DataFrame]: Processed game data
        """
        try:
            if local_client:
                return self._process_local_client_data(game_data)
            else:
                return self._process_spectator_data(game_data)
                
        except Exception as e:
            logger.error(f"Error processing game data: {str(e)}")
            return None
    
    def _process_local_client_data(self, game_data: Dict[str, Any]) -> pd.DataFrame:
        """Process data from the local client API"""
        # Extract participants data
        participants = []
        
        active_player = game_data.get('activePlayer', {})
        all_players = game_data.get('allPlayers', [])
        game_info = game_data.get('gameData', {})
        
        for player in all_players:
            scores = player.get('scores', {})
            
            participant = {
                'summoner_name': player.get('summonerName', ''),
                'champion_name': player.get('championName', ''),
                'team': 'BLUE' if player.get('team') == 'ORDER' else 'RED',
                'kills': scores.get('kills', 0),
                'deaths': scores.get('deaths', 0),
                'assists': scores.get('assists', 0),
                'creep_score': scores.get('creepScore', 0),
                'ward_score': scores.get('wardScore', 0),
                'gold': player.get('currentGold', 0) + player.get('totalGold', 0),
                # Calculate KDA ratio
                'kda_ratio': (scores.get('kills', 0) + scores.get('assists', 0)) / max(1, scores.get('deaths', 1))
            }
            participants.append(participant)
        
        # Create DataFrame
        df = pd.DataFrame(participants)
        
        # Add match metadata
        df['match_id'] = f"LIVE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        df['game_duration'] = game_info.get('gameTime', 0)
        df['game_mode'] = game_info.get('gameMode', 'UNKNOWN')
        df['game_type'] = 'LIVE'
        
        # Calculate performance metrics
        game_minutes = max(1, df['game_duration'].iloc[0] / 60)
        df['gold_per_minute'] = df['gold'] / game_minutes
        
        return df
    
    def _process_spectator_data(self, game_data: Dict[str, Any]) -> pd.DataFrame:
        """Process data from the spectator API"""
        # Extract participants data
        participants = []
        
        for participant in game_data.get('participants', []):
            player = {
                'summoner_name': participant.get('summonerName', ''),
                'champion_name': participant.get('championName', ''),
                'team': 'BLUE' if participant.get('teamId') == 100 else 'RED',
                'kills': 0,  # These will be updated post-game
                'deaths': 0,
                'assists': 0,
                'creep_score': 0,
                'ward_score': 0,
                'gold': 0,
                'kda_ratio': 0
            }
            participants.append(player)
        
        # Create DataFrame
        df = pd.DataFrame(participants)
        
        # Add match metadata
        df['match_id'] = str(game_data.get('gameId', f"SPEC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"))
        df['game_duration'] = (int(time.time()) - game_data.get('gameStartTime', int(time.time())) / 1000) if 'gameStartTime' in game_data else 0
        df['game_mode'] = game_data.get('gameMode', 'UNKNOWN')
        df['game_type'] = game_data.get('gameType', 'UNKNOWN')
        
        return df
    
    def save_game_data(self, df: pd.DataFrame, is_complete: bool = False) -> bool:
        """
        Save processed game data to the database
        
        Args:
            df (pd.DataFrame): Processed game data
            is_complete (bool): Whether this is complete post-game data
            
        Returns:
            bool: Success status
        """
        try:
            # Convert DataFrame to dictionary
            match_dict = {
                'match_id': df['match_id'].iloc[0],
                'game_duration': int(df['game_duration'].iloc[0]),
                'game_mode': df['game_mode'].iloc[0],
                'game_type': df['game_type'].iloc[0],
                'participants': json.loads(df.to_json(orient='records'))
            }
            
            # Only save complete games to avoid duplicates
            if is_complete:
                self.db_client.insert_match_data(match_dict)
                logger.info(f"Saved complete game data for match {match_dict['match_id']}")
                return True
            else:
                # For live games, just log the data
                logger.info(f"Collected live game data for match {match_dict['match_id']}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving game data: {str(e)}")
            return False
    
    def check_game_completion(self) -> None:
        """Check if tracked games have completed and save the final data"""
        completed_games = []
        
        for summoner_id, game_info in self.active_games.items():
            try:
                # Check if the game is still active
                current_game = self.riot_client.get_current_game(
                    summoner_id, 
                    region=game_info['region']
                )
                
                # If game is no longer active, fetch match data
                if not current_game:
                    logger.info(f"Game completed for summoner {game_info['summoner']['name']}")
                    
                    # Get match details using match history
                    time.sleep(30)  # Wait for match to be available in match history
                    
                    puuid = game_info['summoner']['puuid']
                    match_history = self.riot_client.get_match_history(puuid, count=1)
                    
                    if match_history:
                        match_id = match_history[0]
                        match_data = self.riot_client.get_match_details(match_id)
                        
                        # Process match data
                        processed_data = self.data_processor.process_match_data(match_data)
                        processed_data = self.data_processor.calculate_technical_indicators(processed_data)
                        
                        # Save to database
                        self.save_game_data(processed_data, is_complete=True)
                    
                    # Mark game as completed
                    completed_games.append(summoner_id)
                    
            except Exception as e:
                logger.error(f"Error checking game completion: {str(e)}")
        
        # Remove completed games from active tracking
        for summoner_id in completed_games:
            if summoner_id in self.active_games:
                del self.active_games[summoner_id]
    
    def run(self, check_interval: int = 60, use_local_client: bool = False) -> None:
        """
        Run the live game collector continuously
        
        Args:
            check_interval (int): Interval between checks in seconds
            use_local_client (bool): Whether to use local client data
        """
        logger.info("Starting live game collector...")
        
        try:
            while True:
                # Check for game completion
                if self.active_games:
                    self.check_game_completion()
                
                # Get game data
                game_data = self.get_live_game_data(local_client=use_local_client)
                
                if game_data:
                    # Process and save data
                    processed_data = self.process_game_data(game_data, local_client=use_local_client)
                    if processed_data is not None:
                        self.save_game_data(processed_data)
                    
                    # Shorter interval for active games
                    logger.info(f"Active games found. Checking again in {check_interval // 2} seconds...")
                    time.sleep(check_interval // 2)
                else:
                    logger.info(f"No active games found. Checking again in {check_interval} seconds...")
                    time.sleep(check_interval)
                    
        except KeyboardInterrupt:
            logger.info("Stopping live game collector...")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

def print_game_summary(game_data: Dict[str, Any]) -> None:
    """Print a summary of the game data (for CLI usage)"""
    active_player = game_data.get('activePlayer', {})
    all_players = game_data.get('allPlayers', [])
    events = game_data.get('events', {}).get('Events', [])
    game_info = game_data.get('gameData', {})
    
    # Print game info
    print("\nGame Information:")
    print(f"Game Time: {game_info.get('gameTime', 0):.0f} seconds")
    print(f"Game Mode: {game_info.get('gameMode', 'N/A')}")
    
    # Print active player info
    print("\nYour Champion Stats:")
    print(f"Champion: {active_player.get('championName', 'N/A')}")
    print(f"Level: {active_player.get('level', 0)}")
    print(f"Current Gold: {active_player.get('currentGold', 0)}")
    
    abilities = active_player.get('abilities', {})
    if abilities:
        print("\nAbility Levels:")
        for key, data in abilities.items():
            print(f"{key}: Level {data.get('abilityLevel', 0)}")
    
    # Print all players info
    print("\nAll Players:")
    for player in all_players:
        team = "Blue" if player.get('team', '') == 'ORDER' else "Red"
        print(f"\n{team} Team - {player.get('summonerName', 'N/A')} as {player.get('championName', 'N/A')}")
        scores = player.get('scores', {})
        print(f"KDA: {scores.get('kills', 0)}/{scores.get('deaths', 0)}/{scores.get('assists', 0)}")
        print(f"CS: {scores.get('creepScore', 0)}")
    
    # Print recent events
    print("\nRecent Events:")
    recent_events = events[-5:] if events else []
    for event in recent_events:
        print(f"- {event.get('EventName', 'Unknown Event')}")

if __name__ == "__main__":
    collector = LiveGameCollector()
    
    # Check for command line arguments
    import sys
    use_local = "--local" in sys.argv
    
    if use_local:
        print("Starting live game collector with local client mode...")
        collector.run(check_interval=10, use_local_client=True)
    else:
        print("Starting live game collector in spectator mode...")
        print("Tracking summoners:", ', '.join([s['name'] for s in collector.tracked_summoners]))
        collector.run(check_interval=60, use_local_client=False) 