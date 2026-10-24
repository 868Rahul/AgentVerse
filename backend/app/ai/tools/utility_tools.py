"""
Weather and calculator tools.

- Weather uses the free Open-Meteo APIs (no API key): geocoding to turn a place name into coordinates,
  then the forecast API for current conditions and a daily forecast.
- The calculator evaluates math expressions safely by walking the Python AST (no eval), with limits
  that stop huge powers / factorials from freezing the server.
"""

import ast
import logging
import math
import operator
import re

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HTTP_TIMEOUT = httpx.Timeout(10.0)

# WMO weather interpretation codes used by Open-Meteo
WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


async def _geocode(client: httpx.AsyncClient, location: str) -> dict | None:
    # "Paris, France" -> search "Paris", prefer results whose country/region matches "France"
    name, _, hint = location.partition(",")
    response = await client.get(GEOCODING_URL, params={"name": name.strip(), "count": 10, "language": "en"})
    response.raise_for_status()
    results = response.json().get("results") or []
    if not results:
        return None
    hint = hint.strip().lower()
    if hint:
        for place in results:
            if hint in f"{place.get('country', '')} {place.get('country_code', '')} {place.get('admin1', '')}".lower():
                return place
    return results[0]


@tool
async def get_weather(location: str, days: int = 3) -> dict:
    """Get the current weather and a daily forecast for a city or place.
    `location` is a place name, optionally with country, e.g. "Mumbai" or "Paris, France".
    `days` is the number of forecast days (1-7). Temperatures are in °C, wind in km/h."""
    days = max(1, min(int(days), 7))
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            place = await _geocode(client, location)
            if not place:
                return {"error": f"location '{location}' not found, ask the user for a more specific place name"}
            response = await client.get(FORECAST_URL, params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,precipitation",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
                "timezone": "auto",
                "forecast_days": days,
            })
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        logger.error(f"Weather lookup failed: {e}")
        return {"error": "the weather service is currently unavailable, tell the user to try again later"}

    current = data.get("current", {})
    daily = data.get("daily", {})
    return {
        "location": ", ".join(p for p in (place.get("name"), place.get("admin1"), place.get("country")) if p),
        "local_time": current.get("time"),
        "current": {
            "condition": WEATHER_CODES.get(current.get("weather_code"), "Unknown"),
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_kmh": current.get("wind_speed_10m"),
            "precipitation_mm": current.get("precipitation"),
        },
        "forecast": [
            {
                "date": date,
                "condition": WEATHER_CODES.get(code, "Unknown"),
                "min_c": t_min,
                "max_c": t_max,
                "rain_chance_percent": rain_chance,
                "precipitation_mm": rain_sum,
            }
            for date, code, t_min, t_max, rain_chance, rain_sum in zip(
                daily.get("time", []),
                daily.get("weather_code", []),
                daily.get("temperature_2m_min", []),
                daily.get("temperature_2m_max", []),
                daily.get("precipitation_probability_max", []),
                daily.get("precipitation_sum", []),
            )
        ],
        "source": "Open-Meteo",
    }


# ---------------------------------------------------------------- calculator

class CalculatorError(ValueError):
    pass


MAX_EXPONENT = 1000
MAX_FACTORIAL = 500
MAX_ABS_RESULT = 1e300


def _safe_pow(base, exponent):
    if abs(exponent) > MAX_EXPONENT:
        raise CalculatorError(f"exponent larger than {MAX_EXPONENT} is not allowed")
    return operator.pow(base, exponent)


def _safe_factorial(n):
    if n != int(n) or n < 0 or n > MAX_FACTORIAL:
        raise CalculatorError(f"factorial needs a whole number between 0 and {MAX_FACTORIAL}")
    return math.factorial(int(n))


_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: _safe_pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCTIONS = {
    "sqrt": math.sqrt, "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x), "abs": abs, "round": round,
    "floor": math.floor, "ceil": math.ceil, "exp": math.exp,
    "log": math.log, "ln": math.log, "log10": math.log10, "log2": math.log2,
    "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "radians": math.radians, "degrees": math.degrees, "factorial": _safe_factorial,
    "min": min, "max": max, "pow": _safe_pow, "hypot": math.hypot,
}
_CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


def _evaluate(node):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FUNCTIONS
        and not node.keywords
    ):
        return _FUNCTIONS[node.func.id](*[_evaluate(arg) for arg in node.args])
    raise CalculatorError("only numbers, + - * / // % ** ( ) and math functions like sqrt, log, sin are allowed")


def calculate(expression: str) -> int | float:
    """Evaluate a math expression without eval()."""
    text = expression.strip().replace("^", "**").replace("×", "*").replace("÷", "/")
    # drop thousands separators ("1,234") but keep commas between function arguments ("log(100, 10)")
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    if len(text) > 300:
        raise CalculatorError("expression is too long")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError:
        raise CalculatorError("the expression is not valid math")
    result = _evaluate(tree)
    if isinstance(result, float):
        if math.isnan(result) or abs(result) > MAX_ABS_RESULT:
            raise CalculatorError("the result is not a finite number")
        result = round(result, 12)
        if result.is_integer():
            result = int(result)
    return result


@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression exactly. Always use this for arithmetic instead of computing in your head.
    Supports + - * / // % ** (or ^), parentheses, pi, e, and functions: sqrt, cbrt, abs, round, floor, ceil,
    exp, log/ln, log10, log2, sin, cos, tan (radians), asin, acos, atan, radians, degrees, factorial, min, max, hypot.
    Percentages must be written as math, e.g. "17% of 2450" -> "0.17 * 2450"."""
    try:
        return f"{expression} = {calculate(expression)}"
    except ZeroDivisionError:
        return "Error: division by zero"
    except (CalculatorError, ValueError, OverflowError, TypeError) as e:
        return f"Error: {e}"
