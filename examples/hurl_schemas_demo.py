#!/usr/bin/env python3
"""Example demonstrating YAML-style Pydantic model representations in hurl.schemas."""

from hurl.schemas import DataItem, GetDataRequest, GetDataResponse


def main():
    """Demonstrate the YAML-style model representations."""
    
    print("=" * 60)
    print("HURL Schemas - YAML-Style Model Representation Demo")
    print("=" * 60)
    
    # Example 1: Basic DataItem
    print("\n1. DataItem with all fields set:")
    print("-" * 35)
    item1 = DataItem(
        id=1, 
        value=3.14159, 
        tags=["pi", "mathematics", "constant"],
        metadata={"precision": "high", "source": "calculation"}
    )
    print(item1)
    
    # Example 2: DataItem with minimal fields (shows exclusion of None values)
    print("\n2. DataItem with minimal fields (excludes None):")
    print("-" * 50)
    item2 = DataItem(id=2, value=2.71828)
    print(item2)
    
    # Example 3: GetDataRequest showing always_include_fields functionality
    print("\n3. GetDataRequest (note 'limit' field always included):")
    print("-" * 55)
    request = GetDataRequest(
        site="Manawatu at Teachers College",
        measurement="WaterLevel",
        from_date="2023-01-01",
        to_date="2023-01-31"
    )
    print(request)
    
    # Example 4: Complex GetDataResponse with nested data
    print("\n4. GetDataResponse with nested data items:")
    print("-" * 45)
    data_items = [
        DataItem(id=1, value=1.25, tags=["flow", "validated"]),
        DataItem(id=2, value=1.30, tags=["flow", "validated"]),
        DataItem(id=3, value=1.22, tags=["flow", "estimated"])
    ]
    
    response = GetDataResponse(
        status="success",
        data=data_items,
        total_count=3,
        metadata={
            "query_time": "2023-08-26T10:30:00Z",
            "source": "hilltop_server",
            "version": "2.0"
        }
    )
    print(response)
    
    # Example 5: Error response (shows always_include_fields for error_message)
    print("\n5. Error response (note 'error_message' always included):")
    print("-" * 55)
    error_response = GetDataResponse(
        status="error"
    )
    print(error_response)
    
    print("\n" + "=" * 60)
    print("All representations are valid YAML and can be parsed!")
    print("=" * 60)


if __name__ == "__main__":
    main()