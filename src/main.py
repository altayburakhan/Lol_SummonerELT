import os
import time
import argparse
from typing import Dict, Any
from dotenv import load_dotenv

from api.riot_api import RiotAPIClient
from processor.data_processor import DataProcessor
from database.db_client import BigQueryClient
from visualization.dashboard import Dashboard
from live_game_collector import LiveGameCollector

class LoLAnalytics:
    def __init__(self):
        load_dotenv()
        self.riot_client = RiotAPIClient()
        self.data_processor = DataProcessor()
        self.db_client = BigQueryClient()
        self.dashboard = Dashboard()
        self.live_collector = LiveGameCollector()
    
    def collect_match_data(self, summoner_name: str, num_matches: int = 10):
        """
        Collect and process match data for a summoner.
        
        Args:
            summoner_name (str): Name of the summoner
            num_matches (int): Number of matches to collect
        """
        # Get summoner information
        summoner = self.riot_client.get_summoner_by_name(summoner_name)
        
        # Get match history
        match_ids = self.riot_client.get_match_history(summoner['puuid'], count=num_matches)
        
        # Process each match
        for match_id in match_ids:
            try:
                # Get match details
                match_data = self.riot_client.get_match_details(match_id)
                
                # Process match data
                processed_data = self.data_processor.process_match_data(match_data)
                
                # Calculate technical indicators
                processed_data = self.data_processor.calculate_technical_indicators(processed_data)
                
                # Convert to dictionary for database storage
                match_dict = processed_data.to_dict(orient='records')[0]
                
                # Store in database
                self.db_client.insert_match_data(match_dict)
                
                # Respect API rate limits
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing match {match_id}: {str(e)}")
    
    def run_dashboard(self, debug: bool = True, port: int = 8050):
        """
        Run the analytics dashboard.
        
        Args:
            debug (bool): Whether to run in debug mode
            port (int): Port to run the dashboard on
        """
        self.dashboard.run(debug=debug, port=port)
    
    def start_live_collector(self, use_local_client: bool = False, check_interval: int = 60):
        """
        Start collecting live game data.
        
        Args:
            use_local_client (bool): Whether to use local client data
            check_interval (int): Interval between checks in seconds
        """
        print(f"Starting live game collector in {'local client' if use_local_client else 'spectator'} mode")
        self.live_collector.run(check_interval=check_interval, use_local_client=use_local_client)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='LoL Analytics Tool')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Collection command
    collection_parser = subparsers.add_parser('collect', help='Collect match data')
    collection_parser.add_argument('--summoner', '-s', type=str, required=True, help='Summoner name')
    collection_parser.add_argument('--matches', '-m', type=int, default=10, help='Number of matches to collect')
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Run the analytics dashboard')
    dashboard_parser.add_argument('--port', '-p', type=int, default=8050, help='Dashboard port')
    dashboard_parser.add_argument('--debug', '-d', action='store_true', help='Run in debug mode')
    
    # Live collector command
    live_parser = subparsers.add_parser('live', help='Run the live game collector')
    live_parser.add_argument('--local', '-l', action='store_true', help='Use local client data')
    live_parser.add_argument('--interval', '-i', type=int, default=60, help='Check interval in seconds')
    
    args = parser.parse_args()
    
    # Initialize the application
    app = LoLAnalytics()
    
    # Process commands
    if args.command == 'collect':
        app.collect_match_data(args.summoner, args.matches)
    elif args.command == 'dashboard':
        app.run_dashboard(debug=args.debug, port=args.port)
    elif args.command == 'live':
        app.start_live_collector(use_local_client=args.local, check_interval=args.interval)
    else:
        # Default behavior - collect some data and run dashboard
        summoner_name = os.getenv('SUMMONER_NAME', 'default_summoner')
        app.collect_match_data(summoner_name)
        app.run_dashboard()

if __name__ == "__main__":
    main() 