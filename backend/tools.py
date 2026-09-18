"""
All tools the chat model can call.
"""
import requests
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

from backend.config import WEATHER_API_KEY, ALPHA_VANTAGE_API_KEY

search_tool = DuckDuckGoSearchRun(region="us-en")


@tool
def calculate(n1: str, n2: str, operation: str) -> dict:
    """
    Perform a basic mathematical calculation.
    Supported operations: add, sub, mul, div
    """
    try:
        n1 = float(n1)
        n2 = float(n2)
        if operation == "add":
            res = n1 + n2
        elif operation == "sub":
            res = n1 - n2
        elif operation == "mul":
            res = n1 * n2
        elif operation == "div":
            if n2 == 0:
                return {"error": "Division by zero is not possible"}
            res = n1 / n2
        else:
            return {"error": f"Unsupported operation: {operation}"}
        return {"first_number": n1, "second_number": n2, "operation": operation, "result": res}
    except Exception as e:
        return {"error": str(e)}


@tool
def get_weather(place: str) -> dict:
    """Returns current weather and climate conditions for a given place."""
    if not WEATHER_API_KEY:
        return {"error": "WEATHER_API_KEY is not configured on the server."}
    try:
        response = requests.get(
            "http://api.weatherapi.com/v1/current.json",
            params={"key": WEATHER_API_KEY, "q": place},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}


@tool
def get_stock_price(symbol: str) -> dict:
    """Returns the latest stock price quote for a given ticker symbol."""
    if not ALPHA_VANTAGE_API_KEY:
        return {"error": "ALPHA_VANTAGE_API_KEY is not configured on the server."}
    try:
        response = requests.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": ALPHA_VANTAGE_API_KEY,
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}


TOOLS = [get_weather, get_stock_price, search_tool, calculate]
