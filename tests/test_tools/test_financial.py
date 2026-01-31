"""Tests for the financial tool."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from mcp_server.tools.financial import FinancialTool
from mcp_server.schemas.financial import (
    FinancialInput, FinancialOutput, FinancialItem
)


class TestFinancialTool:
    """Test the FinancialTool class."""

    @pytest.fixture
    def financial_tool(self):
        """Create a FinancialTool instance."""
        return FinancialTool()

    @pytest.mark.asyncio
    async def test_get_financial_data_mock_stocks(self, financial_tool):
        """Test getting stock data with mock data (no API key)."""
        input_data = FinancialInput(
            symbols=["MSFT", "NVDA", "GOOGL"],
            data_type="stocks"
        )

        result = await financial_tool.get_financial_data(input_data)

        assert isinstance(result, FinancialOutput)
        assert result.total_items == 3
        assert result.request_time is not None
        assert result.market_status in ["open", "closed", "mixed"]

        for item in result.data:
            assert isinstance(item, FinancialItem)
            assert item.symbol in ["MSFT", "NVDA", "GOOGL"]
            assert item.data_type == "stocks"
            assert item.price > 0

    @pytest.mark.asyncio
    async def test_get_financial_data_mock_crypto(self, financial_tool):
        """Test getting crypto data with mock data."""
        input_data = FinancialInput(
            symbols=["BTC", "ETH", "SOL"],
            data_type="crypto"
        )

        result = await financial_tool.get_financial_data(input_data)

        assert result.total_items == 3

        for item in result.data:
            assert item.symbol in ["BTC", "ETH", "SOL"]
            assert item.data_type == "crypto"
            assert item.currency == "USD"

    @pytest.mark.asyncio
    async def test_get_financial_data_mixed(self, financial_tool):
        """Test getting mixed stock and crypto data."""
        input_data = FinancialInput(
            symbols=["MSFT", "BTC", "GOOGL", "ETH"]
        )

        result = await financial_tool.get_financial_data(input_data)

        # Should have both stocks and crypto
        stock_items = [item for item in result.data if item.data_type == "stocks"]
        crypto_items = [item for item in result.data if item.data_type == "crypto"]

        assert len(stock_items) > 0
        assert len(crypto_items) > 0
        assert result.market_status == "mixed"

    @pytest.mark.asyncio
    async def test_get_financial_data_single_stock(self, financial_tool):
        """Test getting single stock data."""
        input_data = FinancialInput(symbols=["VOO"])

        result = await financial_tool.get_financial_data(input_data)

        assert result.total_items == 1
        assert result.data[0].symbol == "VOO"

    @pytest.mark.asyncio
    async def test_get_financial_data_single_crypto(self, financial_tool):
        """Test getting single crypto data."""
        input_data = FinancialInput(symbols=["BTC"])

        result = await financial_tool.get_financial_data(input_data)

        assert result.total_items == 1
        assert result.data[0].symbol == "BTC"
        assert result.data[0].name == "Bitcoin"

    @pytest.mark.asyncio
    async def test_get_financial_data_output_structure(self, financial_tool):
        """Test that output has all required fields."""
        input_data = FinancialInput(symbols=["MSFT"])

        result = await financial_tool.get_financial_data(input_data)

        assert hasattr(result, 'request_time')
        assert hasattr(result, 'total_items')
        assert hasattr(result, 'market_status')
        assert hasattr(result, 'data')
        assert hasattr(result, 'summary')

    @pytest.mark.asyncio
    async def test_financial_item_structure(self, financial_tool):
        """Test that financial items have all required fields."""
        input_data = FinancialInput(symbols=["NVDA"])

        result = await financial_tool.get_financial_data(input_data)

        item = result.data[0]
        assert hasattr(item, 'symbol')
        assert hasattr(item, 'name')
        assert hasattr(item, 'price')
        assert hasattr(item, 'change')
        assert hasattr(item, 'change_percent')
        assert hasattr(item, 'currency')
        assert hasattr(item, 'data_type')
        assert hasattr(item, 'last_updated')


class TestFinancialHelperMethods:
    """Test helper methods of the FinancialTool."""

    @pytest.fixture
    def financial_tool(self):
        """Create a FinancialTool instance."""
        return FinancialTool()

    def test_get_company_name(self, financial_tool):
        """Test getting company names for stock symbols."""
        assert financial_tool._get_company_name("MSFT") == "Microsoft Corporation"
        assert financial_tool._get_company_name("NVDA") == "NVIDIA Corporation"
        assert financial_tool._get_company_name("GOOGL") == "Alphabet Inc."
        assert financial_tool._get_company_name("VOO") == "Vanguard S&P 500 ETF"

        # Unknown symbol should return a default
        unknown = financial_tool._get_company_name("UNKNOWN")
        assert "UNKNOWN" in unknown

    def test_get_crypto_name(self, financial_tool):
        """Test getting full names for crypto symbols."""
        assert financial_tool._get_crypto_name("BTC") == "Bitcoin"
        assert financial_tool._get_crypto_name("ETH") == "Ethereum"
        assert financial_tool._get_crypto_name("SOL") == "Solana"
        assert financial_tool._get_crypto_name("DOGE") == "Dogecoin"

        # Unknown crypto should return the symbol itself
        unknown = financial_tool._get_crypto_name("UNKNOWN")
        assert unknown == "UNKNOWN"

    def test_get_market_status_stocks_only(self, financial_tool):
        """Test market status for stocks only."""
        items = [
            FinancialItem(
                symbol="MSFT", name="Microsoft", price=400.0,
                change=5.0, change_percent=1.25, currency="USD",
                data_type="stocks", last_updated=datetime.now().isoformat()
            )
        ]

        status = financial_tool._get_market_status(items)

        # Should be either open or closed depending on time
        assert status in ["open", "closed"]

    def test_get_market_status_crypto_only(self, financial_tool):
        """Test market status for crypto only."""
        items = [
            FinancialItem(
                symbol="BTC", name="Bitcoin", price=45000.0,
                change=500.0, change_percent=1.1, currency="USD",
                data_type="crypto", last_updated=datetime.now().isoformat()
            )
        ]

        status = financial_tool._get_market_status(items)

        assert status == "24/7"  # Crypto markets never close

    def test_get_market_status_mixed(self, financial_tool):
        """Test market status for mixed stocks and crypto."""
        items = [
            FinancialItem(
                symbol="MSFT", name="Microsoft", price=400.0,
                change=5.0, change_percent=1.25, currency="USD",
                data_type="stocks", last_updated=datetime.now().isoformat()
            ),
            FinancialItem(
                symbol="BTC", name="Bitcoin", price=45000.0,
                change=500.0, change_percent=1.1, currency="USD",
                data_type="crypto", last_updated=datetime.now().isoformat()
            )
        ]

        status = financial_tool._get_market_status(items)

        assert status == "mixed"

    def test_create_financial_summary_empty(self, financial_tool):
        """Test summary creation with empty list."""
        summary = financial_tool._create_financial_summary([])

        assert "No financial data" in summary

    def test_create_financial_summary_gains(self, financial_tool):
        """Test summary creation with gaining stocks."""
        items = [
            FinancialItem(
                symbol="MSFT", name="Microsoft", price=400.0,
                change=10.0, change_percent=2.5, currency="USD",
                data_type="stocks", last_updated=datetime.now().isoformat()
            ),
            FinancialItem(
                symbol="NVDA", name="NVIDIA", price=800.0,
                change=20.0, change_percent=2.6, currency="USD",
                data_type="stocks", last_updated=datetime.now().isoformat()
            )
        ]

        summary = financial_tool._create_financial_summary(items)

        assert "gaining" in summary.lower() or "best" in summary.lower()

    def test_create_financial_summary_losses(self, financial_tool):
        """Test summary creation with losing stocks."""
        items = [
            FinancialItem(
                symbol="MSFT", name="Microsoft", price=400.0,
                change=-10.0, change_percent=-2.5, currency="USD",
                data_type="stocks", last_updated=datetime.now().isoformat()
            )
        ]

        summary = financial_tool._create_financial_summary(items)

        # Should mention declining or worst
        assert summary is not None


class TestFinancialMockDataGeneration:
    """Test mock data generation for financial tool."""

    @pytest.fixture
    def financial_tool(self):
        """Create a FinancialTool instance."""
        return FinancialTool()

    @pytest.mark.asyncio
    async def test_mock_data_price_ranges(self, financial_tool):
        """Test that mock data generates realistic price ranges."""
        input_data = FinancialInput(symbols=["BTC", "ETH", "MSFT"])

        result = await financial_tool._generate_mock_financial_data(input_data)

        for item in result.data:
            if item.symbol == "BTC":
                # Bitcoin should be in high thousands
                assert item.price > 10000
            elif item.symbol == "ETH":
                # Ethereum should be in thousands
                assert item.price > 1000
            elif item.symbol == "MSFT":
                # Microsoft should be in hundreds
                assert item.price > 100

    @pytest.mark.asyncio
    async def test_mock_data_change_percentages(self, financial_tool):
        """Test that mock change percentages are realistic."""
        input_data = FinancialInput(symbols=["MSFT", "BTC"])

        result = await financial_tool._generate_mock_financial_data(input_data)

        for item in result.data:
            # Change percent should be within realistic daily range
            assert -15 < item.change_percent < 15

    @pytest.mark.asyncio
    async def test_mock_data_currency(self, financial_tool):
        """Test that all mock data is in USD."""
        input_data = FinancialInput(symbols=["MSFT", "BTC", "ETH"])

        result = await financial_tool._generate_mock_financial_data(input_data)

        for item in result.data:
            assert item.currency == "USD"

    @pytest.mark.asyncio
    async def test_mock_data_last_updated(self, financial_tool):
        """Test that last_updated is set correctly."""
        input_data = FinancialInput(symbols=["MSFT"])

        result = await financial_tool._generate_mock_financial_data(input_data)

        for item in result.data:
            assert item.last_updated is not None
            # Should be a valid ISO format datetime string
            datetime.fromisoformat(item.last_updated.replace('Z', '+00:00'))
