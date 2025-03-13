from typing import Dict

import polars as pl

from .models import (
    AthleteResponse,
    AthletesPageResponse,
    GameSummaryResponse,
    GroupsResponse,
    RankingsResponse,
    RosterResponse,
    ScheduleResponse,
    ScoreboardResponse,
    StandingsResponse,
    TeamResponse,
    TeamsResponse,
    TeamStatisticsResponse,
    TournamentResponse,
)


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
                "play_id": play["id"],
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
        "team_id": team.id,
        "team_name": team.display_name,
        "location": team.location,
        "abbreviation": team.abbreviation,
        "color": team.color,
        "alternate_color": team.alternate_color,
        "logo_url": team.logo_url
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
            for team_entry in league["teams"]:
                team = team_entry["team"]
                record = {
                    "team_id": team["id"],
                    "team_name": team["displayName"],
                    "location": team["location"],
                    "abbreviation": team["abbreviation"],
                    "color": team.get("color"),
                    "alternate_color": team.get("alternateColor"),
                    "logo_url": team["logos"][0]["href"] if team.get("logos") else None,
                    "conference": team.get("groups", {}).get("name"),
                    "division": team.get("groups", {}).get("division")
                }
                records.append(record)
    
    return pl.DataFrame(records) if records else pl.DataFrame()

def parse_team_roster(response: RosterResponse) -> pl.DataFrame:
    """
    Parse team roster response into a DataFrame.
    
    Args:
        response: Team roster response from ESPN API
        
    Returns:
        DataFrame containing player information
    """
    records = []
    
    team_id = response.team.id
    team_name = response.team.display_name
    
    for roster_item in response.roster:
        player = roster_item.player
        position = player.position
        
        record = {
            "team_id": team_id,
            "team_name": team_name,
            "player_id": player.id,
            "player_uid": player.uid,
            "player_name": player.display_name,
            "first_name": player.first_name,
            "last_name": player.last_name,
            "jersey": player.jersey,
            "position": position.name if position else None,
            "position_abbreviation": position.abbreviation if position else None,
            "height": player.height,
            "weight": player.weight,
            "age": player.age,
            "college": player.college_name,
            "headshot_url": player.headshot_url
        }
        records.append(record)
    
    if not records:
        # Return empty DataFrame with correct schema
        return pl.DataFrame(schema={
            "team_id": pl.Utf8,
            "team_name": pl.Utf8,
            "player_id": pl.Utf8,
            "player_uid": pl.Utf8,
            "player_name": pl.Utf8,
            "first_name": pl.Utf8,
            "last_name": pl.Utf8,
            "jersey": pl.Utf8,
            "position": pl.Utf8,
            "position_abbreviation": pl.Utf8,
            "height": pl.Utf8,
            "weight": pl.Int64,
            "age": pl.Int64,
            "college": pl.Utf8,
            "headshot_url": pl.Utf8
        })
        
    return pl.DataFrame(records)

def parse_rankings(response: RankingsResponse) -> pl.DataFrame:
    """
    Parse rankings response into a DataFrame.
    
    Args:
        response: Rankings response from ESPN API
        
    Returns:
        DataFrame containing team ranking information
    """
    records = []
    
    for group in response.rankings:
        poll_name = group.name
        poll_type = group.type
        
        for ranked_team in group.rankings:
            record = {
                "poll_name": poll_name,
                "poll_type": poll_type,
                "team_id": ranked_team.id,
                "team_uid": ranked_team.uid,
                "team_name": ranked_team.name,
                "team_nickname": ranked_team.nickname,
                "team_abbreviation": ranked_team.abbreviation,
                "rank": ranked_team.rank,
                "previous_rank": ranked_team.previous_rank,
                "score": ranked_team.score,
                "logo_url": ranked_team.logo_url
            }
            records.append(record)
    
    if not records:
        # Return empty DataFrame with correct schema
        return pl.DataFrame(schema={
            "poll_name": pl.Utf8,
            "poll_type": pl.Utf8,
            "team_id": pl.Utf8,
            "team_uid": pl.Utf8,
            "team_name": pl.Utf8,
            "team_nickname": pl.Utf8,
            "team_abbreviation": pl.Utf8,
            "rank": pl.Int64,
            "previous_rank": pl.Int64,
            "score": pl.Float64,
            "logo_url": pl.Utf8
        })
        
    return pl.DataFrame(records)

def parse_conferences(response: GroupsResponse) -> Dict[str, pl.DataFrame]:
    """
    Parse conferences/groups response into DataFrames.
    
    Args:
        response: Groups response from ESPN API
        
    Returns:
        Dictionary with two DataFrames:
        - 'conferences': DataFrame containing conference information
        - 'conference_teams': DataFrame containing team-to-conference mappings
    """
    conference_records = []
    team_records = []
    
    for conference in response.groups:
        # Conference record
        conf_record = {
            "conference_id": conference.id,
            "conference_uid": conference.uid,
            "conference_name": conference.name,
            "conference_short_name": conference.short_name,
            "conference_abbreviation": conference.abbreviation
        }
        conference_records.append(conf_record)
        
        # Team-to-conference mapping records
        for team_entry in conference.teams:
            if "team" in team_entry:
                team = team_entry["team"]
                team_record = {
                    "conference_id": conference.id,
                    "conference_name": conference.name,
                    "team_id": team.get("id", ""),
                    "team_uid": team.get("uid", ""),
                    "team_name": team.get("name", ""),
                    "team_location": team.get("location", ""),
                    "team_abbreviation": team.get("abbreviation", ""),
                    "team_display_name": team.get("displayName", team.get("name", ""))
                }
                team_records.append(team_record)
    
    # Create DataFrames or empty ones with correct schema if no data
    if not conference_records:
        conferences_df = pl.DataFrame(schema={
            "conference_id": pl.Utf8,
            "conference_uid": pl.Utf8,
            "conference_name": pl.Utf8,
            "conference_short_name": pl.Utf8,
            "conference_abbreviation": pl.Utf8
        })
    else:
        conferences_df = pl.DataFrame(conference_records)
    
    if not team_records:
        conference_teams_df = pl.DataFrame(schema={
            "conference_id": pl.Utf8,
            "conference_name": pl.Utf8,
            "team_id": pl.Utf8,
            "team_uid": pl.Utf8,
            "team_name": pl.Utf8,
            "team_location": pl.Utf8,
            "team_abbreviation": pl.Utf8,
            "team_display_name": pl.Utf8
        })
    else:
        conference_teams_df = pl.DataFrame(team_records)
    
    return {
        "conferences": conferences_df,
        "conference_teams": conference_teams_df
    }

def parse_standings(response: StandingsResponse) -> pl.DataFrame:
    """
    Parse standings response into a DataFrame.
    
    Args:
        response: Standings response from ESPN API
        
    Returns:
        DataFrame containing team standings information
    """
    records = []
    
    for group in response.groups:
        conference_id = group.id
        conference_name = group.name
        conference_abbreviation = group.abbreviation
        
        for team_standing in group.entries:
            team = team_standing.team
            
            # Create a base record
            record = {
                "conference_id": conference_id,
                "conference_name": conference_name,
                "conference_abbreviation": conference_abbreviation,
                "team_id": team.id,
                "team_name": team.display_name,
                "team_abbreviation": team.abbreviation,
                "team_location": team.location
            }
            
            # Add all stats
            for stat in team_standing.stats:
                # Create a suitable column name from the stat name
                col_name = stat.name.lower().replace(" ", "_").replace("-", "_")
                record[col_name] = stat.value
                record[f"{col_name}_display"] = stat.displayValue
            
            records.append(record)
    
    if not records:
        # Return empty DataFrame with minimum schema
        return pl.DataFrame(schema={
            "conference_id": pl.Utf8,
            "conference_name": pl.Utf8,
            "conference_abbreviation": pl.Utf8,
            "team_id": pl.Utf8,
            "team_name": pl.Utf8,
            "team_abbreviation": pl.Utf8,
            "team_location": pl.Utf8
        })
        
    return pl.DataFrame(records)

def parse_team_schedule(response: ScheduleResponse) -> pl.DataFrame:
    """
    Parse team schedule response into a DataFrame.
    
    Args:
        response: Team schedule response from ESPN API
        
    Returns:
        DataFrame containing team schedule information
    """
    records = []
    
    team_id = response.team.id
    team_name = response.team.display_name
    
    for event in response.events:
        
        # Extract competition info from the first competition if available
        competition_data = {}
        if event.competitions and len(event.competitions) > 0:
            competition = event.competitions[0]
            
            # Extract teams involved
            home_team = None
            away_team = None
            if "competitors" in competition:
                for competitor in competition["competitors"]:
                    if "homeAway" in competitor:
                        if competitor["homeAway"] == "home":
                            home_team = competitor.get("team", {})
                        elif competitor["homeAway"] == "away":
                            away_team = competitor.get("team", {})
            
            # Add competition data
            if home_team:
                competition_data.update({
                    "home_team_id": home_team.get("id", ""),
                    "home_team_name": (
                        home_team.get("displayName", home_team.get("name", ""))
                    ),
                    "home_team_abbreviation": home_team.get("abbreviation", "")
                })
            
            if away_team:
                competition_data.update({
                    "away_team_id": away_team.get("id", ""),
                    "away_team_name": (
                        away_team.get("displayName", away_team.get("name", ""))
                    ),
                    "away_team_abbreviation": away_team.get("abbreviation", "")
                })
            
            # Add status information
            if "status" in competition:
                status = competition["status"]
                if isinstance(status, dict):
                    competition_data.update({
                        "status_type": status.get("type", {}).get("name", ""),
                        "status_detail": status.get("type", {}).get("detail", "")
                    })
            
            # Add venue information
            if "venue" in competition:
                venue = competition["venue"]
                if isinstance(venue, dict):
                    competition_data.update({
                        "venue_name": venue.get("fullName", ""),
                        "venue_city": venue.get("address", {}).get("city", ""),
                        "venue_state": venue.get("address", {}).get("state", "")
                    })
        
        record = {
            "team_id": team_id,
            "team_name": team_name,
            "game_id": event.id,
            "game_uid": event.uid,
            "game_date": event.date,
            "game_name": event.name,
            "game_short_name": event.short_name,
            "season_year": event.season.year,
            "season_name": event.season.display_name
        }
        
        # Add competition data if available
        record.update(competition_data)
        
        records.append(record)
    
    if not records:
        # Return empty DataFrame with minimum schema
        return pl.DataFrame(schema={
            "team_id": pl.Utf8,
            "team_name": pl.Utf8,
            "game_id": pl.Utf8,
            "game_uid": pl.Utf8,
            "game_date": pl.Datetime,
            "game_name": pl.Utf8,
            "game_short_name": pl.Utf8,
            "season_year": pl.Int64,
            "season_name": pl.Utf8
        })
        
    return pl.DataFrame(records)

def parse_athlete(response: AthleteResponse) -> dict:
    """
    Parse athlete response into a dictionary.
    
    Args:
        response: Athlete response from ESPN API
        
    Returns:
        Dictionary containing athlete information
    """
    athlete = response.athlete
    return {
        "id": athlete.id,
        "name": athlete.display_name,
        "first_name": athlete.first_name,
        "last_name": athlete.last_name,
        "jersey": athlete.jersey,
        "position_name": athlete.position.name if athlete.position else None,
        "position_abbreviation": (athlete.position.abbreviation 
                                if athlete.position else None),
        "headshot_url": athlete.headshot_url,
        "active": athlete.active
    }

def parse_athletes(response: AthletesPageResponse) -> pl.DataFrame:
    """
    Parse athletes page response into a DataFrame.
    
    Args:
        response: Athletes page response from ESPN API
        
    Returns:
        DataFrame containing athletes information
    """
    records = []
    
    for athlete in response.items:
        record = {
            "id": athlete.id,
            "name": athlete.display_name,
            "first_name": athlete.first_name,
            "last_name": athlete.last_name,
            "jersey": athlete.jersey,
            "position_name": athlete.position.name if athlete.position else None,
            "position_abbreviation": (athlete.position.abbreviation 
                                    if athlete.position else None),
            "headshot_url": athlete.headshot_url,
            "active": athlete.active
        }
        records.append(record)
    
    return pl.DataFrame(records) if records else pl.DataFrame()

def parse_team_statistics(response: TeamStatisticsResponse) -> pl.DataFrame:
    """
    Parse a team statistics response into a Polars DataFrame.
    
    Args:
        response: The team statistics response from the ESPN API
        
    Returns:
        A Polars DataFrame containing the team statistics
    """
    if not response or not response.statistics:
        # Return empty DataFrame with schema
        return pl.DataFrame(schema={
            "team_id": pl.Utf8,
            "team_name": pl.Utf8,
            "category": pl.Utf8,
            "stat_name": pl.Utf8,
            "stat_display_name": pl.Utf8,
            "stat_value": pl.Float64,
            "stat_display_value": pl.Utf8
        })
    
    records = []
    
    team_id = str(response.team.id)
    team_name = response.team.display_name
    
    for category in response.statistics:
        category_name = category.name
        
        for stat in category.stats:
            record = {
                "team_id": team_id,
                "team_name": team_name,
                "category": category_name,
                "stat_name": stat.name,
                "stat_display_name": stat.display_name,
                "stat_value": stat.value,
                "stat_display_value": stat.display_value
            }
            records.append(record)
    
    return pl.DataFrame(records)

def parse_tournament_bracket(response: TournamentResponse) -> dict:
    """
    Parse tournament bracket response into structured DataFrames.
    
    Args:
        response: Tournament bracket response from ESPN API
        
    Returns:
        Dictionary containing DataFrames for different aspects of the tournament:
        - tournament: General tournament information
        - rounds: Round information
        - games: Game information
    """
    result = {}
    
    # Extract tournament information
    tournament = response.tournament
    result["tournament"] = pl.DataFrame([{
        "id": tournament.id,
        "name": tournament.name,
        "short_name": tournament.short_name,
        "year": tournament.season.year
    }])
    
    # Extract round information
    round_records = []
    for round_obj in tournament.rounds:
        round_record = {
            "tournament_id": tournament.id,
            "round_number": round_obj.number,
            "round_name": round_obj.name,
            "short_name": round_obj.short_name
        }
        round_records.append(round_record)
    
    result["rounds"] = (pl.DataFrame(round_records) if round_records 
                       else pl.DataFrame(schema={
        "tournament_id": pl.Utf8,
        "round_number": pl.Int64,
        "round_name": pl.Utf8,
        "short_name": pl.Utf8
    }))
    
    # Extract game information
    game_records = []
    for round_obj in tournament.rounds:
        for competition in round_obj.competitions:
            # Sort competitors to ensure consistent ordering (home team first)
            competitors = sorted(competition.competitors, 
                               key=lambda x: x.home_away == "home", 
                               reverse=True)
            
            # Extract venue name if available
            venue_name = None
            if competition.venue:
                venue_name = competition.venue.name
            
            # Determine winner_id if available
            winner_id = None
            for competitor in competitors:
                if competitor.winner:
                    winner_id = competitor.team.id
                    break
            
            # Create game record
            game_record = {
                "tournament_id": tournament.id,
                "round_number": round_obj.number,
                "game_id": competition.id,
                "game_date": competition.date,
                "team1_id": competitors[0].team.id if len(competitors) > 0 else None,
                "team1_name": (competitors[0].team.display_name 
                             if len(competitors) > 0 else None),
                "team1_seed": (competitors[0].team.seed.rank 
                             if len(competitors) > 0 and competitors[0].team.seed 
                             else None),
                "team1_score": competitors[0].score if len(competitors) > 0 else None,
                "team2_id": competitors[1].team.id if len(competitors) > 1 else None,
                "team2_name": (competitors[1].team.display_name 
                             if len(competitors) > 1 else None),
                "team2_seed": (competitors[1].team.seed.rank 
                             if len(competitors) > 1 and competitors[1].team.seed 
                             else None),
                "team2_score": competitors[1].score if len(competitors) > 1 else None,
                "winner_id": winner_id,
                "venue_name": venue_name,
                "status": competition.status.type.name
            }
            game_records.append(game_record)
    
    result["games"] = (pl.DataFrame(game_records) if game_records 
                      else pl.DataFrame(schema={
        "tournament_id": pl.Utf8,
        "round_number": pl.Int64,
        "game_id": pl.Utf8,
        "game_date": pl.Datetime,
        "team1_id": pl.Utf8,
        "team1_name": pl.Utf8,
        "team1_seed": pl.Int64,
        "team1_score": pl.Utf8,
        "team2_id": pl.Utf8,
        "team2_name": pl.Utf8,
        "team2_seed": pl.Int64,
        "team2_score": pl.Utf8,
        "winner_id": pl.Utf8,
        "venue_name": pl.Utf8,
        "status": pl.Utf8
    }))
    
    return result

def parse_scoreboard(response: ScoreboardResponse) -> pl.DataFrame:
    """
    Parse scoreboard response into a DataFrame.
    
    Args:
        response: Scoreboard response object
        
    Returns:
        DataFrame containing game information
    """
    records = []
    
    for event in response.events:
        for competition in event.competitions:
            home_team = None
            away_team = None
            home_score = None
            away_score = None
            
            for competitor in competition.competitors:
                if competitor.home_away == "home":
                    home_team = competitor.team
                    home_score = competitor.score
                elif competitor.home_away == "away":
                    away_team = competitor.team
                    away_score = competitor.score
            
            if home_team and away_team:
                record = {
                    "game_id": competition.id,
                    "date": competition.date,
                    "home_team_id": home_team.id,
                    "home_team_name": home_team.display_name,
                    "away_team_id": away_team.id,
                    "away_team_name": away_team.display_name,
                    "home_score": home_score,
                    "away_score": away_score,
                    "status": competition.status.type.get("state", ""),
                    "period": competition.status.period,
                    "season_year": event.season.year,
                    "season_type": event.season.type
                }
                records.append(record)
    
    if records:
        return pl.DataFrame(records)
    else:
        # Return empty DataFrame with correct schema
        return pl.DataFrame(schema={
            "game_id": pl.Utf8,
            "date": pl.Datetime,
            "home_team_id": pl.Utf8,
            "home_team_name": pl.Utf8,
            "away_team_id": pl.Utf8,
            "away_team_name": pl.Utf8,
            "home_score": pl.Utf8,
            "away_score": pl.Utf8,
            "status": pl.Utf8,
            "period": pl.Int64,
            "season_year": pl.Int64,
            "season_type": pl.Int64
        })

def process_competition_data(competition_data, competition):
    """Process competition data for standings."""
    for competitor in competition.competitors:
        team = competitor.team 
        if competitor.home_away == "home":
            home_team = {
                "id": team.id,
                "displayName": team.display_name,
                "name": getattr(team, "name", ""),
                "abbreviation": team.abbreviation
            }
            competition_data.update({
                "home_team_id": home_team.get("id", ""),
                "home_team_name": (
                    home_team.get("displayName", home_team.get("name", ""))
                ),
                "home_team_abbreviation": home_team.get("abbreviation", "")
            })
        elif competitor.home_away == "away":
            away_team = {
                "id": team.id,
                "displayName": team.display_name,
                "name": getattr(team, "name", ""),
                "abbreviation": team.abbreviation
            }
            competition_data.update({
                "away_team_id": away_team.get("id", ""),
                "away_team_name": (
                    away_team.get("displayName", away_team.get("name", ""))
                ),
                "away_team_abbreviation": away_team.get("abbreviation", "")
            })
