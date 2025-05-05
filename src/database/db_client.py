from typing import Dict, Any, List
import os
from google.cloud import bigquery
from google.api_core import retry
from dotenv import load_dotenv

class BigQueryClient:
    def __init__(self):
        load_dotenv()
        self.project_id = os.getenv('GCP_PROJECT_ID')
        if not self.project_id:
            raise ValueError("GCP_PROJECT_ID environment variable is not set")
        
        self.client = bigquery.Client(project=self.project_id)
        self.dataset_id = 'lol_analytics'
        self._ensure_dataset_exists()
    
    def _ensure_dataset_exists(self):
        """Ensure the dataset exists, create if it doesn't."""
        dataset_ref = self.client.dataset(self.dataset_id)
        try:
            self.client.get_dataset(dataset_ref)
        except Exception:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            self.client.create_dataset(dataset)
    
    def _read_sql_file(self, filename: str) -> str:
        """
        Read SQL query from file.
        
        Args:
            filename (str): Name of the SQL file
            
        Returns:
            str: SQL query with project and dataset placeholders
        """
        sql_path = os.path.join(os.path.dirname(__file__), 'sql', filename)
        with open(sql_path, 'r') as f:
            query = f.read()
            return query.format(
                project_id=self.project_id,
                dataset_id=self.dataset_id
            )
    
    @retry.Retry(predicate=retry.if_transient_error)
    def insert_match_data(self, match_data: Dict[str, Any]):
        """
        Insert match data into BigQuery.
        
        Args:
            match_data (Dict[str, Any]): Processed match data
        """
        table_id = f"{self.project_id}.{self.dataset_id}.matches"
        
        # Ensure table exists with correct schema
        self._ensure_table_exists(table_id)
        
        # Insert data
        errors = self.client.insert_rows_json(table_id, [match_data])
        if errors:
            raise Exception(f"Error inserting data: {errors}")
    
    def _ensure_table_exists(self, table_id: str):
        """Ensure the table exists with correct schema."""
        try:
            self.client.get_table(table_id)
        except Exception:
            schema = [
                bigquery.SchemaField("match_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("game_duration", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("game_mode", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("game_type", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("participants", "RECORD", mode="REPEATED", fields=[
                    bigquery.SchemaField("summoner_name", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("champion_name", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("kills", "INTEGER", mode="REQUIRED"),
                    bigquery.SchemaField("deaths", "INTEGER", mode="REQUIRED"),
                    bigquery.SchemaField("assists", "INTEGER", mode="REQUIRED"),
                    bigquery.SchemaField("gold_earned", "INTEGER", mode="REQUIRED"),
                    bigquery.SchemaField("vision_score", "INTEGER", mode="REQUIRED"),
                    bigquery.SchemaField("kda_ratio", "FLOAT", mode="REQUIRED"),
                    bigquery.SchemaField("gold_per_minute", "FLOAT", mode="REQUIRED"),
                    bigquery.SchemaField("damage_per_minute", "FLOAT", mode="REQUIRED"),
                    bigquery.SchemaField("vision_score_per_minute", "FLOAT", mode="REQUIRED"),
                    bigquery.SchemaField("win", "BOOLEAN", mode="REQUIRED")
                ])
            ]
            
            table = bigquery.Table(table_id, schema=schema)
            self.client.create_table(table)
    
    def query_match_history(self, summoner_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Query match history for a specific summoner.
        
        Args:
            summoner_name (str): Name of the summoner
            limit (int): Maximum number of matches to return
            
        Returns:
            List[Dict[str, Any]]: List of match data
        """
        query = self._read_sql_file('match_history.sql')
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("summoner_name", "STRING", summoner_name),
                bigquery.ScalarQueryParameter("limit", "INTEGER", limit)
            ]
        )
        
        query_job = self.client.query(query, job_config=job_config)
        return [dict(row.items()) for row in query_job]
    
    def get_player_stats(self, summoner_name: str) -> Dict[str, Any]:
        """
        Get player statistics.
        
        Args:
            summoner_name (str): Name of the summoner
            
        Returns:
            Dict[str, Any]: Player statistics
        """
        query = self._read_sql_file('match_history.sql')
        query = query.split(';')[1]  # Get the second query (average performance metrics)
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("summoner_name", "STRING", summoner_name)
            ]
        )
        
        query_job = self.client.query(query, job_config=job_config)
        results = [dict(row.items()) for row in query_job]
        return results[0] if results else {}
    
    def get_champion_performance(self, summoner_name: str) -> List[Dict[str, Any]]:
        """
        Get champion performance statistics.
        
        Args:
            summoner_name (str): Name of the summoner
            
        Returns:
            List[Dict[str, Any]]: Champion performance statistics
        """
        query = self._read_sql_file('match_history.sql')
        query = query.split(';')[2]  # Get the third query (champion performance)
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("summoner_name", "STRING", summoner_name)
            ]
        )
        
        query_job = self.client.query(query, job_config=job_config)
        return [dict(row.items()) for row in query_job]
    
    def get_technical_indicators(self, summoner_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get technical indicators (RSI, Bollinger Bands).
        
        Args:
            summoner_name (str): Name of the summoner
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Technical indicators
        """
        query = self._read_sql_file('technical_analysis.sql')
        queries = query.split(';')
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("summoner_name", "STRING", summoner_name)
            ]
        )
        
        results = {}
        
        # Get RSI
        rsi_query = queries[0]
        rsi_job = self.client.query(rsi_query, job_config=job_config)
        results['rsi'] = [dict(row.items()) for row in rsi_job]
        
        # Get Bollinger Bands
        bb_query = queries[1]
        bb_job = self.client.query(bb_query, job_config=job_config)
        results['bollinger_bands'] = [dict(row.items()) for row in bb_job]
        
        return results 