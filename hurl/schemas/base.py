"""Base mixin for custom __repr__ and __str__ methods using YAML-style output."""

import yaml
from typing import Any, Dict, ClassVar


class ModelReprMixin:
    """Mixin that provides YAML-style __repr__ and __str__ methods for Pydantic models.
    
    This mixin adds YAML-formatted string representations to Pydantic models,
    showing only set (non-None) values with proper indentation and line breaks.
    Each representation includes a header with the model class name.
    
    Example output:
        GetDataResponse:
          status: success
          data:
            - id: 1
              value: 3.14
              tags:
                - foo
                - bar
            - id: 2
              value: 2.71
    
    Usage:
        class MyModel(BaseModel, ModelReprMixin):
            field1: str
            field2: Optional[int] = None
    
    Attributes:
        always_include_fields (set): Field names to always include even if None.
            Can be overridden by subclasses to customize which fields are always shown.
    """
    
    # Fields to always include even if None - can be overridden by subclasses
    always_include_fields: ClassVar[set] = set()
    
    def _to_yaml(self) -> str:
        """Generate YAML string representation of the model.
        
        Returns:
            str: YAML-formatted string with model name as header.
        """
        # Get model data, excluding unset fields unless they're in _always_include_fields
        model_data = self.model_dump(exclude_unset=True)
        
        # Add back any fields marked as always_include, even if they were None
        # Check for always_include_fields on the class, not the instance
        always_include = getattr(self.__class__, 'always_include_fields', set())
        for field_name in always_include:
            if hasattr(self, field_name):
                field_value = getattr(self, field_name)
                model_data[field_name] = field_value
        
        # Create the YAML structure with class name as header
        yaml_data = {self.__class__.__name__: model_data}
        
        # Convert to YAML with proper formatting
        yaml_str = yaml.dump(
            yaml_data,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=120,  # Prevent excessive line wrapping
            allow_unicode=True,
        )
        
        # Remove trailing newline for cleaner output
        return yaml_str.rstrip('\n')
    
    def __repr__(self) -> str:
        """Return YAML-style representation of the model."""
        return self._to_yaml()
    
    def __str__(self) -> str:
        """Return YAML-style string representation of the model."""
        return self._to_yaml()