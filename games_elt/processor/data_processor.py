from typing import Dict, Any, List
import pandas as pd
import numpy as np
from datetime import datetime

class DataProcessor:
    def __init__(self):
        """Initialize data processor"""
        self.champion_data = self._load_champion_data()
        self.window_size = 14  # Default window size for technical indicators
        
    def _load_champion_data(self) -> Dict[str, Any]:
        """Load champion data from static file"""
        # TODO: Implement champion data loading
        return {}
    
    def process_match_data(self, match_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Process match data from Riot API.
        
        Args:
            match_data (Dict[str, Any]): Raw match data from Riot API
            
        Returns:
            pd.DataFrame: Processed match data
        """
        if not match_data:
            return pd.DataFrame()
        
        # Check if this is live game data
        is_live_game = 'gameId' not in match_data
        
        # Extract basic match information
        processed_data = {
            'match_id': match_data.get('gameId', f"live_{match_data.get('gameStartTime', int(datetime.now().timestamp() * 1000))}"),
            'game_mode': match_data.get('gameMode', 'Unknown'),
            'game_type': match_data.get('gameType', 'Unknown'),
            'game_duration': match_data.get('gameLength', 0) // 1000 if is_live_game else match_data.get('gameDuration', 0),
            'game_version': match_data.get('gameVersion', 'Unknown'),
            'game_creation': match_data.get('gameStartTime', int(datetime.now().timestamp() * 1000)),
            'is_live_game': is_live_game,
            'teams': [],
            'participants': []
        }
        
        # Process teams
        for team in match_data.get('teams', []):
            team_data = {
                'team_id': team.get('teamId', 0),
                'win': team.get('win', False),
                'objectives': {
                    'baron': team.get('objectives', {}).get('baron', {}).get('kills', 0),
                    'dragon': team.get('objectives', {}).get('dragon', {}).get('kills', 0),
                    'tower': team.get('objectives', {}).get('tower', {}).get('kills', 0)
                }
            }
            processed_data['teams'].append(team_data)
        
        # Process participants
        for participant in match_data.get('participants', []):
            participant_data = {
                'summoner_name': participant.get('summonerName', 'Unknown'),
                'champion_name': self._get_champion_name(participant.get('championId', 0)),
                'team_id': participant.get('teamId', 0),
                'kills': participant.get('kills', 0),
                'deaths': participant.get('deaths', 0),
                'assists': participant.get('assists', 0),
                'kda_ratio': self._calculate_kda(participant.get('kills', 0), 
                                               participant.get('deaths', 0), 
                                               participant.get('assists', 0)),
                'gold_earned': participant.get('goldEarned', 0),
                'gold_per_minute': self._calculate_gold_per_minute(participant.get('goldEarned', 0), 
                                                                 processed_data['game_duration']),
                'total_damage_dealt': participant.get('totalDamageDealtToChampions', 0),
                'damage_per_minute': self._calculate_damage_per_minute(participant.get('totalDamageDealtToChampions', 0), 
                                                                     processed_data['game_duration']),
                'vision_score': participant.get('visionScore', 0),
                'vision_score_per_minute': self._calculate_vision_score_per_minute(participant.get('visionScore', 0), 
                                                                                 processed_data['game_duration']),
                'win': participant.get('win', False)
            }
            processed_data['participants'].append(participant_data)
        
        return pd.DataFrame([processed_data])
    
    def _get_champion_name(self, champion_id: int) -> str:
        """Get champion name from champion ID"""
        # TODO: Implement champion name lookup
        return f"Champion_{champion_id}"
    
    def _calculate_kda(self, kills: int, deaths: int, assists: int) -> float:
        """Calculate KDA ratio"""
        if deaths == 0:
            return kills + assists
        return (kills + assists) / deaths
    
    def _calculate_gold_per_minute(self, gold: int, duration: int) -> float:
        """Calculate gold per minute"""
        if duration == 0:
            return 0
        return (gold / duration) * 60
    
    def _calculate_damage_per_minute(self, damage: int, duration: int) -> float:
        """Calculate damage per minute"""
        if duration == 0:
            return 0
        return (damage / duration) * 60
    
    def _calculate_vision_score_per_minute(self, vision_score: int, duration: int) -> float:
        """Calculate vision score per minute"""
        if duration == 0:
            return 0
        return (vision_score / duration) * 60
    
    def calculate_technical_indicators(self, match_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators for match data.
        
        Args:
            match_data (pd.DataFrame): Processed match data
            
        Returns:
            pd.DataFrame: Match data with technical indicators
        """
        if match_data.empty:
            return match_data
        
        # Add technical indicators
        match_data['win_streak'] = 0  # TODO: Implement win streak calculation
        match_data['performance_trend'] = 0  # TODO: Implement performance trend calculation
        
        return match_data
    
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