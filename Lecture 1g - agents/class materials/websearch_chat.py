import argparse
import sys
from pathlib import Path
from time import time

from openai import OpenAI

from usage import print_usage

WEB_SEARCH_CALL_COST_USD = 0.01


def _as_dict(item):
    '''Convert an SDK response item into a dictionary for inspection/history.'''
    if isinstance(item, dict):
        return item
    if hasattr(item, 'model_dump'):
        return item.model_dump(exclude_none=True)
    return dict(item)


def _print_search_trace(items):
    '''Show the hosted search actions and source metadata returned by Responses.'''
    print('\nSEARCH TRACE', file=sys.stderr)
    print('------------------------', file=sys.stderr)

    for item in items:
        if item.get('type') == 'web_search_call':
            action = item.get('action') or {}
            action_type = action.get('type', 'unknown')
            print(f'action: {action_type}', file=sys.stderr)

            queries = action.get('queries')
            if queries:
                for query in queries:
                    print(f'query: {query}', file=sys.stderr)
            elif action.get('query'):
                query = action['query']
                print(f'query: {query}', file=sys.stderr)

            if action.get('url'):
                url = action['url']
                print(f'url: {url}', file=sys.stderr)

            sources = action.get('sources') or []
            if sources:
                print('consulted sources:', file=sys.stderr)
                for source in sources:
                    title = source.get('title', 'untitled')
                    url = source.get('url', '')
                    print(f'  - {title}: {url}', file=sys.stderr)

    print('\ncitations in answer:', file=sys.stderr)
    seen = set()
    for item in items:
        if item.get('type') != 'message':
            continue
        for content in item.get('content', []):
            for annotation in content.get('annotations', []):
                if annotation.get('type') != 'url_citation':
                    continue
                citation = (
                    annotation.get('title', 'untitled'),
                    annotation.get('url', ''),
                )
                if citation in seen:
                    continue
                seen.add(citation)
                print(f'  - {citation[0]}: {citation[1]}', file=sys.stderr)
    print('------------------------', file=sys.stderr)


def _run_agent_turn(client, model: str, reasoning: str, history: list,
                    search_context_size: str, excluded_domains: list[str]):
    search_tool = {
        'type': 'web_search',
        'search_context_size': search_context_size,
    }
    if excluded_domains:
        search_tool['filters'] = {'blocked_domains': excluded_domains}

    response = client.responses.create(
        model=model,
        input=history,
        reasoning={'effort': reasoning},
        tools=[search_tool],
        tool_choice='required',     # or 'auto'
        include=['web_search_call.action.sources'],
    )

    response_items = [_as_dict(item) for item in response.output]
    _print_search_trace(response_items)
    web_search_calls = sum(
        item.get('type') == 'web_search_call'
        for item in response_items
    )

    if not response.output_text:
        raise RuntimeError('web search returned no final text response')
    return (response.output_text, response_items,
            [(response.model, response.usage)], web_search_calls)


def main(model: str, reasoning: str, prompt: str,
         search_context_size: str, excluded_domains: list[str]):
    client = OpenAI()

    history = [{'role': 'system', 'content': prompt}]
    usage = []
    web_search_calls = 0

    print('Enter a news item to investigate. Press Enter on an empty line to quit.')
    while True:
        usr_message = input('\nUSER: ')
        if not usr_message:
            break

        history.append({'role': 'user', 'content': usr_message})

        start = time()
        output_text, response_items, turn_usage, turn_search_calls = _run_agent_turn(
            client,
            model,
            reasoning,
            history,
            search_context_size,
            excluded_domains,
        )
        history += response_items
        usage += turn_usage
        web_search_calls += turn_search_calls
        print(f'{round(time() - start, 2)} seconds elapsed', file=sys.stderr)
        print('AGENT: ', output_text)

    print_usage(usage)
    print(f'Web search calls: {web_search_calls}', file=sys.stderr)
    print(
        f'Web search cost (USD): ${web_search_calls * WEB_SEARCH_CALL_COST_USD:.6f}',
        file=sys.stderr,
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Web-search news investigator')
    parser.add_argument('prompt_file', type=Path)
    parser.add_argument(
        '--excluded-domains',
        type=Path,
        default=Path(__file__).with_name('excluded_domains.txt'),
    )
    parser.add_argument('--model', default='gpt-5.6-luna')
    parser.add_argument('--reasoning', default='none')
    parser.add_argument(
        '--search-context-size',
        choices=('low', 'medium', 'high'),
        default='high',
        help='How much search context to provide to the model.',
    )
    args = parser.parse_args()

    excluded_domains = [
        line.strip()
        for line in args.excluded_domains.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    ]

    main(args.model, args.reasoning, args.prompt_file.read_text(),
         args.search_context_size, excluded_domains)
