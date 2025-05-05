import os
from dotenv import load_dotenv
import requests
from datetime import datetime, timezone
import json

def get_account_info(api_key, summoner_name, tag):
    """Get account information using Riot Account API"""
    print(f"\nLooking up account: {summoner_name}#{tag}")
    
    account_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{tag}"
    headers = {"X-Riot-Token": api_key}
    
    try:
        response = requests.get(account_url, headers=headers)
        if response.status_code == 200:
            account_data = response.json()
            print(f"Found account - Game Name: {account_data.get('gameName')}")
            return account_data
        else:
            print(f"Error finding account: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error in API call: {str(e)}")
        return None

def get_match_history(api_key, puuid, queue_type=None, start_time=None, count=20):
    """Get match history using Match-V5 API"""
    region = "europe"  # Match-V5 API uses regional routing
    matches_url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    headers = {"X-Riot-Token": api_key}
    
    # Build query parameters
    params = {"count": count}
    if queue_type:
        params["queue"] = queue_type
    if start_time:
        params["startTime"] = start_time
    
    try:
        response = requests.get(matches_url, headers=headers, params=params)
        if response.status_code == 200:
            match_ids = response.json()
            print(f"\nFound {len(match_ids)} matches")
            return match_ids
        else:
            print(f"Error getting match history: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error in API call: {str(e)}")
        return None

def get_match_details(api_key, match_id):
    """Get detailed match information using Match-V5 API"""
    region = "europe"
    match_url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": api_key}
    
    try:
        response = requests.get(match_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting match details: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error in API call: {str(e)}")
        return None

def format_match_details(match_data):
    """Format match details for display"""
    info = match_data.get('info', {})
    
    # Basic match information
    match_info = {
        'gameId': info.get('gameId'),
        'gameMode': info.get('gameMode'),
        'gameDuration': info.get('gameDuration'),
        'gameStartTimestamp': info.get('gameStartTimestamp'),
        'queueId': info.get('queueId')
    }
    
    # Format timestamp
    if match_info['gameStartTimestamp']:
        timestamp = datetime.fromtimestamp(match_info['gameStartTimestamp'] / 1000, tz=timezone.utc)
        match_info['gameStartTime'] = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Process participants
    teams = {'blue': [], 'red': []}
    for participant in info.get('participants', []):
        player_info = {
            'summonerName': participant.get('summonerName'),
            'championName': participant.get('championName'),
            'kills': participant.get('kills'),
            'deaths': participant.get('deaths'),
            'assists': participant.get('assists'),
            'totalDamageDealt': participant.get('totalDamageDealt'),
            'goldEarned': participant.get('goldEarned'),
            'win': participant.get('win')
        }
        
        # Add to appropriate team
        team = 'blue' if participant.get('teamId') == 100 else 'red'
        teams[team].append(player_info)
    
    match_info['teams'] = teams
    return match_info

def print_match_details(match_info):
    """Print formatted match details"""
    print(f"\nMatch Details:")
    print(f"Game Mode: {match_info['gameMode']}")
    print(f"Start Time: {match_info.get('gameStartTime', 'Unknown')}")
    print(f"Duration: {match_info['gameDuration']} seconds")
    
    print("\nBlue Team:")
    for player in match_info['teams']['blue']:
        result = "Won" if player['win'] else "Lost"
        print(f"{player['summonerName']} ({player['championName']}) - "
              f"KDA: {player['kills']}/{player['deaths']}/{player['assists']} - {result}")
    
    print("\nRed Team:")
    for player in match_info['teams']['red']:
        result = "Won" if player['win'] else "Lost"
        print(f"{player['summonerName']} ({player['championName']}) - "
              f"KDA: {player['kills']}/{player['deaths']}/{player['assists']} - {result}")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Get API key and summoner info
    api_key = os.getenv('RIOT_API_KEY')
    summoner_name = os.getenv('SUMMONER_NAME', 'Kaşmir Göksü')
    tag = os.getenv('TAG', '6031')
    
    if not api_key:
        print("Error: RIOT_API_KEY not found in .env file")
        exit(1)
    
    # Get account info
    account_data = get_account_info(api_key, summoner_name, tag)
    if not account_data:
        print("Could not find account")
        exit(1)
    
    # Get match history
    puuid = account_data.get('puuid')
    match_ids = get_match_history(api_key, puuid, count=5)  # Get last 5 matches
    
    if match_ids:
        # Get and print details for each match
        for match_id in match_ids:
            print(f"\nFetching details for match {match_id}")
            match_data = get_match_details(api_key, match_id)
            if match_data:
                match_info = format_match_details(match_data)
                print_match_details(match_info)
            else:
                print(f"Could not get details for match {match_id}")
    else:
        print("No matches found") 