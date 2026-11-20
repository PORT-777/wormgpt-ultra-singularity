from typing import Any, Dict, List, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class FinancialIntelligencePlugin(BasePlugin):
    manifest = PluginManifest(
        id="finance",
        name="Finance Intelligence",
        description="Real-time exchange rates, stock quotes and crypto prices",
        long_description=(
            "Financial data intelligence: get current exchange rates for fiat "
            "currencies, fetch live stock prices for equities, and track real-time "
            "cryptocurrency market data."
        ),
        version="1.0.0",
        author="outcome",
        icon="💰",
        category="finance",
        tags=["finance", "stocks", "crypto", "forex", "market"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="finance.getForex",
                display_name="Exchange Rates",
                description="Convert between fiat currencies (e.g. USD to EUR)",
                parameters={
                    "from_currency": {"type": "string", "description": "e.g. USD"},
                    "to_currency": {"type": "string", "description": "e.g. EUR"},
                },
            ),
            PluginTool(
                name="finance.getStocks",
                display_name="Stock Quotes",
                description="Get real-time stock price and volume (e.g. AAPL, TSLA)",
                parameters={"symbol": {"type": "string"}},
            ),
            PluginTool(
                name="finance.getCrypto",
                display_name="Crypto Prices",
                description="Get current price and market cap for a cryptocurrency (e.g. BTC, ETH)",
                parameters={"symbol": {"type": "string", "description": "e.g. BTC"}},
            ),
        ],
        website_url="https://www.alphavantage.co",
        docs_url="https://www.alphavantage.co/documentation/",
        is_free=False,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.credentials['api_key']}"}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        # Note: Using AlphaVantage as an example implementation
        api_key = self.credentials["api_key"]
        base_url = "https://www.alphavantage.co/query"

        async with httpx.AsyncClient(timeout=30.0) as client:
            if tool_name == "finance.getForex":
                params = {
                    "function": "CURRENCY_EXCHANGE_RATE",
                    "from_currency": parameters["from_currency"],
                    "to_currency": parameters["to_currency"],
                    "apikey": api_key,
                }
                resp = await client.get(base_url, params=params)
                data = resp.json()
                rate_info = data.get("Realtime Currency Exchange Rate", {})
                return {
                    "from": rate_info.get("1. From_Currency"),
"to": rate_info.get("3. To_Currency"),
                    "rate": rate_info.get("5. Exchange Rate"),
                    "last_updated": rate_info.get("6. Last Refreshed"),
                }

            if tool_name == "finance.getStocks":
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": parameters["symbol"],
                    "apikey": api_key,
                }
                resp = await client.get(base_url, params=params)
                data = resp.json()
                quote = data.get("Global Quote", {})
                return {
                    "symbol": quote.get("01. symbol"),
                    "price": quote.get("05. price"),
                    "change_percent": quote.get("10. change percent"),
                    "volume": quote.get("06. volume"),
                }

            if tool_name == "finance.getCrypto":
                params = {
                    "function": "CURRENCY_EXCHANGE_RATE",
                    "from_currency": parameters["symbol"],
                    "to_currency": "USD",
                    "apikey": api_key,
                }
                resp = await client.get(base_url, params=params)
                data = resp.json()
                rate_info = data.get("Realtime Currency Exchange Rate", {})
                return {
                    "symbol": parameters["symbol"],
                    "price_usd": rate_info.get("5. Exchange Rate"),
                    "last_updated": rate_info.get("6. Last Refreshed"),
                }

            raise ValueError(f"Unknown finance tool: {tool_name}")
