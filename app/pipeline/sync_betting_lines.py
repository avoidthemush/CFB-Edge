import os
import cfbd
import httpx
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import CFBDBettingLine, OddsSnapshot, Game, TeamSourceAlias
from app.pipeline.api_usage import ApiUsageTracker
from app.config import CURRENT_SEASON, HISTORICAL_START_YEAR

load_dotenv()
CFBD_API_KEY = os.getenv("CFBD_API_KEY")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

SPORT_KEY = "americanfootball_ncaaf"
BOOKMAKERS = "draftkings,fanduel"  # scope decision: only these two books, project-wide


# ============================================================
# CFBD historical lines - one-time backfill + annual top-up
# ============================================================

def sync_cfbd_lines_for_year(year: int, tracker: ApiUsageTracker):
    """
    Pulls CFBD's own aggregated betting lines for a season. Game IDs here
    are the same CFBD game IDs already in our games table - no crosswalk
    needed, just a direct match.
    """
    configuration = cfbd.Configuration(access_token=CFBD_API_KEY)
    db = SessionLocal()

    inserted = 0
    updated = 0
    skipped_no_game = 0

    try:
        with cfbd.ApiClient(configuration) as api_client:
            api_instance = cfbd.BettingApi(api_client)
            games_with_lines = api_instance.get_lines(year=year)
            tracker.tick()

            for g in games_with_lines:
                game_id = getattr(g, "id", None)
                if game_id is None:
                    continue

                game_exists = db.query(Game.id).filter(Game.id == game_id).first()
                if not game_exists:
                    skipped_no_game += 1
                    continue

                lines = getattr(g, "lines", None) or []

                PROVIDER_ALIASES = {
                    "Draft Kings": "DraftKings",
                }

                # ... inside sync_cfbd_lines_for_year(), right after getting provider:
                for line in lines:
                    provider = getattr(line, "provider", None)
                    provider = PROVIDER_ALIASES.get(provider, provider)

                    existing = db.query(CFBDBettingLine).filter(
                        CFBDBettingLine.game_id == game_id,
                        CFBDBettingLine.provider == provider,
                    ).first()

                    fields = dict(
                        spread=getattr(line, "spread", None),
                        spread_open=getattr(line, "spread_open", None),
                        over_under=getattr(line, "over_under", None),
                        over_under_open=getattr(line, "over_under_open", None),
                        home_moneyline=getattr(line, "home_moneyline", None),
                        away_moneyline=getattr(line, "away_moneyline", None),
                    )

                    if existing:
                        for key, value in fields.items():
                            setattr(existing, key, value)
                        updated += 1
                    else:
                        db.add(CFBDBettingLine(game_id=game_id, provider=provider, **fields))
                        inserted += 1

            db.commit()
            print(
                f"  Year {year}: inserted {inserted}, updated {updated} lines "
                f"(skipped {skipped_no_game} lines with no matching game)"
            )

    except Exception as e:
        db.rollback()
        print(f"  Year {year} FAILED: {e}")
        raise
    finally:
        db.close()


def backfill_cfbd_lines(start_year: int = HISTORICAL_START_YEAR, end_year: int = CURRENT_SEASON):
    tracker = ApiUsageTracker("backfill_cfbd_lines")
    print(f"Backfilling CFBD betting lines from {start_year} to {end_year}...")
    for year in range(start_year, end_year + 1):
        sync_cfbd_lines_for_year(year, tracker)
    tracker.report()


# ============================================================
# The Odds API live lines - DraftKings/FanDuel only
# ============================================================

def _load_odds_team_lookup(db):
    """Maps an Odds API team name string directly to a CFBD team_id."""
    aliases = db.query(TeamSourceAlias).filter(
        TeamSourceAlias.source == "odds_api",
        TeamSourceAlias.team_id.isnot(None),
    ).all()
    return {a.source_name: a.team_id for a in aliases}


def _find_game(db, season, home_team_id, away_team_id):
    """
    Odds API's home/away convention should match CFBD's, but fall back to
    a flipped lookup in case of a neutral-site labeling mismatch.
    """
    game = db.query(Game).filter(
        Game.season == season,
        Game.home_team_id == home_team_id,
        Game.away_team_id == away_team_id,
    ).first()
    if game:
        return game

    return db.query(Game).filter(
        Game.season == season,
        Game.home_team_id == away_team_id,
        Game.away_team_id == home_team_id,
    ).first()


def _extract_market(bookmaker, market_key):
    for market in bookmaker.get("markets", []):
        if market.get("key") == market_key:
            return market.get("outcomes", [])
    return []


def sync_live_odds(season: int = CURRENT_SEASON):
    """
    Pulls current odds from The Odds API for DraftKings and FanDuel only.
    Writes one OddsSnapshot row per (game, sportsbook) per run - designed
    to be run repeatedly during the season to track line movement over
    time, not just once.
    """
    db = SessionLocal()

    team_lookup = _load_odds_team_lookup(db)

    url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "bookmakers": BOOKMAKERS,
        "oddsFormat": "american",
    }
    resp = httpx.get(url, params=params, timeout=20)
    resp.raise_for_status()
    events = resp.json()

    remaining = resp.headers.get("x-requests-remaining")
    print(f"Pulled {len(events)} events with odds. Quota remaining: {remaining}")

    inserted = 0
    unmatched_team = 0
    unmatched_game = 0

    for event in events:
        home_name = event.get("home_team")
        away_name = event.get("away_team")

        home_team_id = team_lookup.get(home_name)
        away_team_id = team_lookup.get(away_name)

        if home_team_id is None or away_team_id is None:
            unmatched_team += 1
            print(f"  Unmatched team name(s): '{home_name}' / '{away_name}'")
            continue

        game = _find_game(db, season, home_team_id, away_team_id)
        if game is None:
            unmatched_game += 1
            print(f"  No matching game found for {away_name} @ {home_name} ({season})")
            continue

        for bookmaker in event.get("bookmakers", []):
            book_key = bookmaker.get("key")

            h2h = _extract_market(bookmaker, "h2h")
            spreads = _extract_market(bookmaker, "spreads")
            totals = _extract_market(bookmaker, "totals")

            home_ml = next((o["price"] for o in h2h if o.get("name") == home_name), None)
            away_ml = next((o["price"] for o in h2h if o.get("name") == away_name), None)

            spread_home = next((o["point"] for o in spreads if o.get("name") == home_name), None)
            spread_home_price = next((o["price"] for o in spreads if o.get("name") == home_name), None)
            spread_away_price = next((o["price"] for o in spreads if o.get("name") == away_name), None)

            total_point = next((o["point"] for o in totals if o.get("name") == "Over"), None)
            over_price = next((o["price"] for o in totals if o.get("name") == "Over"), None)
            under_price = next((o["price"] for o in totals if o.get("name") == "Under"), None)

            db.add(OddsSnapshot(
                game_id=game.id,
                sportsbook=book_key,
                spread_home=spread_home,
                spread_home_price=spread_home_price,
                spread_away_price=spread_away_price,
                total=total_point,
                over_price=over_price,
                under_price=under_price,
                moneyline_home=home_ml,
                moneyline_away=away_ml,
                is_closing_line=False,
            ))
            inserted += 1

    db.commit()
    db.close()

    print(
        f"\nOdds snapshot complete: inserted {inserted} rows "
        f"(unmatched teams: {unmatched_team}, unmatched games: {unmatched_game})"
    )


if __name__ == "__main__":
    backfill_cfbd_lines()