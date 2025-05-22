import os
from dotenv import load_dotenv
import requests
import time

def get_riot_api_headers():
    """Get Riot API headers with API key"""
    # Explicitly load the .env file here
    load_dotenv(override=True)
    api_key = os.getenv('RIOT_API_KEY')
    print(f"Using API Key: {api_key}")
    if not api_key:
        raise ValueError("RIOT_API_KEY not found in .env file")
    return {"X-Riot-Token": api_key}

def get_summoner_by_name(summoner_name, region="tr1"):
    """Get summoner info by name"""
    headers = get_riot_api_headers()
    
    # Update URL to use the platform-specific endpoint
    url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}"
    
    try:
        print(f"Requesting URL: {url}")
        print(f"Headers: {headers}")
        response = requests.get(url, headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Text: {response.text}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting summoner info: {str(e)}")
        return None

def get_account_by_riot_id(game_name, tag_line, region="EUROPE"):
    """Get account info by Riot ID (game name and tag line)"""
    headers = get_riot_api_headers()
    
    # Use regional endpoint for account-v1
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    
    try:
        print(f"Requesting URL: {url}")
        print(f"Headers: {headers}")
        response = requests.get(url, headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Text: {response.text}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting account info: {str(e)}")
        return None

def get_account_by_puuid(puuid, region="EUROPE"):
    """Get account info by PUUID"""
    headers = get_riot_api_headers()
    
    # Use regional endpoint for account-v1
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
    
    try:
        print(f"Requesting URL: {url}")
        print(f"Headers: {headers}")
        response = requests.get(url, headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Text: {response.text}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting account info: {str(e)}")
        return None

def get_recent_matches(puuid, region="EUROPE", count=1):
    """Get recent match IDs for a player"""
    headers = get_riot_api_headers()
    
    # Use regional endpoint for match-v5
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={count}"
    
    try:
        print(f"Requesting URL: {url}")
        print(f"Headers: {headers}")
        response = requests.get(url, headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Text: {response.text}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting recent matches: {str(e)}")
        return None

def main():
    """Get a recent match ID for testing"""
    # Test with a different method - first get account by Riot ID
    game_name = "HolyPhoenix"
    tag_line = "TR1"
    platform_region = "tr1"      # For platform specific APIs like summoner-v4
    regional_routing = "EUROPE"  # For regional APIs like account-v1 and match-v5
    
    print(f"Getting summoner info for {game_name} on {platform_region}...")
    summoner_info = get_summoner_by_name(game_name, platform_region)
    
    if not summoner_info:
        print("Failed to get summoner info")
        # Try directly with Riot ID
        print(f"Trying with Riot ID: {game_name}#{tag_line}...")
        account_info = get_account_by_riot_id(game_name, tag_line, regional_routing)
        
        if not account_info:
            print("Failed to get account info by Riot ID")
            return
        
        puuid = account_info.get('puuid')
        if not puuid:
            print("No PUUID found in account info")
            return
    else:
        puuid = summoner_info.get('puuid')
        if not puuid:
            print("No PUUID found in summoner info")
            return
    
    print(f"Getting account info for PUUID: {puuid}...")
    account_info = get_account_by_puuid(puuid, regional_routing)
    
    if not account_info:
        print("Failed to get account info")
        return
    
    print(f"Getting recent matches...")
    match_ids = get_recent_matches(puuid, regional_routing)
    
    if not match_ids:
        print("Failed to get match IDs")
        return
    
    print("\nRecent match IDs:")
    for match_id in match_ids:
        print(f"- {match_id}")

if __name__ == "__main__":
    # Make sure we reload env variables
    load_dotenv(override=True)
    print(f"Testing .env loading: RIOT_API_KEY={os.getenv('RIOT_API_KEY')}")
    main() 