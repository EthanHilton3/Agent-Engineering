from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-5.6-luna",
    input="Write a commandline agent tool like codex. In python, using `openai`. Return just the python code, nothing else.",
)

print(response.output_text)