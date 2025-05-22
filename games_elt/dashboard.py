import dash
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Initialize BigQuery client
credentials = service_account.Credentials.from_service_account_file(
    ".credentials.json",
    scopes=["https://www.googleapis.com/auth/bigquery"]
)
client = bigquery.Client(credentials=credentials, project="lolelt")

def get_riot_api_headers():
    """Get Riot API headers with API key"""
    api_key = os.getenv('RIOT_API_KEY')
    if not api_key:
        raise ValueError("RIOT_API_KEY not found in .env file")
    return {"X-Riot-Token": api_key}

def get_summoner_id(summoner_name, tag, region="TR1"):
    """Get summoner ID from Riot API using new tag system"""
    headers = get_riot_api_headers()
    # URL encode the summoner name and tag
    encoded_name = requests.utils.quote(summoner_name)
    encoded_tag = requests.utils.quote(tag)
    
    # Map region to correct API endpoint
    region_mapping = {
        "TR1": "tr1",
        "KR1": "kr1",
        "EUW1": "euw1",
        "EUN1": "eun1",
        "NA1": "na1"
    }
    
    api_region = region_mapping.get(region, "tr1")
    url = f"https://{api_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
    
    try:
        print(f"Requesting summoner data from: {url}")
        response = requests.get(url, headers=headers)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 404:
            print("Summoner not found")
            return None
            
        response.raise_for_status()
        data = response.json()
        print(f"Found summoner: {data}")
        return data['puuid']
    except Exception as e:
        print(f"Error getting summoner ID: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Response content: {e.response.text}")
        return None

def get_recent_matches(puuid, region="EUROPE"):
    """Get recent matches for a summoner"""
    headers = get_riot_api_headers()
    
    # Map region to correct routing value
    routing_mapping = {
        "TR1": "EUROPE",
        "KR1": "ASIA",
        "EUW1": "EUROPE",
        "EUN1": "EUROPE",
        "NA1": "AMERICAS"
    }
    
    routing = routing_mapping.get(region, "EUROPE")
    url = f"https://{routing.lower()}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=10"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting recent matches: {str(e)}")
        return []

def get_match_details_from_bigquery(match_ids):
    """Get match details from BigQuery"""
    query = f"""
    SELECT *
    FROM `lolelt.lol_analytics.matches`
    WHERE match_id IN UNNEST(@match_ids)
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("match_ids", "STRING", match_ids)
        ]
    )
    
    try:
        query_job = client.query(query, job_config=job_config)
        return query_job.to_dataframe()
    except Exception as e:
        print(f"Error querying BigQuery: {str(e)}")
        return pd.DataFrame()

# Layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("League of Legends Match Analysis", className="text-center mb-4"),
            html.Div([
                dbc.Row([
                    dbc.Col([
                        dbc.Input(
                            id="summoner-name-input",
                            placeholder="Enter summoner name...",
                            type="text",
                            className="mb-3"
                        ),
                    ], width=4),
                    dbc.Col([
                        dbc.Input(
                            id="summoner-tag-input",
                            placeholder="Enter tag (e.g., NA1)...",
                            type="text",
                            className="mb-3"
                        ),
                    ], width=4),
                    dbc.Col([
                        dbc.Select(
                            id="server-select",
                            options=[
                                {"label": "Turkey (TR1)", "value": "TR1"},
                                {"label": "Korea (KR1)", "value": "KR1"},
                                {"label": "Europe West (EUW1)", "value": "EUW1"},
                                {"label": "Europe Nordic (EUN1)", "value": "EUN1"},
                                {"label": "North America (NA1)", "value": "NA1"}
                            ],
                            value="TR1",
                            className="mb-3"
                        ),
                    ], width=4)
                ]),
                dbc.Button("Search", id="search-button", color="primary", className="mb-3")
            ])
        ], width=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Div(id="loading-output"),
            html.Div(id="error-message", className="text-danger"),
            html.Div(id="match-table-container")
        ], width=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Div(id="match-details-container")
        ], width=12)
    ])
], fluid=True)

@app.callback(
    [Output("match-table-container", "children"),
     Output("error-message", "children"),
     Output("loading-output", "children")],
    [Input("search-button", "n_clicks")],
    [State("summoner-name-input", "value"),
     State("summoner-tag-input", "value"),
     State("server-select", "value")]
)
def update_match_table(n_clicks, summoner_name, summoner_tag, server):
    if not n_clicks or not summoner_name or not summoner_tag:
        return None, "Please enter both summoner name and tag", None
    
    # Get summoner ID
    puuid = get_summoner_id(summoner_name, summoner_tag, region=server)
    if not puuid:
        return None, f"Error: Could not find summoner on {server} server. Please check the name and tag.", None
    
    # Get recent matches
    match_ids = get_recent_matches(puuid, region=server)
    if not match_ids:
        return None, "Error: Could not get recent matches", None
    
    # Get match details from BigQuery
    df = get_match_details_from_bigquery(match_ids)
    if df.empty:
        return None, "Error: Could not get match details", None
    
    # Create match table
    table = dash_table.DataTable(
        data=df.to_dict('records'),
        columns=[
            {"name": "Match ID", "id": "match_id"},
            {"name": "Game Mode", "id": "game_mode"},
            {"name": "Game Type", "id": "game_type"},
            {"name": "Game Duration", "id": "game_duration"},
            {"name": "Game Version", "id": "game_version"}
        ],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'whiteSpace': 'normal',
            'height': 'auto',
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        row_selectable='single',
        id='match-table'
    )
    
    return table, None, None

@app.callback(
    Output("match-details-container", "children"),
    [Input("match-table", "selected_rows")],
    [State("match-table", "data")]
)
def update_match_details(selected_rows, table_data):
    if not selected_rows or not table_data:
        return None
    
    selected_match = table_data[selected_rows[0]]
    match_id = selected_match['match_id']
    
    # Get detailed match data from BigQuery
    query = f"""
    SELECT *
    FROM `lolelt.lol_analytics.matches`
    WHERE match_id = @match_id
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("match_id", "STRING", match_id)
        ]
    )
    
    try:
        query_job = client.query(query, job_config=job_config)
        match_data = query_job.to_dataframe().iloc[0]
        
        # Create match details layout
        return html.Div([
            html.H3(f"Match Details: {match_id}"),
            dbc.Row([
                dbc.Col([
                    html.H4("Teams"),
                    html.Div([
                        html.Div([
                            html.H5(f"Team {team['team_id']}"),
                            html.P(f"Win: {'Yes' if team['win'] else 'No'}"),
                            html.H6("Objectives:"),
                            html.Ul([
                                html.Li(f"Baron: {team['objectives']['baron']}"),
                                html.Li(f"Dragon: {team['objectives']['dragon']}"),
                                html.Li(f"Tower: {team['objectives']['tower']}")
                            ])
                        ]) for team in match_data['teams']
                    ])
                ], width=6),
                dbc.Col([
                    html.H4("Participants"),
                    dash_table.DataTable(
                        data=[{
                            "Champion": p['champion_name'],
                            "K/D/A": f"{p['kills']}/{p['deaths']}/{p['assists']}",
                            "Gold": p['gold_earned'],
                            "Damage Dealt": p['total_damage_dealt'],
                            "Vision Score": p['vision_score']
                        } for p in match_data['participants']],
                        columns=[
                            {"name": "Champion", "id": "Champion"},
                            {"name": "K/D/A", "id": "K/D/A"},
                            {"name": "Gold", "id": "Gold"},
                            {"name": "Damage Dealt", "id": "Damage Dealt"},
                            {"name": "Vision Score", "id": "Vision Score"}
                        ],
                        style_table={'overflowX': 'auto'},
                        style_cell={
                            'textAlign': 'left',
                            'padding': '10px',
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        }
                    )
                ], width=6)
            ])
        ])
    except Exception as e:
        return html.Div(f"Error loading match details: {str(e)}")

if __name__ == '__main__':
    app.run_server(debug=True) 