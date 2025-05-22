from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class TeamSide(str, Enum):
    BLUE = "BLUE"
    RED = "RED"

class GameMode(str, Enum):
    CLASSIC = "CLASSIC"
    ARAM = "ARAM"
    URF = "URF"
    CHERRY = "CHERRY"
    TFT = "TFT"

class ObjectiveType(str, Enum):
    TOWER = "TOWER"
    INHIBITOR = "INHIBITOR"
    HERALD = "HERALD"
    DRAGON = "DRAGON"
    BARON = "BARON"

class ParticipantStats(BaseModel):
    kills: int = Field(ge=0)
    deaths: int = Field(ge=0)
    assists: int = Field(ge=0)
    champion_level: int = Field(ge=1, le=18)
    total_damage_dealt: int = Field(ge=0)
    gold_earned: int = Field(ge=0)
    creep_score: int = Field(ge=0)
    vision_score: int = Field(ge=0)
    
    @property
    def kda_ratio(self) -> float:
        return (self.kills + self.assists) / max(1, self.deaths)

class ParticipantData(BaseModel):
    summoner_name: str
    summoner_id: str
    champion_name: str
    team: TeamSide
    role: Optional[str]
    stats: ParticipantStats
    items: List[int] = Field(max_items=7)  # 6 items + trinket
    runes: Optional[Dict[str, Any]]
    spells: List[int] = Field(max_items=2)

class TeamData(BaseModel):
    side: TeamSide
    participants: List[ParticipantData] = Field(min_items=1, max_items=5)
    total_kills: int = Field(ge=0)
    total_gold: int = Field(ge=0)
    objectives_taken: List[ObjectiveType] = Field(default_factory=list)
    is_winner: Optional[bool]
    
    @property
    def average_kda(self) -> float:
        if not self.participants:
            return 0.0
        return sum(p.stats.kda_ratio for p in self.participants) / len(self.participants)

class GameData(BaseModel):
    game_id: str
    platform_id: str
    game_mode: GameMode
    game_type: str
    game_version: str
    game_start_time: datetime
    game_duration: int = Field(ge=0)  # in seconds
    teams: List[TeamData] = Field(min_items=2, max_items=2)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
class ObjectiveEvent(BaseModel):
    game_id: str
    event_time: datetime  # Time since game start
    objective_type: ObjectiveType
    team: TeamSide
    killer_id: Optional[str]  # Summoner ID of the killer
    assistants: List[str] = Field(default_factory=list)  # List of assistant summoner IDs
    position: Optional[Dict[str, int]]  # x, y coordinates
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PlayerPerformanceMetrics(BaseModel):
    game_id: str
    summoner_id: str
    summoner_name: str
    champion_name: str
    team: TeamSide
    stats: ParticipantStats
    gold_per_minute: float = Field(ge=0.0)
    damage_per_minute: float = Field(ge=0.0)
    cs_per_minute: float = Field(ge=0.0)
    vision_score_per_minute: float = Field(ge=0.0)
    kill_participation: float = Field(ge=0.0, le=1.0)
    damage_share: float = Field(ge=0.0, le=1.0)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 