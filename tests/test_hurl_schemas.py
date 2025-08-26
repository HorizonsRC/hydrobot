"""Tests for hurl schemas and ModelReprMixin."""

import pytest
import yaml
from hurl.schemas import ModelReprMixin, DataItem, GetDataRequest, GetDataResponse


class TestModelReprMixin:
    """Test the ModelReprMixin functionality."""
    
    def test_data_item_yaml_representation(self):
        """Test DataItem YAML representation."""
        item = DataItem(id=1, value=3.14, tags=["foo", "bar"])
        result = str(item)
        
        # Check that the output starts with the class name
        assert result.startswith("DataItem:")
        
        # Parse the YAML to verify it's valid
        parsed = yaml.safe_load(result)
        assert "DataItem" in parsed
        assert parsed["DataItem"]["id"] == 1
        assert parsed["DataItem"]["value"] == 3.14
        assert parsed["DataItem"]["tags"] == ["foo", "bar"]
    
    def test_data_item_excludes_none_values(self):
        """Test that None values are excluded from representation."""
        item = DataItem(id=1, value=3.14)  # tags and metadata will be None
        result = str(item)
        
        parsed = yaml.safe_load(result)
        data_item = parsed["DataItem"]
        
        # Should include set values
        assert "id" in data_item
        assert "value" in data_item
        
        # Should exclude None values
        assert "tags" not in data_item
        assert "metadata" not in data_item
    
    def test_get_data_request_yaml_representation(self):
        """Test GetDataRequest YAML representation."""
        request = GetDataRequest(
            site="TestSite",
            measurement="WaterLevel",
            from_date="2023-01-01",
            to_date="2023-01-31"
        )
        result = str(request)
        
        # Check that the output starts with the class name
        assert result.startswith("GetDataRequest:")
        
        # Parse the YAML to verify structure
        parsed = yaml.safe_load(result)
        assert "GetDataRequest" in parsed
        req_data = parsed["GetDataRequest"]
        assert req_data["site"] == "TestSite"
        assert req_data["measurement"] == "WaterLevel"
        assert req_data["from_date"] == "2023-01-01"
        assert req_data["to_date"] == "2023-01-31"
    
    def test_get_data_request_always_includes_limit(self):
        """Test that limit field is always included even when None."""
        request = GetDataRequest(site="TestSite", measurement="WaterLevel")
        result = str(request)
        
        parsed = yaml.safe_load(result)
        req_data = parsed["GetDataRequest"]
        
        # limit should be included even though it's None
        assert "limit" in req_data
        assert req_data["limit"] is None
    
    def test_get_data_response_yaml_representation(self):
        """Test GetDataResponse YAML representation with nested models."""
        data_items = [
            DataItem(id=1, value=3.14, tags=["foo", "bar"]),
            DataItem(id=2, value=2.71, tags=["baz"])
        ]
        
        response = GetDataResponse(
            status="success",
            data=data_items,
            total_count=2
        )
        result = str(response)
        
        # Check that the output starts with the class name
        assert result.startswith("GetDataResponse:")
        
        # Parse the YAML to verify nested structure
        parsed = yaml.safe_load(result)
        assert "GetDataResponse" in parsed
        resp_data = parsed["GetDataResponse"]
        
        assert resp_data["status"] == "success"
        assert resp_data["total_count"] == 2
        assert len(resp_data["data"]) == 2
        
        # Check nested data items
        first_item = resp_data["data"][0]
        assert first_item["id"] == 1
        assert first_item["value"] == 3.14
        assert first_item["tags"] == ["foo", "bar"]
        
        second_item = resp_data["data"][1]
        assert second_item["id"] == 2
        assert second_item["value"] == 2.71
        assert second_item["tags"] == ["baz"]
    
    def test_get_data_response_always_includes_error_message(self):
        """Test that error_message field is always included even when None."""
        response = GetDataResponse(status="success")
        result = str(response)
        
        parsed = yaml.safe_load(result)
        resp_data = parsed["GetDataResponse"]
        
        # error_message should be included even though it's None
        assert "error_message" in resp_data
        assert resp_data["error_message"] is None
    
    def test_repr_equals_str(self):
        """Test that __repr__ and __str__ return the same value."""
        item = DataItem(id=1, value=3.14, tags=["foo"])
        assert repr(item) == str(item)
    
    def test_yaml_is_valid(self):
        """Test that the output is always valid YAML."""
        # Test with complex nested structure
        response = GetDataResponse(
            status="success",
            data=[
                DataItem(id=1, value=3.14159, tags=["pi", "math", "constant"]),
                DataItem(id=2, value=2.71828, tags=["e", "euler"])
            ],
            total_count=100,
            metadata={"version": "1.0", "source": "test"}
        )
        
        result = str(response)
        
        # Should be parseable as YAML
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)
        assert "GetDataResponse" in parsed
    
    def test_output_format_example(self):
        """Test that output matches the expected format from the issue description."""
        data_items = [
            DataItem(id=1, value=3.14, tags=["foo", "bar"]),
            DataItem(id=2, value=2.71)
        ]
        
        response = GetDataResponse(status="success", data=data_items)
        result = str(response)
        
        # Verify the general structure matches expectations
        lines = result.split('\n')
        assert lines[0] == "GetDataResponse:"
        assert any("status: success" in line for line in lines)
        assert any("data:" in line for line in lines)
        assert any("id: 1" in line for line in lines)
        assert any("value: 3.14" in line for line in lines)
        assert any("- foo" in line for line in lines)
        assert any("- bar" in line for line in lines)