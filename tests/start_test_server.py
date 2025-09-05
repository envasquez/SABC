#!/usr/bin/env python3
"""
Start test server for integration tests
"""
import os
import signal
import subprocess
import sys
import time

def start_server():
    """Start the FastAPI server for testing"""
    print("Starting test server...")
    
    # Start server
    server = subprocess.Popen([
        "uvicorn", "app:app", 
        "--host", "127.0.0.1", 
        "--port", "8000",
        "--log-level", "warning"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for server to be ready
    time.sleep(5)
    
    # Check if server is running
    try:
        import requests
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code in [200, 503]:
            print("✅ Server is ready")
            return server
    except:
        pass
    
    print("⚠️ Server may not be fully ready, continuing anyway...")
    return server

def stop_server(server):
    """Stop the test server"""
    if server:
        print("Stopping test server...")
        server.terminate()
        server.wait()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        # Just for manual stopping
        os.system("pkill -f 'uvicorn app:app'")
    else:
        server = start_server()
        try:
            # Keep server running until interrupted
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_server(server)