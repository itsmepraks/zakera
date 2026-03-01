#!/usr/bin/env python3
"""
OpenAPI Schema Validator

Validates the OpenAPI specification against best practices and standards.
Ensures API documentation is complete, accurate, and follows OpenAPI 3.0 spec.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import re


class OpenAPIValidator:
    """Validates OpenAPI 3.0 specifications."""

    def __init__(self, spec_path: str):
        self.spec_path = Path(spec_path)
        self.spec: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info_messages: List[str] = []

    def load_spec(self) -> bool:
        """Load OpenAPI specification from file."""
        try:
            with open(self.spec_path, 'r') as f:
                self.spec = json.load(f)
            return True
        except FileNotFoundError:
            self.errors.append(f"Specification file not found: {self.spec_path}")
            return False
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON in specification: {e}")
            return False

    def validate_structure(self) -> None:
        """Validate basic OpenAPI structure."""
        required_fields = ['openapi', 'info', 'paths']
        
        for field in required_fields:
            if field not in self.spec:
                self.errors.append(f"Missing required field: {field}")
        
        # Check OpenAPI version
        if 'openapi' in self.spec:
            version = self.spec['openapi']
            if not version.startswith('3.'):
                self.errors.append(f"Unsupported OpenAPI version: {version} (expected 3.x)")

    def validate_info(self) -> None:
        """Validate info section."""
        if 'info' not in self.spec:
            return
        
        info = self.spec['info']
        required_info_fields = ['title', 'version']
        recommended_info_fields = ['description', 'contact', 'license']
        
        for field in required_info_fields:
            if field not in info:
                self.errors.append(f"Missing required info field: {field}")
        
        for field in recommended_info_fields:
            if field not in info:
                self.warnings.append(f"Recommended info field missing: {field}")
        
        # Validate version format
        if 'version' in info:
            version = info['version']
            if not re.match(r'^\d+\.\d+\.\d+', version):
                self.warnings.append(f"Version should follow semver format: {version}")

    def validate_paths(self) -> None:
        """Validate API paths."""
        if 'paths' not in self.spec:
            return
        
        paths = self.spec['paths']
        
        if not paths:
            self.warnings.append("No paths defined in specification")
            return
        
        self.info_messages.append(f"Found {len(paths)} API paths")
        
        for path, path_item in paths.items():
            self._validate_path(path, path_item)

    def _validate_path(self, path: str, path_item: Dict[str, Any]) -> None:
        """Validate individual path."""
        # Check path format
        if not path.startswith('/'):
            self.errors.append(f"Path must start with '/': {path}")
        
        # Check for path parameters
        path_params = re.findall(r'\{([^}]+)\}', path)
        
        # Validate operations
        http_methods = ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']
        
        for method in http_methods:
            if method in path_item:
                self._validate_operation(path, method, path_item[method], path_params)

    def _validate_operation(self, path: str, method: str, operation: Dict[str, Any], path_params: List[str]) -> None:
        """Validate individual operation."""
        op_id = f"{method.upper()} {path}"
        
        # Check for operationId
        if 'operationId' not in operation:
            self.warnings.append(f"{op_id}: Missing operationId")
        
        # Check for summary
        if 'summary' not in operation:
            self.warnings.append(f"{op_id}: Missing summary")
        
        # Check for description
        if 'description' not in operation:
            self.warnings.append(f"{op_id}: Missing description")
        
        # Check for tags
        if 'tags' not in operation or not operation['tags']:
            self.warnings.append(f"{op_id}: Missing tags")
        
        # Validate parameters
        if 'parameters' in operation:
            self._validate_parameters(op_id, operation['parameters'], path_params)
        elif path_params:
            self.errors.append(f"{op_id}: Path has parameters but no parameter definitions")
        
        # Validate responses
        if 'responses' not in operation:
            self.errors.append(f"{op_id}: Missing responses")
        else:
            self._validate_responses(op_id, operation['responses'])
        
        # Check for security
        if method in ['post', 'put', 'patch', 'delete']:
            if 'security' not in operation and 'security' not in self.spec:
                self.warnings.append(f"{op_id}: No security defined for mutating operation")

    def _validate_parameters(self, op_id: str, parameters: List[Dict[str, Any]], path_params: List[str]) -> None:
        """Validate operation parameters."""
        defined_path_params = set()
        
        for param in parameters:
            if 'name' not in param:
                self.errors.append(f"{op_id}: Parameter missing 'name'")
                continue
            
            if 'in' not in param:
                self.errors.append(f"{op_id}: Parameter '{param['name']}' missing 'in'")
                continue
            
            if param['in'] == 'path':
                defined_path_params.add(param['name'])
                if 'required' not in param or not param['required']:
                    self.errors.append(f"{op_id}: Path parameter '{param['name']}' must be required")
            
            if 'schema' not in param and 'content' not in param:
                self.errors.append(f"{op_id}: Parameter '{param['name']}' missing schema or content")
        
        # Check all path parameters are defined
        for path_param in path_params:
            if path_param not in defined_path_params:
                self.errors.append(f"{op_id}: Path parameter '{path_param}' not defined")

    def _validate_responses(self, op_id: str, responses: Dict[str, Any]) -> None:
        """Validate operation responses."""
        if not responses:
            self.errors.append(f"{op_id}: No responses defined")
            return
        
        # Check for success response
        success_codes = {'200', '201', '202', '204'}
        if not any(code in responses for code in success_codes):
            self.warnings.append(f"{op_id}: No success response (2xx) defined")
        
        # Check for error responses
        if '400' not in responses and '422' not in responses:
            self.warnings.append(f"{op_id}: Missing 400/422 validation error response")
        
        if '500' not in responses:
            self.warnings.append(f"{op_id}: Missing 500 server error response")
        
        # Validate each response
        for status_code, response in responses.items():
            if 'description' not in response:
                self.errors.append(f"{op_id}: Response {status_code} missing description")

    def validate_components(self) -> None:
        """Validate components/schemas."""
        if 'components' not in self.spec:
            self.warnings.append("No components/schemas defined")
            return
        
        components = self.spec['components']
        
        if 'schemas' in components:
            schemas = components['schemas']
            self.info_messages.append(f"Found {len(schemas)} schema definitions")
            
            for schema_name, schema in schemas.items():
                self._validate_schema(schema_name, schema)

    def _validate_schema(self, name: str, schema: Dict[str, Any]) -> None:
        """Validate individual schema."""
        if 'type' not in schema and '$ref' not in schema and 'allOf' not in schema:
            self.warnings.append(f"Schema '{name}': Missing type definition")
        
        # Check for description
        if 'description' not in schema:
            self.warnings.append(f"Schema '{name}': Missing description")
        
        # Validate object properties
        if schema.get('type') == 'object':
            if 'properties' not in schema:
                self.warnings.append(f"Schema '{name}': Object type but no properties defined")

    def validate_security(self) -> None:
        """Validate security schemes."""
        if 'components' in self.spec and 'securitySchemes' in self.spec['components']:
            schemes = self.spec['components']['securitySchemes']
            self.info_messages.append(f"Found {len(schemes)} security schemes")
        else:
            self.warnings.append("No security schemes defined")

    def validate_tags(self) -> None:
        """Validate tags."""
        if 'tags' in self.spec:
            tags = self.spec['tags']
            self.info_messages.append(f"Found {len(tags)} tags")
            
            for tag in tags:
                if 'name' not in tag:
                    self.errors.append("Tag missing 'name'")
                if 'description' not in tag:
                    self.warnings.append(f"Tag '{tag.get('name', 'unknown')}' missing description")
        else:
            self.warnings.append("No tags defined")

    def validate_servers(self) -> None:
        """Validate server definitions."""
        if 'servers' not in self.spec:
            self.warnings.append("No servers defined")
        else:
            servers = self.spec['servers']
            self.info_messages.append(f"Found {len(servers)} server(s)")
            
            for idx, server in enumerate(servers):
                if 'url' not in server:
                    self.errors.append(f"Server {idx}: Missing URL")
                if 'description' not in server:
                    self.warnings.append(f"Server {idx}: Missing description")

    def validate_all(self) -> bool:
        """Run all validations."""
        if not self.load_spec():
            return False
        
        self.validate_structure()
        self.validate_info()
        self.validate_paths()
        self.validate_components()
        self.validate_security()
        self.validate_tags()
        self.validate_servers()
        
        return len(self.errors) == 0

    def print_report(self) -> None:
        """Print validation report."""
        print("\n" + "="*70)
        print("OpenAPI Specification Validation Report")
        print("="*70 + "\n")
        
        print(f"Specification: {self.spec_path}")
        print(f"OpenAPI Version: {self.spec.get('openapi', 'Unknown')}")
        print(f"API Title: {self.spec.get('info', {}).get('title', 'Unknown')}")
        print(f"API Version: {self.spec.get('info', {}).get('version', 'Unknown')}")
        print()
        
        # Info messages
        if self.info_messages:
            print("\033[34mℹ Info:\033[0m")
            for msg in self.info_messages:
                print(f"  • {msg}")
            print()
        
        # Warnings
        if self.warnings:
            print(f"\033[33m⚠ Warnings ({len(self.warnings)}):\033[0m")
            for warning in self.warnings:
                print(f"  • {warning}")
            print()
        
        # Errors
        if self.errors:
            print(f"\033[31m✗ Errors ({len(self.errors)}):\033[0m")
            for error in self.errors:
                print(f"  • {error}")
            print()
        else:
            print("\033[32m✓ No errors found!\033[0m\n")
        
        # Summary
        print("="*70)
        if self.errors:
            print(f"\033[31mValidation FAILED with {len(self.errors)} error(s)\033[0m")
        elif self.warnings:
            print(f"\033[33mValidation PASSED with {len(self.warnings)} warning(s)\033[0m")
        else:
            print("\033[32mValidation PASSED - Excellent! ✨\033[0m")
        print("="*70 + "\n")

    def generate_stats(self) -> Dict[str, Any]:
        """Generate specification statistics."""
        paths = self.spec.get('paths', {})
        schemas = self.spec.get('components', {}).get('schemas', {})
        
        # Count operations
        operations = 0
        operations_by_method: Dict[str, int] = {}
        
        for path, path_item in paths.items():
            for method in ['get', 'post', 'put', 'patch', 'delete']:
                if method in path_item:
                    operations += 1
                    operations_by_method[method] = operations_by_method.get(method, 0) + 1
        
        return {
            'total_paths': len(paths),
            'total_operations': operations,
            'operations_by_method': operations_by_method,
            'total_schemas': len(schemas),
            'has_security': 'components' in self.spec and 'securitySchemes' in self.spec['components'],
            'has_tags': 'tags' in self.spec,
            'has_servers': 'servers' in self.spec,
        }


def main():
    """Main validation entry point."""
    if len(sys.argv) < 2:
        print("Usage: python openapi-validator.py <path-to-openapi.json>")
        print("\nExample:")
        print("  python openapi-validator.py docs/api/openapi.json")
        sys.exit(1)
    
    spec_path = sys.argv[1]
    
    print(f"\nValidating OpenAPI specification: {spec_path}\n")
    
    validator = OpenAPIValidator(spec_path)
    
    # Run validation
    is_valid = validator.validate_all()
    
    # Print report
    validator.print_report()
    
    # Print statistics
    stats = validator.generate_stats()
    print("\nSpecification Statistics:")
    print(f"  Total Paths: {stats['total_paths']}")
    print(f"  Total Operations: {stats['total_operations']}")
    print(f"  Operations by Method: {stats['operations_by_method']}")
    print(f"  Total Schemas: {stats['total_schemas']}")
    print(f"  Has Security: {stats['has_security']}")
    print(f"  Has Tags: {stats['has_tags']}")
    print(f"  Has Servers: {stats['has_servers']}")
    print()
    
    # Exit with appropriate code
    if validator.errors:
        sys.exit(1)
    elif validator.warnings:
        sys.exit(0)  # Warnings don't fail
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
