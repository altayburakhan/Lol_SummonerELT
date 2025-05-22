from google.cloud import bigquery
from google.oauth2 import service_account
import os

def create_bigquery_tables():
    """Create BigQuery tables for League of Legends analytics"""
    project_id = "lolelt"
    credentials_path = ".credentials.json"
    dataset_id = "lol_analytics"
    
    try:
        # Load service account credentials
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        
        # Create BigQuery client
        client = bigquery.Client(
            credentials=credentials,
            project=project_id
        )
        
        # Define table schemas
        matches_schema = [
            bigquery.SchemaField("match_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("game_creation", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("game_duration", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("game_mode", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("game_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("game_version", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("map_id", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("platform_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("queue_id", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("season_id", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("teams", "RECORD", mode="REPEATED", fields=[
                bigquery.SchemaField("team_id", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("win", "BOOLEAN", mode="REQUIRED"),
                bigquery.SchemaField("objectives", "RECORD", mode="REPEATED", fields=[
                    bigquery.SchemaField("type", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("first", "BOOLEAN", mode="REQUIRED"),
                    bigquery.SchemaField("kills", "INTEGER", mode="REQUIRED")
                ])
            ]),
            bigquery.SchemaField("participants", "RECORD", mode="REPEATED", fields=[
                bigquery.SchemaField("puuid", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("champion_id", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("champion_name", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("team_id", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("kills", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("deaths", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("assists", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("gold_earned", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("total_damage_dealt", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("vision_score", "INTEGER", mode="REQUIRED")
            ])
        ]
        
        live_games_schema = [
            bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("game_start_time", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("game_length", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("game_mode", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("game_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("map_id", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("platform_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("queue_id", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("participants", "RECORD", mode="REPEATED", fields=[
                bigquery.SchemaField("puuid", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("champion_id", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("team_id", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("summoner_name", "STRING", mode="REQUIRED")
            ])
        ]
        
        player_stats_schema = [
            bigquery.SchemaField("puuid", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("summoner_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("region", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("total_games", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("wins", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("losses", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("kda_ratio", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("average_kills", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("average_deaths", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("average_assists", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("average_gold", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("average_vision_score", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("last_updated", "TIMESTAMP", mode="REQUIRED")
        ]
        
        champion_stats_schema = [
            bigquery.SchemaField("champion_id", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("champion_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("total_games", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("wins", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("losses", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("ban_rate", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("pick_rate", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("average_kda", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("average_gold", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("average_damage", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("last_updated", "TIMESTAMP", mode="REQUIRED")
        ]
        
        rankings_schema = [
            bigquery.SchemaField("puuid", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("summoner_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("region", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("queue_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("tier", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("rank", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("league_points", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("wins", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("losses", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("last_updated", "TIMESTAMP", mode="REQUIRED")
        ]
        
        # Create tables
        tables = {
            "matches": matches_schema,
            "live_games": live_games_schema,
            "player_stats": player_stats_schema,
            "champion_stats": champion_stats_schema,
            "rankings": rankings_schema
        }
        
        for table_id, schema in tables.items():
            table_ref = f"{project_id}.{dataset_id}.{table_id}"
            table = bigquery.Table(table_ref, schema=schema)
            
            try:
                table = client.create_table(table)
                print(f"Created table {table_id}")
            except Exception as e:
                if "Already Exists" in str(e):
                    print(f"Table {table_id} already exists")
                else:
                    raise e
        
        print("\n✅ All tables created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False

if __name__ == "__main__":
    create_bigquery_tables() 