"""Tests for the Flask application endpoints."""

import json
import pytest


class TestHealthEndpoint:
    """Test the health check endpoint."""
    
    def test_health_check(self, client):
        """Test that health check returns 200 with correct data."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'version' in data
        assert 'environment' in data


class TestToolsListEndpoint:
    """Test the tools listing endpoint."""
    
    def test_list_tools(self, client):
        """Test that tools endpoint returns available tools."""
        response = client.get('/tools')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'tools' in data
        
        tools = data['tools']
        expected_tools = [
            'weather.get_daily',
            'mobility.get_commute',
            'calendar.list_events',
            'todo.list'
        ]
        
        for tool_name in expected_tools:
            assert tool_name in tools
            assert 'description' in tools[tool_name]
            assert 'input_schema' in tools[tool_name]
            assert 'output_schema' in tools[tool_name]


class TestWeatherEndpoint:
    """Test the weather tool endpoint."""
    
    def test_weather_valid_input(self, client, sample_weather_input):
        """Test weather endpoint with valid input."""
        response = client.post(
            '/tools/weather.get_daily',
            data=json.dumps(sample_weather_input),
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'temp_hi' in data
        assert 'temp_lo' in data
        assert 'summary' in data
        assert 'location' in data
        assert 'date' in data
    
    def test_weather_missing_body(self, client):
        """Test weather endpoint with missing JSON body."""
        response = client.post('/tools/weather.get_daily')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_weather_invalid_input(self, client):
        """Test weather endpoint with invalid input."""
        invalid_input = {"invalid_field": "value"}
        response = client.post(
            '/tools/weather.get_daily',
            data=json.dumps(invalid_input),
            content_type='application/json'
        )
        assert response.status_code == 500  # Validation error


class TestMobilityEndpoint:
    """Test the mobility tool endpoint."""
    
    def test_mobility_valid_input(self, client, sample_mobility_input):
        """Test mobility endpoint with valid input."""
        response = client.post(
            '/tools/mobility.get_commute',
            data=json.dumps(sample_mobility_input),
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'duration_minutes' in data
        assert 'distance_miles' in data
        assert 'route_summary' in data
        assert 'traffic_status' in data
        assert 'origin' in data
        assert 'destination' in data
        assert 'mode' in data


class TestCalendarEndpoint:
    """Test the calendar tool endpoint."""
    
    def test_calendar_valid_input(self, client, sample_calendar_input):
        """Test calendar endpoint with valid input."""
        response = client.post(
            '/tools/calendar.list_events',
            data=json.dumps(sample_calendar_input),
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'date' in data
        assert 'events' in data
        assert 'total_events' in data
        assert isinstance(data['events'], list)


class TestTodoEndpoint:
    """Test the todo tool endpoint."""
    
    def test_todo_valid_input(self, client, sample_todo_input):
        """Test todo endpoint with valid input."""
        response = client.post(
            '/tools/todo.list',
            data=json.dumps(sample_todo_input),
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'bucket' in data
        assert 'items' in data
        assert 'total_items' in data
        assert 'completed_count' in data
        assert 'pending_count' in data
        assert isinstance(data['items'], list)


class TestErrorHandlers:
    """Test error handling."""
    
    def test_404_not_found(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_405_method_not_allowed(self, client):
        """Test 405 error handler."""
        response = client.get('/tools/weather.get_daily')  # Should be POST
        assert response.status_code == 405
        
        data = json.loads(response.data)
        assert 'error' in data
