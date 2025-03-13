from typing import Dict

import polars as pl

from .models import GameSummaryResponse, TeamResponse, TeamsResponse


def parse_game_summary(response: GameSummaryResponse) -> Dict[str, pl.DataFrame]:
    """
    Parse game summary response into structured DataFrames.
    
    Args:
        response: Game summary response object
        
    Returns:
        Dictionary containing DataFrames for different aspects of the game:
        - team_stats: Team-level statistics
        - player_stats: Player-level statistics
        - plays: Play-by-play data
    """
    # Parse team statistics
    team_stats_records = []
    for team in response.boxscore.teams:
        team_data = team["team"]
        stats = {stat["name"]: stat["displayValue"] for stat in team["statistics"]}
        record = {
            "team_id": team_data["id"],
            "team_name": team_data["displayName"],
            **stats
        }
        team_stats_records.append(record)
    
    team_stats_df = pl.DataFrame(team_stats_records)
    
    # Parse player statistics if available
    player_stats_records = []
    if response.boxscore.players:
        for team in response.boxscore.players:
            team_id = team["team"]["id"]
            for player in team["statistics"]:
                for athlete in player["athletes"]:
                    stats = {
                        stat["name"]: stat["displayValue"]
                        for stat in athlete["stats"]
                    }
                    record = {
                        "team_id": team_id,
                        "player_id": athlete["athlete"]["id"],
                        "player_name": athlete["athlete"]["displayName"],
                        **stats
                    }
                    player_stats_records.append(record)
    
    player_stats_df = (
        pl.DataFrame(player_stats_records) if player_stats_records else None
    )
    
    # Parse play-by-play data if available
    play_records = []
    if response.plays:
        for play in response.plays:
            record = {
                "id": play["id"],
                "clock": play.get("clock", {}).get("displayValue"),
                "period": play.get("period", {}).get("number"),
                "text": play.get("text", ""),
                "scoring_play": play.get("scoringPlay", False),
                "score_value": play.get("scoreValue", 0),
                "team_id": play.get("team", {}).get("id") if play.get("team") else None,
                "coordinate_x": (
                    play.get("coordinate", {}).get("x") 
                    if play.get("coordinate") else None
                ),
                "coordinate_y": (
                    play.get("coordinate", {}).get("y") 
                    if play.get("coordinate") else None
                ),
            }
            play_records.append(record)
    
    plays_df = pl.DataFrame(play_records) if play_records else None
    
    return {
        "team_stats": team_stats_df,
        "player_stats": player_stats_df,
        "plays": plays_df
    }

def parse_team_data(response: TeamResponse) -> pl.DataFrame:
    """
    Parse team response into a DataFrame.
    
    Args:
        response: Team response object
        
    Returns:
        DataFrame containing team information
    """
    team = response.team
    record = {
        "id": team.id,
        "name": team.name,
        "location": team.location,
        "abbreviation": team.abbreviation,
        "display_name": team.display_name,
        "color": team.color,
        "alternate_color": team.alternate_color,
        "logo_url": team.logos[0]["href"] if team.logos else None
    }
    return pl.DataFrame([record])

def parse_teams_list(response: TeamsResponse) -> pl.DataFrame:
    """
    Parse teams list response into a DataFrame.
    
    Args:
        response: Teams response object
        
    Returns:
        DataFrame containing all teams information
    """
    records = []
    for sport in response.sports:
        for league in sport["leagues"]:
            for team in league["teams"]:
                record = {
                    "id": team["id"],
                    "name": team["name"],
                    "location": team["location"],
                    "abbreviation": team["abbreviation"],
                    "display_name": team["displayName"],
                    "color": team.get("color"),
                    "alternate_color": team.get("alternateColor"),
                    "logo_url": team["logos"][0]["href"] if team.get("logos") else None,
                    "conference": team.get("groups", {}).get("name"),
                    "division": team.get("groups", {}).get("division")
                }
                records.append(record)
    
    return pl.DataFrame(records)
