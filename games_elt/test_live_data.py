import os
import time
from dotenv import load_dotenv
from api.riot_api import RiotAPIClient
from processor.data_processor import DataProcessor
from database.db_client import BigQueryClient

def test_live_data_collection(summoner_name: str, summoner_tag: str, region: str = "TR1", interval: int = 30):
    """
    Test real-time data collection for a live game.
    
    Args:
        summoner_name (str): Name of the summoner
        summoner_tag (str): Tag of the summoner
        region (str): Server region
        interval (int): Check interval in seconds
    """
    # Initialize clients
    riot_client = RiotAPIClient(region=region)
    data_processor = DataProcessor()
    db_client = BigQueryClient()
    
    print(f"Starting live data collection for {summoner_name}#{summoner_tag} on {region} server")
    print(f"Checking every {interval} seconds...")
    
    try:
        while True:
            # Get account info
            account = riot_client.get_account_by_riot_id(summoner_name, summoner_tag)
            if not account:
                print(f"Could not find account for {summoner_name}#{summoner_tag}")
                break
            
            # Get summoner info
            summoner = riot_client.get_summoner_by_puuid(account['puuid'])
            if not summoner:
                print(f"Could not find summoner info for {summoner_name}#{summoner_tag}")
                break
            
            # Check if summoner is in game
            current_game = riot_client.get_current_game(summoner['id'])
            
            if current_game:
                print("\nFound live game!")
                print(f"Game Mode: {current_game.get('gameMode', 'Unknown')}")
                print(f"Game Type: {current_game.get('gameType', 'Unknown')}")
                print(f"Game Duration: {current_game.get('gameLength', 0) // 60} minutes")
                
                # Process and store game data
                try:
                    processed_data = data_processor.process_match_data(current_game)
                    match_dict = processed_data.to_dict(orient='records')[0]
                    db_client.insert_match_data(match_dict)
                    print("Successfully processed and stored game data")
                except Exception as e:
                    print(f"Error processing game data: {str(e)}")
            else:
                print(f"\n{summoner_name} is not currently in a game")
            
            # Wait for next check
            print(f"\nWaiting {interval} seconds until next check...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nStopping live data collection...")
    except Exception as e:
        print(f"\nError in live data collection: {str(e)}")

if __name__ == "__main__":
    load_dotenv()
    
    # Get test parameters from environment variables or use defaults
    SUMMONER_NAME = os.getenv('TEST_SUMMONER_NAME', 'default_summoner')
    SUMMONER_TAG = os.getenv('TEST_SUMMONER_TAG', 'default_tag')
    REGION = os.getenv('TEST_REGION', 'TR1')
    INTERVAL = int(os.getenv('TEST_INTERVAL', '30'))
    
    test_live_data_collection(SUMMONER_NAME, SUMMONER_TAG, REGION, INTERVAL) 