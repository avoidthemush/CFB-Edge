"""
Daily job: computes and stores each team's rolling last-10-games record
(ATS, Over/Under, straight-up win/loss) - materialized into
team_recent_form, one row per team, overwritten daily.

Correctly crosses season boundaries: pulls each team's most recent 10
COMPLETED games regardless of season, not "last 10 this season" - so
Week 1-2 of a new season correctly reaches back into the prior season's
final games, per explicit design requirement.

Uses get_best_line_for_game() (CFBD-priority historical lookup) for
grading - correct here since we're always grading COMPLETED games,
never live/upcoming ones.
"""
from datetime import datetime
from app.db import SessionLocal
from app.models import Team, Game, TeamRecentForm
from app.features.get_game_line import get_best_line_for_game

GAMES_TO_TRACK = 10


def get_last_n_games(team_id, db, n=GAMES_TO_TRACK):
    games = db.query(Game).filter(
        (Game.home_team_id == team_id) | (Game.away_team_id == team_id),
        Game.completed == True,
        Game.home_points.isnot(None), Game.away_points.isnot(None),
    ).order_by(Game.start_date.desc()).limit(n).all()
    return games


def grade_game_for_team(game, team_id, db):
    """Returns dict of ats/ou/su results, from this specific team's perspective."""
    is_home = game.home_team_id == team_id
    team_points = game.home_points if is_home else game.away_points
    opp_points = game.away_points if is_home else game.home_points
    team_margin = team_points - opp_points

    result = {"su_win": team_margin > 0}

    line = get_best_line_for_game(game.id, db)
    if line is None or line.spread_open is None:
        return result  # SU always available; ATS/OU only if a line exists

    home_implied_margin = -line.spread_open
    team_implied_margin = home_implied_margin if is_home else -home_implied_margin
    actual_vs_line = team_margin - team_implied_margin

    if actual_vs_line > 0:
        result["ats"] = "win"
    elif actual_vs_line < 0:
        result["ats"] = "loss"
    else:
        result["ats"] = "push"

    if line.over_under_open is not None:
        actual_total = game.home_points + game.away_points
        if actual_total > line.over_under_open:
            result["ou"] = "over"
        elif actual_total < line.over_under_open:
            result["ou"] = "under"
        else:
            result["ou"] = "push"

    return result


def refresh_recent_form():
    db = SessionLocal()
    teams = db.query(Team).filter(Team.division == "fbs").all()

    print(f"Refreshing recent-form record for {len(teams)} FBS teams...")

    updated = 0
    for team in teams:
        games = get_last_n_games(team.id, db)
        if not games:
            continue

        ats_wins = ats_losses = ats_pushes = 0
        ou_overs = ou_unders = ou_pushes = 0
        su_wins = su_losses = 0

        for game in games:
            result = grade_game_for_team(game, team.id, db)

            if result["su_win"]:
                su_wins += 1
            else:
                su_losses += 1

            if "ats" in result:
                if result["ats"] == "win":
                    ats_wins += 1
                elif result["ats"] == "loss":
                    ats_losses += 1
                else:
                    ats_pushes += 1

            if "ou" in result:
                if result["ou"] == "over":
                    ou_overs += 1
                elif result["ou"] == "under":
                    ou_unders += 1
                else:
                    ou_pushes += 1

        existing = db.query(TeamRecentForm).filter(TeamRecentForm.team_id == team.id).first()
        fields = dict(
            games_counted=len(games),
            ats_wins=ats_wins, ats_losses=ats_losses, ats_pushes=ats_pushes,
            ou_overs=ou_overs, ou_unders=ou_unders, ou_pushes=ou_pushes,
            su_wins=su_wins, su_losses=su_losses,
            last_updated=datetime.utcnow(),
        )
        if existing:
            for key, value in fields.items():
                setattr(existing, key, value)
        else:
            db.add(TeamRecentForm(team_id=team.id, **fields))
        updated += 1

    db.commit()
    print(f"Updated recent-form record for {updated} teams.")
    db.close()


if __name__ == "__main__":
    refresh_recent_form()