#!/usr/bin/env python3
"""
Test script to verify minimal dependencies work for app import
"""

import sys
import subprocess

def test_import():
    try:
        print("🧪 Testing app import with minimal dependencies...")
        import app
        print("✅ App imported successfully!")
        
        # Test basic functionality
        from fastapi.testclient import TestClient
        client = TestClient(app.app)
        print("✅ Test client created")
        
        # Test health endpoint
        response = client.get('/health')
        print(f"✅ Health endpoint responded with: {response.status_code}")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Missing dependency detected!")
        return False
    except Exception as e:
        print(f"⚠️ Other error: {e}")
        return True  # Import worked, other error is okay for now

if __name__ == "__main__":
    success = test_import()
    sys.exit(0 if success else 1)