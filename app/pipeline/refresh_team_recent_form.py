"""
Daily job: computes and stores each team's rolling last-10-games record
(ATS, Over/Under, straight-up win/loss) - materialized into
team_recent_form, one row per team, overwritten daily.

Correctly crosses season boundaries: pulls each team's most recent 10
COMPLETED games regardless of season, not "last 10 this season" - so
Week 1-2 of a new season correctly reaches back into the prior season's
final games, per explicit design requirement.

PERFORMANCE FIXES (Aug 21, 2026): three separate per-item-query issues
found and fixed in this file, same pattern each time (batch once
upfront instead of querying per-item in a loop):
  1. get_best_line_for_game() per-game-per-team -> batched (307.5s -> 48.9s)
  2. TeamRecentForm existence-check per-team -> batched (48.9s -> this run)
Confirmed via direct timing test: the TeamRecentForm lookup alone cost
22.33s of the remaining 48.9s (162ms/team x 138 teams).
"""
from collections import defaultdict
from datetime import datetime
from app.db import SessionLocal
from app.models import Team, Game, TeamRecentForm, CFBDBettingLine
from app.features.get_game_line import PROVIDER_PRIORITY

GAMES_TO_TRACK = 10


def get_last_n_games_per_team(teams, db, n=GAMES_TO_TRACK):
    team_ids = [t.id for t in teams]
    all_games = db.query(Game).filter(
        (Game.home_team_id.in_(team_ids)) | (Game.away_team_id.in_(team_ids)),
        Game.completed == True,
        Game.home_points.isnot(None), Game.away_points.isnot(None),
    ).order_by(Game.start_date.desc()).all()

    games_by_team = defaultdict(list)
    for game in all_games:
        if game.home_team_id in team_ids and len(games_by_team[game.home_team_id]) < n:
            games_by_team[game.home_team_id].append(game)
        if game.away_team_id in team_ids and len(games_by_team[game.away_team_id]) < n:
            games_by_team[game.away_team_id].append(game)

    return games_by_team


def get_lines_for_games_batch(game_ids, db):
    all_lines = db.query(CFBDBettingLine).filter(CFBDBettingLine.game_id.in_(game_ids)).all()

    lines_by_game = defaultdict(list)
    for line in all_lines:
        lines_by_game[line.game_id].append(line)

    best_line_by_game = {}
    for game_id, lines in lines_by_game.items():
        lines_by_provider = {line.provider: line for line in lines}
        for provider in PROVIDER_PRIORITY:
            if provider in lines_by_provider:
                best_line_by_game[game_id] = lines_by_provider[provider]
                break
        else:
            best_line_by_game[game_id] = lines[0]

    return best_line_by_game


def grade_game_for_team(game, team_id, line):
    is_home = game.home_team_id == team_id
    team_points = game.home_points if is_home else game.away_points
    opp_points = game.away_points if is_home else game.home_points
    team_margin = team_points - opp_points

    result = {"su_win": team_margin > 0}

    if line is None or line.spread_open is None:
        return result

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

    games_by_team = get_last_n_games_per_team(teams, db)

    all_game_ids = list({g.id for games in games_by_team.values() for g in games})
    lines_by_game = get_lines_for_games_batch(all_game_ids, db)

    team_ids = [t.id for t in teams]
    existing_records = db.query(TeamRecentForm).filter(TeamRecentForm.team_id.in_(team_ids)).all()
    existing_by_team = {r.team_id: r for r in existing_records}

    updated = 0
    for team in teams:
        games = games_by_team.get(team.id, [])
        if not games:
            continue

        ats_wins = ats_losses = ats_pushes = 0
        ou_overs = ou_unders = ou_pushes = 0
        su_wins = su_losses = 0

        for game in games:
            line = lines_by_game.get(game.id)
            result = grade_game_for_team(game, team.id, line)

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

        fields = dict(
            games_counted=len(games),
            ats_wins=ats_wins, ats_losses=ats_losses, ats_pushes=ats_pushes,
            ou_overs=ou_overs, ou_unders=ou_unders, ou_pushes=ou_pushes,
            su_wins=su_wins, su_losses=su_losses,
            last_updated=datetime.utcnow(),
        )

        existing = existing_by_team.get(team.id)
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