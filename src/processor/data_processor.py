from typing import Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime

class DataProcessor:
    def __init__(self):
        self.window_size = 14  # Default window size for technical indicators
        
    def process_match_data(self, match_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Process raw match data into a structured DataFrame.
        
        Args:
            match_data (Dict[str, Any]): Raw match data from Riot API
            
        Returns:
            pd.DataFrame: Processed match data
        """
        participants = match_data['info']['participants']
        df = pd.DataFrame(participants)
        
        # Add match metadata
        df['match_id'] = match_data['metadata']['matchId']
        df['game_duration'] = match_data['info']['gameDuration']
        df['game_mode'] = match_data['info']['gameMode']
        df['game_type'] = match_data['info']['gameType']
        
        return df
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators for the match data.
        
        Args:
            df (pd.DataFrame): Match data DataFrame
            
        Returns:
            pd.DataFrame: DataFrame with technical indicators
        """
        # Calculate KDA ratio
        df['kda_ratio'] = (df['kills'] + df['assists']) / df['deaths'].replace(0, 1)
        
        # Calculate gold per minute
        df['gold_per_minute'] = df['goldEarned'] / (df['game_duration'] / 60)
        
        # Calculate damage per minute
        df['damage_per_minute'] = df['totalDamageDealtToChampions'] / (df['game_duration'] / 60)
        
        # Calculate vision score per minute
        df['vision_score_per_minute'] = df['visionScore'] / (df['game_duration'] / 60)
        
        return df
    
    def calculate_bollinger_bands(self, data: List[float], window: int = 20) -> Dict[str, List[float]]:
        """
        Calculate Bollinger Bands for a given data series.
        
        Args:
            data (List[float]): Time series data
            window (int): Window size for moving average
            
        Returns:
            Dict[str, List[float]]: Dictionary containing upper, middle, and lower bands
        """
        df = pd.DataFrame(data)
        df['MA'] = df.rolling(window=window).mean()
        df['STD'] = df.rolling(window=window).std()
        
        return {
            'upper': (df['MA'] + (df['STD'] * 2)).tolist(),
            'middle': df['MA'].tolist(),
            'lower': (df['MA'] - (df['STD'] * 2)).tolist()
        }
    
    def calculate_rsi(self, data: List[float], window: int = 14) -> List[float]:
        """
        Calculate Relative Strength Index (RSI) for a given data series.
        
        Args:
            data (List[float]): Time series data
            window (int): Window size for RSI calculation
            
        Returns:
            List[float]: RSI values
        """
        df = pd.DataFrame(data)
        delta = df.diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.tolist() 