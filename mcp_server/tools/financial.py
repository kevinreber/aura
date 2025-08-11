"""Financial data tool for stocks and cryptocurrency."""

import asyncio
import datetime as dt
from typing import Dict, Any, List
import random
from loguru import logger

from ..schemas.financial import FinancialInput, FinancialOutput, FinancialItem, PortfolioSummary
from ..utils.http_client import HTTPClient
from ..utils.logging import get_logger, log_tool_call
from ..config import get_settings

logger = get_logger("financial_tool")


class FinancialTool:
    """Tool for getting financial data for stocks and cryptocurrencies."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def get_financial_data(self, input_data: FinancialInput) -> FinancialOutput:
        """
        Get financial data for stocks and cryptocurrencies.
        
        Uses Alpha Vantage for stocks and CoinGecko for crypto (both free).
        """
        import asyncio
        start_time = asyncio.get_event_loop().time()
        # Check if we have API keys for real data
        has_alpha_vantage = bool(self.settings.alpha_vantage_api_key)
        
        if not has_alpha_vantage:
            logger.info("No Alpha Vantage API key found, using mock financial data")
            result = await self._generate_mock_financial_data(input_data)
            
            # Log the successful tool call
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("financial.get_data", input_data.dict(), duration_ms)
            
            return result
        
        try:
            # Separate stocks and crypto symbols
            stock_symbols = []
            crypto_symbols = []
            
            # Common crypto symbols that should be treated as crypto
            crypto_list = ['BTC', 'ETH', 'ADA', 'SOL', 'DOGE', 'LTC', 'XRP', 'DOT', 'LINK', 'UNI']
            
            for symbol in input_data.symbols:
                if symbol.upper() in crypto_list or input_data.data_type == "crypto":
                    crypto_symbols.append(symbol.upper())
                else:
                    stock_symbols.append(symbol.upper())
            
            # Fetch data concurrently
            tasks = []
            if stock_symbols:
                tasks.append(self._fetch_stock_data(stock_symbols, self.settings.alpha_vantage_api_key))
            if crypto_symbols:
                tasks.append(self._fetch_crypto_data(crypto_symbols))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            all_financial_items = []
            for result in results:
                if isinstance(result, list):
                    all_financial_items.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error fetching financial data: {result}")
            
            # If no real data, fall back to mock
            if not all_financial_items:
                result = await self._generate_mock_financial_data(input_data)
                
                # Log the successful tool call
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                log_tool_call("financial.get_data", input_data.dict(), duration_ms)
                
                return result
            
            # Determine market status
            market_status = self._get_market_status(all_financial_items)
            
            # Create summary
            summary = self._create_financial_summary(all_financial_items)
            
            result = FinancialOutput(
                request_time=dt.datetime.now().isoformat(),
                total_items=len(all_financial_items),
                market_status=market_status,
                data=all_financial_items,
                summary=summary
            )
            
            # Log the successful tool call
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("financial.get_data", input_data.dict(), duration_ms)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in get_financial_data: {e}")
            result = await self._generate_mock_financial_data(input_data)
            
            # Log the tool call (with error)
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            log_tool_call("financial.get_data", input_data.dict(), duration_ms)
            
            return result

    async def _fetch_stock_data(self, symbols: List[str], api_key: str) -> List[FinancialItem]:
        """Fetch stock data from Alpha Vantage."""
        financial_items = []
        
        # Alpha Vantage requires individual calls for each symbol using GLOBAL_QUOTE
        try:
            # Make individual calls for each symbol
            for symbol in symbols:
                url = f"https://www.alphavantage.co/query"
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": api_key
                }
                
                async with HTTPClient() as client:
                    response = await client.get(url, params=params)
                data = response.json()
                
                if "Global Quote" in data:
                    quote = data["Global Quote"]
                    symbol_name = quote.get("01. symbol", symbol)
                    price = float(quote.get("05. price", 0))
                    change = float(quote.get("09. change", 0))
                    change_percent_str = quote.get("10. change percent", "0%").replace("%", "")
                    change_percent = float(change_percent_str)
                    
                    financial_items.append(FinancialItem(
                        symbol=symbol_name,
                        name=self._get_company_name(symbol_name),
                        price=price,
                        change=change,
                        change_percent=change_percent,
                        currency="USD",
                        data_type="stocks",
                        last_updated=dt.datetime.now().isoformat()
                    ))
                else:
                    logger.warning(f"No quote data found for {symbol}: {data}")
                
                # Add small delay to respect API rate limits
                await asyncio.sleep(0.1)
            
            return financial_items
            
        except Exception as e:
            logger.error(f"Error fetching stock data: {e}")
            return []

    async def _fetch_crypto_data(self, symbols: List[str]) -> List[FinancialItem]:
        """Fetch crypto data from CoinGecko (free API)."""
        financial_items = []
        
        try:
            # Convert symbols to CoinGecko IDs
            crypto_ids = {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "ADA": "cardano",
                "SOL": "solana",
                "DOGE": "dogecoin",
                "LTC": "litecoin",
                "XRP": "ripple",
                "DOT": "polkadot",
                "LINK": "chainlink",
                "UNI": "uniswap"
            }
            
            ids_list = [crypto_ids.get(symbol, symbol.lower()) for symbol in symbols]
            ids_str = ",".join(ids_list)
            
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": ids_str,
                "vs_currencies": "usd",
                "include_24hr_change": "true"
            }
            
            async with HTTPClient() as client:
                response = await client.get(url, params=params)
            data = response.json()
            
            for symbol in symbols:
                crypto_id = crypto_ids.get(symbol, symbol.lower())
                if crypto_id in data:
                    crypto_data = data[crypto_id]
                    price = crypto_data.get("usd", 0)
                    change_percent = crypto_data.get("usd_24h_change", 0)
                    change = (price * change_percent) / 100
                    
                    financial_items.append(FinancialItem(
                        symbol=symbol,
                        name=self._get_crypto_name(symbol),
                        price=price,
                        change=change,
                        change_percent=change_percent,
                        currency="USD",
                        data_type="crypto",
                        last_updated=dt.datetime.now().isoformat()
                    ))
            
            return financial_items
            
        except Exception as e:
            logger.error(f"Error fetching crypto data: {e}")
            return []

    async def _generate_mock_financial_data(self, input_data: FinancialInput) -> FinancialOutput:
        """Generate mock financial data for testing."""
        mock_data = []
        
        # Mock data for the requested symbols
        for symbol in input_data.symbols:
            # Determine if it's crypto or stock
            crypto_symbols = ['BTC', 'ETH', 'ADA', 'SOL', 'DOGE', 'LTC', 'XRP']
            is_crypto = symbol.upper() in crypto_symbols
            
            if is_crypto:
                # Crypto prices and changes
                base_prices = {
                    'BTC': 45000, 'ETH': 2800, 'ADA': 0.45, 'SOL': 95,
                    'DOGE': 0.08, 'LTC': 85, 'XRP': 0.55
                }
                base_price = base_prices.get(symbol.upper(), 100)
                change_percent = random.uniform(-8, 8)  # Crypto is more volatile
            else:
                # Stock prices and changes
                base_prices = {
                    'MSFT': 415, 'NVDA': 875, 'GOOGL': 175, 'SMR': 45, 'VOO': 450
                }
                base_price = base_prices.get(symbol.upper(), 150)
                change_percent = random.uniform(-3, 3)  # Stocks less volatile
            
            price = base_price * (1 + random.uniform(-0.02, 0.02))
            change = price * (change_percent / 100)
            
            mock_data.append(FinancialItem(
                symbol=symbol.upper(),
                name=self._get_company_name(symbol) if not is_crypto else self._get_crypto_name(symbol),
                price=round(price, 2),
                change=round(change, 2),
                change_percent=round(change_percent, 2),
                currency="USD",
                data_type="crypto" if is_crypto else "stocks",
                last_updated=dt.datetime.now().isoformat()
            ))
        
        market_status = "mixed" if any(item.data_type == "crypto" for item in mock_data) and any(item.data_type == "stocks" for item in mock_data) else "open"
        summary = self._create_financial_summary(mock_data)
        
        return FinancialOutput(
            request_time=dt.datetime.now().isoformat(),
            total_items=len(mock_data),
            market_status=market_status,
            data=mock_data,
            summary=summary
        )

    def _get_company_name(self, symbol: str) -> str:
        """Get company name for stock symbol."""
        company_names = {
            "MSFT": "Microsoft Corporation",
            "NVDA": "NVIDIA Corporation", 
            "GOOGL": "Alphabet Inc.",
            "SMR": "NuScale Power Corporation",
            "VOO": "Vanguard S&P 500 ETF",
            "SPY": "SPDR S&P 500 ETF Trust"
        }
        return company_names.get(symbol.upper(), f"{symbol.upper()} Corporation")

    def _get_crypto_name(self, symbol: str) -> str:
        """Get full name for crypto symbol."""
        crypto_names = {
            "BTC": "Bitcoin",
            "ETH": "Ethereum",
            "ADA": "Cardano",
            "SOL": "Solana",
            "DOGE": "Dogecoin",
            "LTC": "Litecoin",
            "XRP": "XRP",
            "DOT": "Polkadot",
            "LINK": "Chainlink",
            "UNI": "Uniswap"
        }
        return crypto_names.get(symbol.upper(), symbol.upper())

    def _get_market_status(self, financial_items: List[FinancialItem]) -> str:
        """Determine market status based on the data types."""
        has_stocks = any(item.data_type == "stocks" for item in financial_items)
        has_crypto = any(item.data_type == "crypto" for item in financial_items)
        
        if has_stocks and has_crypto:
            return "mixed"
        elif has_crypto:
            return "24/7"  # Crypto markets are always open
        else:
            # Check if during market hours (simplified)
            now = dt.datetime.now()
            if 9 <= now.hour < 16 and now.weekday() < 5:  # Market hours Mon-Fri 9am-4pm
                return "open"
            else:
                return "closed"

    def _create_financial_summary(self, financial_items: List[FinancialItem]) -> str:
        """Create a summary of the financial data."""
        if not financial_items:
            return "No financial data available"
        
        gains = [item for item in financial_items if item.change > 0]
        losses = [item for item in financial_items if item.change < 0]
        
        # Find best and worst performers
        best = max(financial_items, key=lambda x: x.change_percent)
        worst = min(financial_items, key=lambda x: x.change_percent)
        
        summary_parts = []
        summary_parts.append(f"📊 {len(financial_items)} instruments tracked")
        
        if gains:
            summary_parts.append(f"📈 {len(gains)} gaining")
        if losses:
            summary_parts.append(f"📉 {len(losses)} declining")
        
        summary_parts.append(f"🏆 Best: {best.symbol} (+{best.change_percent:.1f}%)")
        if worst.change_percent < 0:
            summary_parts.append(f"📉 Worst: {worst.symbol} ({worst.change_percent:.1f}%)")
        
        return " | ".join(summary_parts)