from google.cloud import bigquery
from google.oauth2 import service_account

def create_matches_table():
    """Create the matches table in BigQuery"""
    try:
        # Load credentials and create client
        credentials = service_account.Credentials.from_service_account_file(
            ".credentials.json",
            scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        
        client = bigquery.Client(
            credentials=credentials,
            project="lolelt"
        )
        
        # Define table reference
        table_ref = "lolelt.lol_analytics.matches"
        
        # Delete table if exists
        try:
            client.delete_table(table_ref)
            print(f"Deleted existing table {table_ref}")
        except Exception as e:
            print(f"Table {table_ref} does not exist or could not be deleted: {str(e)}")
        
        # Define schema
        schema = [
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
        
        # Create table
        table = bigquery.Table(table_ref, schema=schema)
        table = client.create_table(table)
        
        print(f"Created table {table.project}.{table.dataset_id}.{table.table_id}")
        return True
        
    except Exception as e:
        print(f"Error creating table: {str(e)}")
        return False

if __name__ == "__main__":
    create_matches_table() 