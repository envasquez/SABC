#!/usr/bin/env python3
"""
Test runner for SABC application.
Orchestrates backend and frontend testing with proper setup and teardown.
"""

import os
import sys
import subprocess
import argparse
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import signal


class TestRunner:
    """Manages test execution for SABC application."""
    
    def __init__(self):
        self.test_db_path = None
        self.original_db_path = "sabc.db"
        self.app_process = None
        self.test_results = {
            "backend": {"passed": 0, "failed": 0, "errors": []},
            "frontend": {"passed": 0, "failed": 0, "errors": []},
            "coverage": {"percentage": 0, "missing_lines": []},
        }
    
    def setup_test_database(self):
        """Create a test database with sample data."""
        print("🔧 Setting up test database...")
        
        # Create temporary database
        temp_dir = tempfile.mkdtemp()
        self.test_db_path = Path(temp_dir) / "test_sabc.db"
        
        # Copy production database if it exists
        if Path(self.original_db_path).exists():
            shutil.copy(self.original_db_path, self.test_db_path)
            print(f"✅ Copied existing database to {self.test_db_path}")
        else:
            # Create new test database
            self.create_test_database()
        
        # Add test data
        self.populate_test_data()
        
        # Backup original and use test database
        if Path(self.original_db_path).exists():
            shutil.move(self.original_db_path, f"{self.original_db_path}.backup")
        
        shutil.copy(self.test_db_path, self.original_db_path)
        print("✅ Test database setup complete")
    
    def create_test_database(self):
        """Create a new test database with schema."""
        print("📊 Creating new test database...")
        
        # Run database initialization
        from database import init_db, create_views
        
        # Initialize with test database
        os.environ["DATABASE_URL"] = f"sqlite:///{self.test_db_path}"
        init_db()
        create_views()
        
        print("✅ Test database schema created")
    
    def populate_test_data(self):
        """Add test data to database."""
        print("📝 Adding test data...")
        
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        try:
            # Test users
            test_users = [
                ("Test Admin", "admin@test.com", "$2b$12$hashedpassword", 1, 1, 1),  # admin
                ("Test Member", "member@test.com", "$2b$12$hashedpassword", 1, 0, 1),  # member
                ("Test Guest", "guest@test.com", "$2b$12$hashedpassword", 0, 0, 1),   # guest
            ]
            
            cursor.executemany("""
                INSERT OR IGNORE INTO anglers (name, email, password, member, is_admin, active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, test_users)
            
            # Test events
            test_events = [
                ("2025-01-15", 2025, "January Tournament", "sabc_tournament", "Monthly tournament"),
                ("2025-02-15", 2025, "February Tournament", "sabc_tournament", "Monthly tournament"),
                ("2025-07-04", 2025, "Independence Day", "federal_holiday", "Federal Holiday"),
            ]
            
            cursor.executemany("""
                INSERT OR IGNORE INTO events (date, year, name, event_type, description)
                VALUES (?, ?, ?, ?, ?)
            """, test_events)
            
            # Test news
            test_news = [
                ("Welcome to Testing", "This is a test news item", 1, 1, 0),
                ("Draft News", "This is a draft news item", 1, 0, 1),
            ]
            
            cursor.executemany("""
                INSERT OR IGNORE INTO news (title, content, author_id, published, priority)
                VALUES (?, ?, ?, ?, ?)
            """, test_news)
            
            conn.commit()
            print("✅ Test data added")
            
        except Exception as e:
            print(f"❌ Error adding test data: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def start_test_server(self):
        """Start the application server for testing."""
        print("🚀 Starting test server...")
        
        try:
            # Start FastAPI server in background
            self.app_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", "app:app",
                "--host", "127.0.0.1",
                "--port", "8000",
                "--log-level", "error"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for server to start
            import time
            time.sleep(2)
            
            # Test if server is running
            import requests
            try:
                response = requests.get("http://127.0.0.1:8000/", timeout=5)
                print("✅ Test server started successfully")
                return True
            except requests.exceptions.RequestException:
                print("❌ Failed to start test server")
                return False
                
        except Exception as e:
            print(f"❌ Error starting server: {e}")
            return False
    
    def run_backend_tests(self, test_filter=""):
        """Run backend/API tests."""
        print("🧪 Running backend tests...")
        
        try:
            cmd = [
                "python", "-m", "pytest", 
                "test_backend.py",
                "-v",
                "--tb=short",
                "--cov=app",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--html=backend_test_report.html",
                "--junit-xml=backend_results.xml"
            ]
            
            if test_filter:
                cmd.extend(["-k", test_filter])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Parse results
            if result.returncode == 0:
                print("✅ Backend tests passed")
                self.test_results["backend"]["passed"] = self.parse_test_count(result.stdout, "passed")
            else:
                print("❌ Backend tests failed")
                self.test_results["backend"]["failed"] = self.parse_test_count(result.stdout, "failed")
                self.test_results["backend"]["errors"].append(result.stderr)
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ Error running backend tests: {e}")
            return False
    
    def run_frontend_tests(self, test_filter="", headless=True):
        """Run frontend/UI tests."""
        print("🖥️  Running frontend tests...")
        
        try:
            # Install playwright browsers if needed
            subprocess.run(["python", "-m", "playwright", "install", "chromium"], 
                         capture_output=True)
            
            cmd = [
                "python", "-m", "pytest",
                "test_frontend.py",
                "-v",
                "--tb=short",
                "--html=frontend_test_report.html",
                "--junit-xml=frontend_results.xml"
            ]
            
            if headless:
                cmd.extend(["--headed"])  # Remove for headless
            
            if test_filter:
                cmd.extend(["-k", test_filter])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Parse results
            if result.returncode == 0:
                print("✅ Frontend tests passed")
                self.test_results["frontend"]["passed"] = self.parse_test_count(result.stdout, "passed")
            else:
                print("❌ Frontend tests failed")
                self.test_results["frontend"]["failed"] = self.parse_test_count(result.stdout, "failed")
                self.test_results["frontend"]["errors"].append(result.stderr)
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("⏰ Frontend tests timed out")
            return False
        except Exception as e:
            print(f"❌ Error running frontend tests: {e}")
            return False
    
    def parse_test_count(self, output, status):
        """Parse test count from pytest output."""
        import re
        
        patterns = {
            "passed": r"(\d+) passed",
            "failed": r"(\d+) failed",
            "error": r"(\d+) error"
        }
        
        pattern = patterns.get(status, patterns["passed"])
        match = re.search(pattern, output)
        return int(match.group(1)) if match else 0
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        print("📊 Generating test report...")
        
        report = f"""
# SABC Test Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Backend Tests: {self.test_results['backend']['passed']} passed, {self.test_results['backend']['failed']} failed
- Frontend Tests: {self.test_results['frontend']['passed']} passed, {self.test_results['frontend']['failed']} failed
- Coverage: {self.test_results['coverage']['percentage']}%

## Backend Results
✅ Passed: {self.test_results['backend']['passed']}
❌ Failed: {self.test_results['backend']['failed']}

## Frontend Results  
✅ Passed: {self.test_results['frontend']['passed']}
❌ Failed: {self.test_results['frontend']['failed']}

## Files Generated
- `htmlcov/index.html` - Coverage report
- `backend_test_report.html` - Backend test details
- `frontend_test_report.html` - Frontend test details
- `backend_results.xml` - JUnit XML for CI/CD
- `frontend_results.xml` - JUnit XML for CI/CD

## Errors
{chr(10).join(self.test_results['backend']['errors'] + self.test_results['frontend']['errors'])}
"""
        
        with open("test_report.md", "w") as f:
            f.write(report)
        
        print("✅ Test report saved to test_report.md")
    
    def cleanup(self):
        """Clean up test environment."""
        print("🧹 Cleaning up...")
        
        # Stop server
        if self.app_process:
            self.app_process.terminate()
            self.app_process.wait()
        
        # Restore original database
        if Path(f"{self.original_db_path}.backup").exists():
            if Path(self.original_db_path).exists():
                os.remove(self.original_db_path)
            shutil.move(f"{self.original_db_path}.backup", self.original_db_path)
        
        # Remove test database
        if self.test_db_path and Path(self.test_db_path).exists():
            shutil.rmtree(self.test_db_path.parent)
        
        print("✅ Cleanup complete")
    
    def run_all_tests(self, backend_only=False, frontend_only=False, 
                      test_filter="", headless=True):
        """Run complete test suite."""
        print("🏁 Starting SABC Test Suite")
        print("=" * 50)
        
        success = True
        
        try:
            # Setup
            self.setup_test_database()
            
            if not frontend_only:
                # Backend tests don't need server
                if not self.run_backend_tests(test_filter):
                    success = False
            
            if not backend_only:
                # Start server for frontend tests
                if self.start_test_server():
                    if not self.run_frontend_tests(test_filter, headless):
                        success = False
                else:
                    print("❌ Could not start server for frontend tests")
                    success = False
            
            # Generate report
            self.generate_test_report()
            
            print("=" * 50)
            if success:
                print("🎉 All tests completed successfully!")
            else:
                print("❌ Some tests failed. Check reports for details.")
                
            return success
            
        except KeyboardInterrupt:
            print("\n⚠️  Tests interrupted by user")
            return False
        except Exception as e:
            print(f"❌ Test suite error: {e}")
            return False
        finally:
            self.cleanup()


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="SABC Application Test Suite")
    parser.add_argument("--backend-only", action="store_true", 
                       help="Run only backend tests")
    parser.add_argument("--frontend-only", action="store_true", 
                       help="Run only frontend tests")
    parser.add_argument("--filter", "-k", default="", 
                       help="Filter tests by name pattern")
    parser.add_argument("--headed", action="store_true",
                       help="Run frontend tests in headed mode (show browser)")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick test subset only")
    
    args = parser.parse_args()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n⚠️  Test interrupted")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create test runner
    runner = TestRunner()
    
    # Run tests
    success = runner.run_all_tests(
        backend_only=args.backend_only,
        frontend_only=args.frontend_only,
        test_filter=args.filter,
        headless=not args.headed
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()