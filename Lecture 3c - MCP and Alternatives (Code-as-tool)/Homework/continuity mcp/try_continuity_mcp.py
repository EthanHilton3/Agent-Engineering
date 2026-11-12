"""Call the Continuity MCP server directly, no LLM: list its tools, then run a few of them.

    python mcp/continuity_mcp.py        # in one terminal
    python mcp/try_continuity_mcp.py    # in another
"""
import asyncio
import json

from fastmcp import Client


def show(label: str, result) -> None:
    print(f'\n== {label}')
    print(json.dumps(result.structured_content, indent=2, default=str)[:1500])


async def main():
    async with Client('http://127.0.0.1:8765/mcp') as client:
        tools = await client.list_tools()
        print('Tools:', ', '.join(t.name for t in tools))

        show('list_goals', await client.call_tool('list_goals', {}))
        show('get_my_history (last 5)', await client.call_tool('get_my_history', {'limit': 5}))

        found = await client.call_tool('search_movies_tv', {'query': 'Severance', 'type': 'tv'})
        show('search_movies_tv Severance', found)
        shows = found.structured_content.get('result') or []
        if shows:
            show('get_next_episodes', await client.call_tool('get_next_episodes', {'show_id': shows[0]['id'], 'count': 2}))


if __name__ == '__main__':
    asyncio.run(main())
