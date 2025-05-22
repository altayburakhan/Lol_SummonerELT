import os
from dotenv import load_dotenv
import requests
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timezone
import time
import json
import glob

def get_riot_api_headers():
    """Get Riot API headers with API key"""
    load_dotenv()
    api_key = os.getenv('RIOT_API_KEY')
    if not api_key:
        raise ValueError("RIOT_API_KEY not found in .env file")
    return {"X-Riot-Token": api_key}

def get_match_data(match_id, region="EUROPE"):
    """Fetch match data from Riot API"""
    headers = get_riot_api_headers()
    
    # Map regions to their API endpoints
    region_endpoints = {
        "EUROPE": "europe",
        "AMERICAS": "americas",
        "ASIA": "asia",
        "SEA": "sea",
        "TR1": "europe"  # Turkish region uses Europe endpoint
    }
    
    # Extract region from match ID if not provided
    if not region and match_id:
        region = match_id.split('_')[0].upper()
    
    region_endpoint = region_endpoints.get(region.upper(), "europe")
    url = f"https://{region_endpoint}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    
    try:
        print(f"\nAPI Request Details:")
        print(f"URL: {url}")
        print(f"Headers: {headers}")
        
        response = requests.get(url, headers=headers)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 403:
            print("\nError: Invalid or expired API key. Please update your RIOT_API_KEY in .env file")
            return None
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 1))
            print(f"\nRate limit hit. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            return get_match_data(match_id, region)
            
        response.raise_for_status()
        data = response.json()
        print("\nSuccessfully retrieved match data")
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"\nError fetching match data: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response Status: {e.response.status_code}")
            print(f"Response Text: {e.response.text}")
        return None

def transform_match_data(match_data):
    """Transform match data into the required format"""
    try:
        # Extract basic match info
        match_info = match_data['info']
        
        # Create transformed data
        transformed_data = {
            'match_id': match_data['metadata']['matchId'],
            'game_creation': int(match_info['gameCreation']),  # Store as integer timestamp
            'game_duration': match_info['gameDuration'],
            'game_mode': match_info['gameMode'],
            'game_type': match_info['gameType'],
            'game_version': match_info['gameVersion'],
            'map_id': match_info['mapId'],
            'queue_id': match_info['queueId'],
            'platform_id': match_data['metadata']['matchId'].split('_')[0],
            'season_id': match_info.get('seasonId', 0),
            'teams': []
        }
        
        # Process teams
        for team in match_info['teams']:
            team_data = {
                'team_id': team['teamId'],
                'win': team['win'],
                'objectives': {
                    'baron': team['objectives']['baron']['kills'],
                    'champion': team['objectives']['champion']['kills'],
                    'dragon': team['objectives']['dragon']['kills'],
                    'inhibitor': team['objectives']['inhibitor']['kills'],
                    'rift_herald': team['objectives']['riftHerald']['kills'],
                    'tower': team['objectives']['tower']['kills']
                }
            }
            transformed_data['teams'].append(team_data)
        
        # Process participants
        transformed_data['participants'] = []
        for participant in match_info['participants']:
            participant_data = {
                'participant_id': participant['participantId'],
                'team_id': participant['teamId'],
                'champion_id': participant['championId'],
                'champion_name': participant['championName'],
                'kills': participant['kills'],
                'deaths': participant['deaths'],
                'assists': participant['assists'],
                'gold_earned': participant['goldEarned'],
                'total_damage_dealt': participant['totalDamageDealtToChampions'],
                'total_damage_taken': participant['totalDamageTaken'],
                'vision_score': participant['visionScore'],
                'win': participant['win']
            }
            transformed_data['participants'].append(participant_data)
        
        return transformed_data
    except KeyError as e:
        print(f"Error transforming match data: {str(e)}")
        return None

def save_to_json(match_record, output_dir="data"):
    """Save match data to a JSON file"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename with match ID and timestamp
        filename = f"{output_dir}/match_{match_record['match_id']}_{int(time.time())}.json"
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(match_record, f, indent=2, ensure_ascii=False)
            
        print(f"Successfully saved match data to {filename}")
        return True
    except Exception as e:
        print(f"Error saving to JSON: {str(e)}")
        return False

def load_to_bigquery(json_files, project_id="lolelt", dataset_id="lol_analytics", table_id="matches"):
    """Load match data to BigQuery using batch load"""
    try:
        # Load credentials and create client
        credentials = service_account.Credentials.from_service_account_file(
            ".credentials.json",
            scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        
        client = bigquery.Client(
            credentials=credentials,
            project=project_id
        )
        
        # Get table reference
        table_ref = f"{project_id}.{dataset_id}.{table_id}"
        
        # Create job config
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            ignore_unknown_values=True,
            schema=[
                bigquery.SchemaField("match_id", "STRING"),
                bigquery.SchemaField("game_creation", "INTEGER"),
                bigquery.SchemaField("game_duration", "INTEGER"),
                bigquery.SchemaField("game_mode", "STRING"),
                bigquery.SchemaField("game_type", "STRING"),
                bigquery.SchemaField("game_version", "STRING"),
                bigquery.SchemaField("map_id", "INTEGER"),
                bigquery.SchemaField("queue_id", "INTEGER"),
                bigquery.SchemaField("platform_id", "STRING"),
                bigquery.SchemaField("season_id", "INTEGER"),
                bigquery.SchemaField("teams", "RECORD", mode="REPEATED", fields=[
                    bigquery.SchemaField("team_id", "INTEGER"),
                    bigquery.SchemaField("win", "BOOLEAN"),
                    bigquery.SchemaField("objectives", "RECORD", fields=[
                        bigquery.SchemaField("baron", "INTEGER"),
                        bigquery.SchemaField("champion", "INTEGER"),
                        bigquery.SchemaField("dragon", "INTEGER"),
                        bigquery.SchemaField("inhibitor", "INTEGER"),
                        bigquery.SchemaField("rift_herald", "INTEGER"),
                        bigquery.SchemaField("tower", "INTEGER")
                    ])
                ]),
                bigquery.SchemaField("participants", "RECORD", mode="REPEATED", fields=[
                    bigquery.SchemaField("participant_id", "INTEGER"),
                    bigquery.SchemaField("team_id", "INTEGER"),
                    bigquery.SchemaField("champion_id", "INTEGER"),
                    bigquery.SchemaField("champion_name", "STRING"),
                    bigquery.SchemaField("kills", "INTEGER"),
                    bigquery.SchemaField("deaths", "INTEGER"),
                    bigquery.SchemaField("assists", "INTEGER"),
                    bigquery.SchemaField("gold_earned", "INTEGER"),
                    bigquery.SchemaField("total_damage_dealt", "INTEGER"),
                    bigquery.SchemaField("total_damage_taken", "INTEGER"),
                    bigquery.SchemaField("vision_score", "INTEGER"),
                    bigquery.SchemaField("win", "BOOLEAN")
                ])
            ]
        )
        
        # Load data
        for json_file in json_files:
            print(f"\nLoading {json_file} to BigQuery...")
            with open(json_file, 'r', encoding='utf-8') as source_file:
                # Read and validate JSON
                json_data = json.load(source_file)
                print(f"JSON data structure: {json.dumps(json_data, indent=2)[:200]}...")  # Print first 200 chars
                
                # Convert to newline-delimited JSON
                ndjson_data = json.dumps(json_data) + '\n'
                
                # Create a temporary file with the correct format
                temp_file = f"{json_file}.temp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(ndjson_data)
                
                # Load the temporary file
                with open(temp_file, 'rb') as f:
                    job = client.load_table_from_file(
                        f,
                        table_ref,
                        job_config=job_config
                    )
                    job.result()  # Wait for the job to complete
                
                # Clean up temporary file
                os.remove(temp_file)
                print(f"Successfully loaded {json_file} to BigQuery")
        
        return True
    except Exception as e:
        print(f"Error loading to BigQuery: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Response: {e.response.text}")
        return False

def process_match(match_id, region="EUROPE"):
    """Process a single match: fetch, transform, and save"""
    print(f"\nProcessing match {match_id}...")
    
    # Fetch match data
    match_data = get_match_data(match_id, region)
    if not match_data:
        print(f"Failed to fetch match data for {match_id}")
        return False
    
    # Transform data
    match_record = transform_match_data(match_data)
    if not match_record:
        print(f"Failed to transform match data for {match_id}")
        return False
    
    # Save to JSON
    return save_to_json(match_record)

def main():
    """Main function to process matches"""
    # Get region from environment
    load_dotenv()
    default_region = os.getenv('REGION', 'TR1').upper()
    
    # Example match IDs (you can replace these with actual match IDs)
    match_ids = [
        "TR1_1587340154"  # Real match ID from HolyPhoenix
    ]
    
    # Process matches and save to JSON
    for match_id in match_ids:
        success = process_match(match_id, region=default_region)
        if success:
            print(f"Successfully processed match {match_id}")
        else:
            print(f"Failed to process match {match_id}")
        
        # Respect rate limits
        time.sleep(1)  # 1 second delay between requests
    
    # Load all JSON files to BigQuery
    json_files = glob.glob("data/match_*.json")
    if json_files:
        print("\nLoading matches to BigQuery...")
        if load_to_bigquery(json_files):
            print("Successfully loaded all matches to BigQuery")
        else:
            print("Failed to load matches to BigQuery")
    else:
        print("No JSON files found to load")

if __name__ == "__main__":
    main() 