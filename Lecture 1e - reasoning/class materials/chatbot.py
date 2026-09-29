# Before running this script:
# pip install gradio openai

import argparse
import asyncio
from pathlib import Path

import gradio as gr
from openai import AsyncOpenAI

from usage import print_usage, format_usage_markdown


class ChatAgent:
    def __init__(self, model: str, prompt: str, show_reasoning: bool, reasoning_effort: str | None):
        self._ai = AsyncOpenAI()
        self.model = model
        self.show_reasoning = show_reasoning
        self.reasoning = {}
        if show_reasoning:
            self.reasoning['summary'] = 'auto'
        if 'gpt-5' in self.model and reasoning_effort:
            self.reasoning['effort'] = reasoning_effort

        self.usage = []
        self.usage_markdown = format_usage_markdown(self.model, [])

        self._history = []
        self._prompt = prompt
        if prompt:
            self._history.append({'role': 'system', 'content': prompt})

    async def get_response(self, user_message: str):
        self._history.append({'role': 'user', 'content': user_message})

        stream = self._ai.responses.stream(
            input=self._history,
            model=self.model,
            reasoning=self.reasoning,
        )
        reasoning_summary = ""
        async with stream as stream:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    yield 'output', event.delta

                if event.type == "response.reasoning_summary_text.delta":
                    reasoning_summary += event.delta
                    yield 'reasoning', event.delta

            response = await stream.get_final_response()
            self.usage.append(response.usage)
            self.usage_markdown = format_usage_markdown(self.model, self.usage)

            if self.show_reasoning and not reasoning_summary:
                final_summary = "\n\n".join(
                    summary.text
                    for item in response.output
                    if item.type == 'reasoning'
                    for summary in item.summary
                )
                yield (
                    'reasoning',
                    final_summary or '*No reasoning summary was returned by the model.*',
                )

            self._history.extend(
                response.output
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print_usage([(self.model, usage) for usage in self.usage])


async def _main_console(agent_args):
    with ChatAgent(**agent_args) as agent:
        while True:
            message = input('User: ')
            if not message:
                break

            reasoning_complete = True
            if agent.show_reasoning:
                print(' Reasoning '.center(30, '-'))
                reasoning_complete = False

            async for text_type, text in agent.get_response(message):
                if text_type == 'output' and not reasoning_complete:
                    print()
                    print('-' * 30)
                    print()
                    print('Agent: ')
                    reasoning_complete = True

                print(text, end='', flush=True)
            print()
            print()


def _main_gradio(agent_args):
    # Constrain width with CSS and center
    css = """
    /* limit overall Gradio app width and center it */
    .gradio-container, .gradio-app, .gradio-root {
      width: 120ch;
      max-width: 120ch !important;
      margin-left: auto !important;
      margin-right: auto !important;
      box-sizing: border-box !important;
    }
    
    #reasoning-md {
        max-height: 300px;
        overflow-y: auto;
    }
    """

    with ChatAgent(**agent_args) as chat_agent:
        reasoning_view = gr.Markdown('', elem_id='reasoning-md')
        usage_view = gr.Markdown(chat_agent.usage_markdown)

        with gr.Blocks() as demo:

            async def get_response(message, chat_view_history):
                output = ""
                reasoning = ""

                async for text_type, text in chat_agent.get_response(message):
                    if text_type == 'reasoning':
                        reasoning += text
                    elif text_type == 'output':
                        output += text
                    else:
                        raise NotImplementedError(text_type)

                    yield output, reasoning, chat_agent.usage_markdown

                yield output, reasoning, chat_agent.usage_markdown

            with gr.Row():
                with gr.Column(scale=5):
                    bot = gr.Chatbot(
                        label=' ',
                        height=600,
                        resizable=True,
                    )
                    message_box = gr.Textbox(
                        autofocus=True,
                        elem_id='chat-input',
                    )
                    chat = gr.ChatInterface(
                        chatbot=bot,
                        textbox=message_box,
                        fn=get_response,
                        additional_outputs=[reasoning_view, usage_view]
                    )
                    message_box.submit(
                        fn=None,
                        queue=False,
                        js="""
                        () => {
                            const focus_input = () => {
                                const input = document.querySelector(
                                    '#chat-input textarea, #chat-input input'
                                );
                                if (
                                    input &&
                                    !input.disabled &&
                                    input.getAttribute('aria-disabled') !== 'true'
                                ) {
                                    input.focus();
                                    return true;
                                }
                                return false;
                            };

                            let attempts = 0;
                            const refocus = setInterval(() => {
                                if (focus_input() || ++attempts >= 200) {
                                    clearInterval(refocus);
                                }
                            }, 100);
                        }
                        """,
                    )

                with gr.Column(scale=1):
                    reasoning_view.render()
                    usage_view.render()

        demo.launch(css=css, theme=gr.themes.Monochrome())


def main(prompt_path: Path, model: str, show_reasoning, reasoning_effort: str | None, use_web: bool):
    agent_args = dict(
        model=model,
        prompt=prompt_path.read_text() if prompt_path else '',
        show_reasoning=show_reasoning,
        reasoning_effort=reasoning_effort

    )

    if use_web:
        _main_gradio(agent_args)
    else:
        asyncio.run(_main_console(agent_args))


# Launch app
if __name__ == "__main__":
    parser = argparse.ArgumentParser('ChatBot')
    parser.add_argument('prompt_file', nargs='?', type=Path, default=None)
    parser.add_argument('--web', action='store_true')
    parser.add_argument('--model', default='gpt-5.6-luna')
    parser.add_argument('--show-reasoning', action='store_true')
    parser.add_argument('--reasoning-effort', default='none')
    args = parser.parse_args()
    main(args.prompt_file, args.model, args.show_reasoning, args.reasoning_effort, args.web)
