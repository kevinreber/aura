"""HTTP client utilities for external API calls."""

import httpx
import time
from typing import Dict, Any, Optional
from .logging import get_logger, log_api_call

logger = get_logger("http_client")


class HTTPClient:
    """Async HTTP client with logging and error handling."""
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._client = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def get(
        self, 
        url: str, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """Make an async GET request with logging."""
        return await self._request("GET", url, params=params, headers=headers)
    
    async def post(
        self, 
        url: str, 
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """Make an async POST request with logging."""
        return await self._request("POST", url, json=json, data=data, headers=headers)
    
    async def _request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> httpx.Response:
        """Make an async HTTP request with timing and logging."""
        start_time = time.time()
        
        try:
            logger.debug(f"Making {method} request to {url}")
            response = await self._client.request(method, url, **kwargs)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log the API call
            log_api_call(url, method, response.status_code, duration_ms)
            
            # Raise for bad status codes
            response.raise_for_status()
            
            return response
            
        except httpx.HTTPStatusError as e:
            duration_ms = (time.time() - start_time) * 1000
            log_api_call(url, method, e.response.status_code, duration_ms)
            logger.error(f"HTTP error {e.response.status_code} for {method} {url}: {e}")
            raise
            
        except httpx.RequestError as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Request error for {method} {url}: {e}")
            raise
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Unexpected error for {method} {url}: {e}")
            raise


async def get_json(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Convenience function to make a GET request and return JSON."""
    async with HTTPClient() as client:
        response = await client.get(url, params=params, headers=headers)
        return response.json()


async def post_json(url: str, json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Convenience function to make a POST request and return JSON."""
    async with HTTPClient() as client:
        response = await client.post(url, json=json, headers=headers)
        return response.json()
