import os
from dotenv import load_dotenv
import requests
from google.cloud import bigquery
from google.oauth2 import service_account

def test_riot_api_connection():
    # Load environment variables
    print("\nLoading environment variables...")
    load_dotenv(override=True)  # Force reload of environment variables
    
    # Get API key and summoner info from environment variables
    api_key = os.getenv('RIOT_API_KEY')
    summoner_name = os.getenv('SUMMONER_NAME', 'Xreyna').strip()  # Remove any extra whitespace
    region = os.getenv('REGION', 'tr1')
    tag = os.getenv('TAG', 'TR1').strip('#')  # Remove # if present
    
    print(f"API Key loaded: {'Yes' if api_key else 'No'}")
    print(f"Original Summoner Name: {summoner_name}")
    print(f"Tag: {tag}")
    print(f"Region: {region}")
    
    if not api_key:
        print("Error: RIOT_API_KEY not found in .env file")
        return False
        
    headers = {"X-Riot-Token": api_key}
    print(f"Headers: {headers}")
    
    # Try different name variations and popular players
    name_variations = [
        summoner_name,            # Original name from .env
        'Faker',                  # Famous KR player
        'Caps',                   # Famous EU player
        'BrokenBlade',            # EU player
        'Jankos',                 # EU player
        'CoreJJ',                 # NA player
        'HolyPhoenix',            # TR player
        'Closer',                 # TR player
        'Elwind',                 # TR player
    ]
    
    # Try different tags (without # symbol)
    tags = ["TR1", "KR", "EUW", "NA1"]
    
    for name in name_variations:
        for current_tag in tags:
            try:
                print(f"\nTrying with name: {name}, Tag: {current_tag}")
                # Test Account API
                print("Testing Account API...")
                # URL encode the summoner name
                encoded_name = requests.utils.quote(name)
                account_url = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{current_tag}"
                print(f"Account URL: {account_url}")
                
                account_response = requests.get(account_url, headers=headers)
                print(f"Response Status Code: {account_response.status_code}")
                
                if account_response.status_code == 200:
                    print("✓ Account API connection successful")
                    account_data = account_response.json()
                    print(f"   Game Name: {account_data.get('gameName', 'N/A')}")
                    print(f"   Tag Line: {account_data.get('tagLine', 'N/A')}")
                    print(f"   PUUID: {account_data.get('puuid', 'N/A')}")
                    
                    # Test Summoner API with PUUID
                    print("\nTesting Summoner API...")
                    puuid = account_data['puuid']
                    
                    # Choose the correct region based on tag
                    api_region = region
                    if current_tag == "KR":
                        api_region = "kr"
                    elif current_tag == "EUW":
                        api_region = "euw1"
                    elif current_tag == "NA1":
                        api_region = "na1"
                    
                    summoner_url = f"https://{api_region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
                    print(f"Summoner URL: {summoner_url}")
                    
                    summoner_response = requests.get(summoner_url, headers=headers)
                    print(f"Response Status Code: {summoner_response.status_code}")
                    
                    if summoner_response.status_code == 200:
                        print("✓ Summoner API connection successful")
                        summoner_data = summoner_response.json()
                        print(f"   Name: {summoner_data.get('name', 'N/A')}")
                        print(f"   Level: {summoner_data.get('summonerLevel', 'N/A')}")
                        return True
                    else:
                        print(f"✗ Summoner API connection failed with status code: {summoner_response.status_code}")
                        print(f"Response: {summoner_response.text}")
                else:
                    print(f"✗ Account API connection failed with status code: {account_response.status_code}")
                    print(f"Response: {account_response.text}")
            except Exception as e:
                print(f"✗ Error trying name variation: {str(e)}")
                continue
    
    print("\n✗ All name variations failed")
    return False

def test_bigquery():
    """Test BigQuery connection and list available datasets and tables"""
    project_id = "lolelt"
    credentials_path = ".credentials.json"
    
    print("\nDebug - Using values:")
    print(f"Project ID: {project_id}")
    print(f"Credentials Path: {credentials_path}")
    
    try:
        # Load service account credentials
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(f"Credentials file not found at {credentials_path}")
            
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        
        # Create BigQuery client
        client = bigquery.Client(
            credentials=credentials,
            project=project_id
        )
        
        # List all datasets
        print("\nListing available datasets:")
        datasets = list(client.list_datasets())
        if not datasets:
            print("No datasets found in project")
        else:
            for dataset in datasets:
                print(f"\nDataset: {dataset.dataset_id}")
                # List all tables in the dataset
                tables = list(client.list_tables(dataset.dataset_id))
                if not tables:
                    print("  No tables found in dataset")
                else:
                    print("  Tables:")
                    for table in tables:
                        print(f"  - {table.table_id}")
        
        # Test query
        print("\nExecuting test query...")
        query = "SELECT 1 as test"
        query_job = client.query(query)
        results = list(query_job.result())
        
        print("✅ BigQuery connection successful")
        print(f"   Test query result: {results[0].test}")
        return True
        
    except FileNotFoundError as e:
        print(f"❌ BigQuery connection failed: {str(e)}")
        print("   Please follow these steps to set up credentials:")
        print("   1. Go to Google Cloud Console")
        print("   2. Select your project 'lolelt'")
        print("   3. Go to IAM & Admin > Service Accounts")
        print("   4. Create a new service account with BigQuery access")
        print("   5. Create and download a JSON key")
        print("   6. Save the JSON file as '.credentials.json' in the project root")
        return False
        
    except Exception as e:
        print(f"❌ BigQuery connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing API connections...")
    print("\nChecking .env file location:")
    print(f"Current working directory: {os.getcwd()}")
    print(f".env file exists: {os.path.exists('.env')}")
    
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            print("\nDebug - .env file contents:")
            print(f.read())
    
    print("\nTesting Riot Games API...")
    riot_success = test_riot_api_connection()
    
    print("\nTesting BigQuery...")
    bigquery_success = test_bigquery()
    
    if riot_success and bigquery_success:
        print("\n✅ All connections successful!")
    else:
        print("\n❌ Some connections failed. Please check the errors above.") 