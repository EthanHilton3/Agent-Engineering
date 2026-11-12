"""Continuity as an MCP server: the Lorekeeper's read tools, usable from any MCP client (Claude Code, mcpbot, ...).

Read-only on purpose. There are no write tools, so an outside agent can look at the lore but can't change it.
Logging still goes through the app, where every write is a proposal the user confirms.

Signs in as the demo user (.demo-user.json), so Row Level Security applies exactly as it does in the app.
The model never supplies a user ID.

    python mcp/continuity_mcp.py          # serves http://127.0.0.1:8765/mcp
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.agent import DbHistory, Toolbox  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import user_db  # noqa: E402
from app.goals import GoalStore  # noqa: E402
from app.planner import PlannerStore  # noqa: E402

TZ = 'America/Denver'
mcp = FastMCP('Continuity', instructions=(
    "Continuity is the user's personal media journal: the movies, TV shows and books they've watched or read, "
    "their watch goals and deadlines, and what episode they're on. Use these tools for any question about the user's "
    "shows, movies, books, watch history, goals or viewing schedule. The tools are read-only."
))

_session: dict = {}  # access token, user id and when it was issued


async def _sign_in(http: httpx.AsyncClient) -> tuple[str, str]:
    """The demo user's token, refreshed before Supabase's one-hour expiry."""
    if _session and time.time() - _session['at'] < 50 * 60:
        return _session['token'], _session['user_id']
    creds = json.loads((ROOT / '.demo-user.json').read_text(encoding='utf-8'))
    s = get_settings()
    resp = await http.post(f'{s.supabase_auth_url}/token', params={'grant_type': 'password'},
                           headers={'apikey': s.supabase_anon_key.get_secret_value()},
                           json={'email': creds['email'], 'password': creds['password']})
    resp.raise_for_status()
    body = resp.json()
    _session.update(token=body['access_token'], user_id=body['user']['id'], at=time.time())
    return _session['token'], _session['user_id']


async def _call(tool: str, **kwargs):
    """Build a fresh Toolbox the same way the Lorekeeper does, and run one of its read tools."""
    async with httpx.AsyncClient(timeout=30) as http:
        token, user_id = await _sign_in(http)
        db = user_db(http, token)
        today = datetime.now(ZoneInfo(TZ)).date()
        toolbox = Toolbox(http, DbHistory(db, user_id), today, GoalStore(db, user_id, today, http),
                          PlannerStore(db, user_id, today, TZ), TZ)
        return await getattr(toolbox, tool)(**kwargs)


@mcp.tool
async def search_movies_tv(query: str, type: str, year: int | None = None) -> list[dict]:
    """Search TMDB for a movie or TV show. type is 'movie' or 'tv'. Returns the top matches with ids like
    'tmdb:tv:95396', and flags whether each is already in the user's history. Use the id with the other tools."""
    return await _call('search_movies_tv', query=query, type=type, year=year)


@mcp.tool
async def get_my_history(media_id: str | None = None, since: str | None = None, until: str | None = None,
                         limit: int = 10) -> dict:
    """The user's logged experiences (what they watched or read), newest first. Optionally filter by a media id
    from search_movies_tv, and by dates (YYYY-MM-DD). limit is at most 20."""
    return await _call('get_my_history', media_id=media_id, since=since, until=until, limit=limit)


@mcp.tool
async def get_next_episodes(show_id: str, count: int | None = None) -> dict:
    """The next unwatched episodes of a TV show after the last one the user logged. show_id is a 'tmdb:tv:...' id."""
    return await _call('get_next_episodes', show_id=show_id, count=count)


@mcp.tool
async def list_goals(status: str | None = None) -> dict:
    """The user's goals with id, name, status, deadline and percent done. Optionally filter by status."""
    return await _call('list_goals', status=status)


@mcp.tool
async def get_goal_progress(goal_id: str) -> dict:
    """Detailed progress on one goal (use an id from list_goals): done, remaining, runtime left, days left,
    the weekly pace needed vs. the recent pace, and the next item."""
    return await _call('get_goal_progress', goal_id=goal_id)


@mcp.tool
async def get_viewing_patterns(media_type: str | None = None) -> dict:
    """When and how much the user usually watches: usual weekdays, items per sitting, recent pace.
    media_type is 'movie', 'tv' or omitted for both."""
    return await _call('get_viewing_patterns', media_type=media_type)


if __name__ == '__main__':
    mcp.run(transport='http', host='127.0.0.1', port=8765)
