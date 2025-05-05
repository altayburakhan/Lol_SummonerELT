import os
from dotenv import load_dotenv
import requests
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timezone
import time

def get_riot_api_headers():
    """Get Riot API headers with API key"""
    load_dotenv()
    api_key = os.getenv('RIOT_API_KEY')
    if not api_key:
        raise ValueError("RIOT_API_KEY not found in .env file")
    return {"X-Riot-Token": api_key}

def get_match_data(match_id, region="tr1"):
    """Fetch match data from Riot API"""
    headers = get_riot_api_headers()
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching match data: {str(e)}")
        return None

def transform_match_data(match_data):
    """Transform match data to match BigQuery schema"""
    if not match_data:
        return None
        
    try:
        # Extract basic match info
        match_info = match_data['info']
        
        # Transform teams data
        teams = []
        for team in match_info['teams']:
            team_data = {
                'team_id': team['teamId'],
                'win': team['win'],
                'objectives': []
            }
            
            # Transform objectives
            for objective_type, objective_data in team['objectives'].items():
                if objective_type != 'champion':  # Skip champion objective
                    objective = {
                        'type': objective_type,
                        'first': objective_data.get('first', False),
                        'kills': objective_data.get('kills', 0)
                    }
                    team_data['objectives'].append(objective)
            
            teams.append(team_data)
        
        # Transform participants data
        participants = []
        for participant in match_info['participants']:
            participant_data = {
                'puuid': participant['puuid'],
                'champion_id': participant['championId'],
                'champion_name': participant['championName'],
                'team_id': participant['teamId'],
                'kills': participant['kills'],
                'deaths': participant['deaths'],
                'assists': participant['assists'],
                'gold_earned': participant['goldEarned'],
                'total_damage_dealt': participant['totalDamageDealtToChampions'],
                'vision_score': participant['visionScore']
            }
            participants.append(participant_data)
        
        # Create final match record
        match_record = {
            'match_id': match_data['metadata']['matchId'],
            'game_creation': datetime.fromtimestamp(match_info['gameCreation'] / 1000, tz=timezone.utc),
            'game_duration': match_info['gameDuration'],
            'game_mode': match_info['gameMode'],
            'game_type': match_info['gameType'],
            'game_version': match_info['gameVersion'],
            'map_id': match_info['mapId'],
            'platform_id': match_data['metadata']['platformId'],
            'queue_id': match_info['queueId'],
            'season_id': match_info['seasonId'],
            'teams': teams,
            'participants': participants
        }
        
        return match_record
        
    except Exception as e:
        print(f"Error transforming match data: {str(e)}")
        return None

def load_to_bigquery(match_record):
    """Load match data to BigQuery"""
    project_id = "lolelt"
    dataset_id = "lol_analytics"
    table_id = "matches"
    credentials_path = ".credentials.json"
    
    try:
        # Load credentials and create client
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        
        client = bigquery.Client(
            credentials=credentials,
            project=project_id
        )
        
        # Get table reference
        table_ref = f"{project_id}.{dataset_id}.{table_id}"
        
        # Insert the record
        errors = client.insert_rows_json(table_ref, [match_record])
        
        if errors:
            print(f"Errors inserting rows: {errors}")
            return False
        else:
            print(f"Successfully loaded match {match_record['match_id']}")
            return True
            
    except Exception as e:
        print(f"Error loading to BigQuery: {str(e)}")
        return False

def process_match(match_id, region="tr1"):
    """Process a single match: fetch, transform, and load"""
    print(f"\nProcessing match {match_id}...")
    
    # Fetch match data
    match_data = get_match_data(match_id, region)
    if not match_data:
        return False
    
    # Transform data
    match_record = transform_match_data(match_data)
    if not match_record:
        return False
    
    # Load to BigQuery
    return load_to_bigquery(match_record)

def main():
    """Main function to process matches"""
    # Example match IDs (you can replace these with actual match IDs)
    match_ids = [
        "TR1_1234567890",  # Replace with actual match ID
        "TR1_0987654321"   # Replace with actual match ID
    ]
    
    for match_id in match_ids:
        success = process_match(match_id)
        if success:
            print(f"Successfully processed match {match_id}")
        else:
            print(f"Failed to process match {match_id}")
        
        # Respect rate limits
        time.sleep(1)  # 1 second delay between requests

if __name__ == "__main__":
    main() 