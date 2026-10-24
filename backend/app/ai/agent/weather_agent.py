from datetime import datetime

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from ai.guardrails import GUARDRAIL_RULES, trim_history
from ai.llm import get_model, settings
from ai.tools.utility_tools import calculator, get_weather

WEATHER_CALCULATOR_PROMPT = """
You are a friendly weather and calculation assistant.

What you can do (tell the user this when they greet you or ask what you can do):
1. Current weather and up to a 7-day forecast for any city or place in the world.
2. Exact calculations: arithmetic, percentages, powers, roots, logarithms, trigonometry, unit-style conversions.

How to answer:
- For any weather question call `get_weather`. If the user gives no place, ask for one. If several places share a name,
  include the country, e.g. "Paris, France".
- Report temperatures in °C (add °F in brackets when the user asks for it), mention feels-like temperature,
  humidity, wind and chance of rain when relevant. Say the data is from Open-Meteo.
- For ANY arithmetic call `calculator`, even simple sums; never compute in your head. Show the expression you evaluated
  and the result. For percentages write them as math, e.g. 17% of 2450 -> 0.17 * 2450.
- Never invent weather data. If a tool returns an error, explain it briefly.
- Keep answers short and formatted in Markdown.
""" + GUARDRAIL_RULES


def _prompt(state):
    """System prompt with the current date (needed for "tomorrow" / "this weekend") and trimmed history."""
    system = WEATHER_CALCULATOR_PROMPT + f"\nToday is {datetime.now():%A, %Y-%m-%d}."
    return [{"role": "system", "content": system}, *trim_history(state["messages"])]


weather_calculator_agent = create_react_agent(
    model=get_model(settings.DEFAULT_MODEL),
    tools=[get_weather, calculator],
    prompt=_prompt,
    name="weather_calculator",
    checkpointer=InMemorySaver(),
)
