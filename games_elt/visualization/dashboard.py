from typing import Dict, Any, List
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from dash.dependencies import Input, Output, State
import pandas as pd
from datetime import datetime, timedelta
from database.db_client import BigQueryClient

class Dashboard:
    def __init__(self):
        self.app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.db_client = BigQueryClient()
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """Setup the dashboard layout."""
        self.app.layout = dbc.Container([
            dbc.Row([
                dbc.Col(html.H1("League of Legends Analytics Dashboard", className="text-center my-4"))
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Summoner Search", className="card-title"),
                            dbc.Input(id="summoner-input", type="text", placeholder="Enter summoner name"),
                            dbc.Button("Search", id="search-button", color="primary", className="mt-2")
                        ])
                    ])
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Player Statistics", className="card-title"),
                            html.Div(id="player-stats")
                        ])
                    ])
                ], width=8)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("KDA Ratio Trend", className="card-title"),
                            dcc.Graph(id="kda-trend")
                        ])
                    ])
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Gold per Minute", className="card-title"),
                            dcc.Graph(id="gold-trend")
                        ])
                    ])
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Champion Performance", className="card-title"),
                            dcc.Graph(id="champion-performance")
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Technical Analysis", className="card-title"),
                            dbc.Tabs([
                                dbc.Tab(dcc.Graph(id="rsi-chart"), label="RSI"),
                                dbc.Tab(dcc.Graph(id="bollinger-chart"), label="Bollinger Bands")
                            ])
                        ])
                    ])
                ], width=12)
            ])
        ], fluid=True)
    
    def setup_callbacks(self):
        """Setup dashboard callbacks."""
        @self.app.callback(
            [Output("player-stats", "children"),
             Output("kda-trend", "figure"),
             Output("gold-trend", "figure"),
             Output("champion-performance", "figure"),
             Output("rsi-chart", "figure"),
             Output("bollinger-chart", "figure")],
            [Input("search-button", "n_clicks")],
            [State("summoner-input", "value")]
        )
        def update_dashboard(n_clicks, summoner_name):
            if not n_clicks or not summoner_name:
                empty_fig = go.Figure()
                empty_fig.update_layout(
                    title="No data available",
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                )
                return html.Div("Enter a summoner name and click Search"), empty_fig, empty_fig, empty_fig, empty_fig, empty_fig
            
            try:
                # Get data from BigQuery
                match_history = self.db_client.query_match_history(summoner_name, limit=20)
                player_stats = self.db_client.get_player_stats(summoner_name)
                champion_data = self.db_client.get_champion_performance(summoner_name)
                technical_indicators = self.db_client.get_technical_indicators(summoner_name)
                
                # Player Stats
                stats_html = self._create_stats_html(player_stats)
                
                # KDA Trend
                kda_fig = self._create_kda_trend(match_history)
                
                # Gold Trend
                gold_fig = self._create_gold_trend(match_history)
                
                # Champion Performance
                champ_fig = self._create_champion_performance(champion_data)
                
                # Technical Indicators
                rsi_fig = self._create_rsi_chart(technical_indicators.get('rsi', []))
                bollinger_fig = self._create_bollinger_chart(technical_indicators.get('bollinger_bands', []))
                
                return stats_html, kda_fig, gold_fig, champ_fig, rsi_fig, bollinger_fig
                
            except Exception as e:
                error_msg = html.Div([
                    html.H6("Error retrieving data:"),
                    html.P(str(e))
                ])
                empty_fig = go.Figure()
                empty_fig.update_layout(
                    title="Error retrieving data",
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                )
                return error_msg, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig
    
    def _create_stats_html(self, stats: Dict[str, Any]) -> html.Div:
        """Create HTML for player statistics."""
        if not stats:
            return html.Div("No player statistics available")
        
        return html.Div([
            html.H6(f"Average KDA: {stats.get('avg_kda', 0):.2f}"),
            html.H6(f"Average Gold per Minute: {stats.get('avg_gold_per_minute', 0):.0f}"),
            html.H6(f"Average Vision Score: {stats.get('avg_vision_score', 0):.2f}"),
            html.H6(f"Win Rate: {stats.get('win_rate', 0):.1f}%"),
            html.H6(f"Total Games: {stats.get('total_games', 0)}")
        ])
    
    def _create_kda_trend(self, match_history: List[Dict[str, Any]]) -> go.Figure:
        """Create KDA trend graph."""
        if not match_history:
            fig = go.Figure()
            fig.update_layout(title="No KDA data available")
            return fig
        
        # Extract KDA values and match timestamps
        kda_values = []
        timestamps = []
        
        for match in match_history:
            for participant in match.get('participants', []):
                if participant.get('summoner_name') == match.get('summoner_searched'):
                    kda = participant.get('kda_ratio', 0)
                    kda_values.append(kda)
                    # Use match timestamp if available, otherwise use index
                    timestamp = match.get('game_creation', len(timestamps))
                    if isinstance(timestamp, (int, float)):
                        timestamp = datetime.fromtimestamp(timestamp / 1000) if timestamp > 1e10 else datetime.now() - timedelta(days=len(timestamps))
                    timestamps.append(timestamp)
        
        # Create figure
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps, 
            y=kda_values, 
            mode='lines+markers',
            name='KDA Ratio'
        ))
        
        fig.update_layout(
            title="KDA Ratio Trend",
            xaxis_title="Match Date",
            yaxis_title="KDA Ratio",
            hovermode="x unified"
        )
        
        return fig
    
    def _create_gold_trend(self, match_history: List[Dict[str, Any]]) -> go.Figure:
        """Create gold per minute trend graph."""
        if not match_history:
            fig = go.Figure()
            fig.update_layout(title="No gold data available")
            return fig
        
        # Extract gold values and match timestamps
        gold_values = []
        timestamps = []
        
        for match in match_history:
            for participant in match.get('participants', []):
                if participant.get('summoner_name') == match.get('summoner_searched'):
                    gold = participant.get('gold_per_minute', 0)
                    gold_values.append(gold)
                    # Use match timestamp if available, otherwise use index
                    timestamp = match.get('game_creation', len(timestamps))
                    if isinstance(timestamp, (int, float)):
                        timestamp = datetime.fromtimestamp(timestamp / 1000) if timestamp > 1e10 else datetime.now() - timedelta(days=len(timestamps))
                    timestamps.append(timestamp)
        
        # Create figure
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps, 
            y=gold_values, 
            mode='lines+markers',
            name='Gold per Minute'
        ))
        
        fig.update_layout(
            title="Gold per Minute Trend",
            xaxis_title="Match Date",
            yaxis_title="Gold per Minute",
            hovermode="x unified"
        )
        
        return fig
    
    def _create_champion_performance(self, champion_data: List[Dict[str, Any]]) -> go.Figure:
        """Create champion performance graph."""
        if not champion_data:
            fig = go.Figure()
            fig.update_layout(title="No champion data available")
            return fig
        
        # Extract data
        champions = [item.get('champion_name', '') for item in champion_data]
        win_rates = [item.get('win_rate', 0) for item in champion_data]
        games_played = [item.get('games_played', 0) for item in champion_data]
        
        # Create a bubble chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=champions,
            y=win_rates,
            mode='markers',
            marker=dict(
                size=[g*5 for g in games_played],  # Size based on games played
                sizemode='area',
                sizeref=2.*max(games_played)/(40.**2),
                sizemin=5,
                color=win_rates,
                colorscale='RdYlGn',
                colorbar=dict(title="Win Rate %"),
                cmin=0,
                cmax=100
            ),
            text=[f"{c}<br>Win Rate: {w:.1f}%<br>Games: {g}" for c, w, g in zip(champions, win_rates, games_played)],
            hoverinfo='text'
        ))
        
        fig.update_layout(
            title="Champion Performance",
            xaxis_title="Champion",
            yaxis_title="Win Rate (%)",
            yaxis=dict(range=[0, 100])
        )
        
        return fig
    
    def _create_rsi_chart(self, rsi_data: List[Dict[str, Any]]) -> go.Figure:
        """Create RSI chart."""
        if not rsi_data:
            fig = go.Figure()
            fig.update_layout(title="No RSI data available")
            return fig
        
        # Extract data
        dates = [item.get('match_date', idx) for idx, item in enumerate(rsi_data)]
        rsi_values = [item.get('rsi', 0) for item in rsi_data]
        
        # Create figure
        fig = go.Figure()
        
        # Add RSI line
        fig.add_trace(go.Scatter(
            x=dates,
            y=rsi_values,
            mode='lines',
            name='RSI'
        ))
        
        # Add reference lines
        fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
        fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
        
        fig.update_layout(
            title="Relative Strength Index (RSI)",
            xaxis_title="Match Date",
            yaxis_title="RSI Value",
            yaxis=dict(range=[0, 100])
        )
        
        return fig
    
    def _create_bollinger_chart(self, bollinger_data: List[Dict[str, Any]]) -> go.Figure:
        """Create Bollinger Bands chart."""
        if not bollinger_data:
            fig = go.Figure()
            fig.update_layout(title="No Bollinger Bands data available")
            return fig
        
        # Extract data
        dates = [item.get('match_date', idx) for idx, item in enumerate(bollinger_data)]
        kda_values = [item.get('kda_ratio', 0) for item in bollinger_data]
        upper_band = [item.get('upper_band', 0) for item in bollinger_data]
        middle_band = [item.get('middle_band', 0) for item in bollinger_data]
        lower_band = [item.get('lower_band', 0) for item in bollinger_data]
        
        # Create figure
        fig = go.Figure()
        
        # Add KDA line
        fig.add_trace(go.Scatter(
            x=dates,
            y=kda_values,
            mode='lines',
            name='KDA Ratio',
            line=dict(color='blue')
        ))
        
        # Add Bollinger Bands
        fig.add_trace(go.Scatter(
            x=dates,
            y=upper_band,
            mode='lines',
            name='Upper Band',
            line=dict(width=1, color='rgba(255,0,0,0.5)')
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=middle_band,
            mode='lines',
            name='Middle Band (MA20)',
            line=dict(width=1, color='rgba(0,0,0,0.5)')
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=lower_band,
            mode='lines',
            name='Lower Band',
            line=dict(width=1, color='rgba(0,128,0,0.5)')
        ))
        
        fig.update_layout(
            title="Bollinger Bands (KDA Performance)",
            xaxis_title="Match Date",
            yaxis_title="KDA Value",
            hovermode="x unified"
        )
        
        return fig
    
    def run(self, debug: bool = True, port: int = 8050):
        """Run the dashboard server."""
        self.app.run_server(debug=debug, port=port) 