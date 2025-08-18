#!/usr/bin/env python3

"""
Test script for hIGMA integration with masq-monitor.
This script validates that hIGMA YAML files can be properly parsed and converted.
"""

import unittest
import tempfile
import os
import yaml
from masq_monitor import MasqMonitor

class TestHIGMAIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            "output_directory": "test_output",
            "default_days": 7,
            "report_username": "TestUser",
            "queries": {}
        }
        
        # Create a temporary config file
        self.config_fd, self.config_path = tempfile.mkstemp(suffix='.yaml')
        with os.fdopen(self.config_fd, 'w') as f:
            yaml.dump(self.test_config, f)
            
        self.monitor = MasqMonitor(config_path=self.config_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.config_path)
    
    def test_parse_higma_file_valid(self):
        """Test parsing a valid hIGMA file."""
        # Create a test hIGMA file
        test_higma_data = {
            'metadata': {
                'rules_title': 'Test Threat Detection',
                'rules_id': 'test-123',
                'rules_author': 'TestAuthor',
                'rules_date': '2025-08-17',
                'threat_actor': 'TEST',
                'references': [
                    'https://example.com/reference1',
                    'https://example.com/reference2'
                ],
                'plugin': 'urlscan',
                'plugin_version': '1.0',
                'description': 'Test threat detection rule'
            },
            'queries': [
                {
                    'query_id': 'test_query',
                    'query': 'page.title:"Test Title"',
                    'pivot_ids': ['P0401.001'],
                    'query_type': 'title',
                    'description': 'Test query description',
                    'implementation_notes': 'Test implementation notes'
                }
            ]
        }
        
        # Create temporary hIGMA file
        higma_fd, higma_path = tempfile.mkstemp(suffix='.yaml')
        with os.fdopen(higma_fd, 'w') as f:
            yaml.dump(test_higma_data, f)
        
        try:
            # Parse the hIGMA file
            converted_queries = self.monitor.parse_higma_file(higma_path)
            
            # Validate the conversion
            self.assertEqual(len(converted_queries), 1)
            
            query_name = list(converted_queries.keys())[0]
            query_data = converted_queries[query_name]
            
            self.assertTrue(query_name.startswith('higma_test_query_'))
            self.assertEqual(query_data['query'], 'page.title:"Test Title"')
            self.assertEqual(query_data['platform'], 'urlscan')
            self.assertEqual(query_data['description'], 'Test query description')
            self.assertIn('P0401.001', query_data['tags'])
            self.assertIn('higma', query_data['tags'])
            self.assertIn('imported', query_data['tags'])
            
        finally:
            os.unlink(higma_path)
    
    def test_parse_higma_file_nonexistent(self):
        """Test parsing a non-existent hIGMA file."""
        converted_queries = self.monitor.parse_higma_file('/nonexistent/file.yaml')
        self.assertEqual(len(converted_queries), 0)
    
    def test_parse_higma_file_invalid_yaml(self):
        """Test parsing an invalid YAML file."""
        # Create invalid YAML file
        invalid_fd, invalid_path = tempfile.mkstemp(suffix='.yaml')
        with os.fdopen(invalid_fd, 'w') as f:
            f.write('invalid: yaml: content: [unclosed')
        
        try:
            converted_queries = self.monitor.parse_higma_file(invalid_path)
            self.assertEqual(len(converted_queries), 0)
        finally:
            os.unlink(invalid_path)

if __name__ == '__main__':
    unittest.main()
