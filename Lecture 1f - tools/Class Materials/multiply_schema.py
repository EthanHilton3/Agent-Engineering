{
  "type": "function",
  "name": "multiply",
  "description": "Multiply two numbers together. Use this tool for **all** multiplication tasks.",
  "strict": True,
  "parameters": {
    "type": "object",
    "properties": {
      "num1": {
        "type": "number",
        "description": "First operand"
      },
      "num2": {
        "type": "number",
        "description": "Second operand"
      }
    },
    "required": [
      "num1",
      "num2"
    ],
    "additionalProperties": False
  }
}