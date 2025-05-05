from google.cloud import bigquery
from google.oauth2 import service_account
import os

def verify_bigquery_tables():
    """Verify BigQuery table structures"""
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
        
        # List all tables in the dataset
        print(f"\nVerifying tables in dataset: {dataset_id}")
        print("-" * 50)
        
        tables = client.list_tables(f"{project_id}.{dataset_id}")
        
        for table in tables:
            print(f"\nTable: {table.table_id}")
            print("-" * 30)
            
            # Get table details
            table_obj = client.get_table(table)
            
            # Print schema
            print("Schema:")
            for field in table_obj.schema:
                print(f"  {field.name}: {field.field_type}")
                if field.mode == "REPEATED":
                    print("    (REPEATED)")
                if field.fields:  # Nested fields
                    for nested_field in field.fields:
                        print(f"    - {nested_field.name}: {nested_field.field_type}")
                        if nested_field.mode == "REPEATED":
                            print("      (REPEATED)")
                        if nested_field.fields:  # Double nested fields
                            for double_nested in nested_field.fields:
                                print(f"      - {double_nested.name}: {double_nested.field_type}")
            
            # Print table info
            print(f"\nTable Info:")
            print(f"  Created: {table_obj.created}")
            print(f"  Modified: {table_obj.modified}")
            print(f"  Num Rows: {table_obj.num_rows}")
            print(f"  Size (bytes): {table_obj.num_bytes}")
            
            print("-" * 50)
        
        print("\n✅ Table verification completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying tables: {str(e)}")
        return False

if __name__ == "__main__":
    verify_bigquery_tables() 