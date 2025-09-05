{
  description = "SABC FastAPI - Minimal Bass Club Tournament App";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowBroken = true;
        };

        python = pkgs.python311;

        # Minimal dependencies for FastAPI + SQLite
        pythonEnv = python.withPackages (ps: with ps; [
          # Core web framework
          fastapi
          uvicorn
          jinja2
          python-multipart  # for form handling
          itsdangerous  # for session middleware
          bcrypt  # for password hashing

          # Database
          sqlalchemy
          aiosqlite  # async SQLite support

          # Development tools
          pytest
          pytest-asyncio
          ruff
          mypy

          # Utilities
          pydantic
          pyyaml  # for config/data loading

          # Testing dependencies
          pytest-cov
          pytest-html
          pytest-xdist  # for parallel testing
          httpx  # for API testing
          playwright  # for frontend testing
        ]);

        devPackages = with pkgs; [
          # Development tools
          git
          sqlite
          curl

          # Optional: for database inspection
          sqlite-interactive
        ];

        # Development scripts
        startApp = pkgs.writeShellScriptBin "start-app" ''
          echo "🎣 Starting SABC FastAPI Application"
          echo "=================================="

          # Initialize database if it doesn't exist
          if [ ! -f "sabc.db" ]; then
            echo "Initializing SQLite database..."
            python -c "from database import init_db; init_db()"
          fi

          # Start FastAPI application
          echo "Starting FastAPI on http://localhost:8000"
          uvicorn app:app --reload --host 0.0.0.0 --port 8000
        '';

        runTests = pkgs.writeShellScriptBin "run-tests" ''
          echo "🧪 Running SABC Tests"
          echo "===================="
          python tests/run_tests.py
        '';

        testBackend = pkgs.writeShellScriptBin "test-backend" ''
          echo "🧪 Running Backend Tests"
          echo "======================="
          python tests/run_tests.py --backend-only
        '';

        testFrontend = pkgs.writeShellScriptBin "test-frontend" ''
          echo "🖥️  Running Frontend Tests"
          echo "========================"
          python tests/run_tests.py --frontend-only
        '';

        testIntegration = pkgs.writeShellScriptBin "test-integration" ''
          echo "🔗 Running Integration Tests"
          echo "==========================="
          python -m pytest tests/test_integration.py -v -m integration
        '';

        testQuick = pkgs.writeShellScriptBin "test-quick" ''
          echo "⚡ Running Quick Tests"
          echo "====================="
          python tests/run_tests.py --filter "not slow"
        '';

        testCoverage = pkgs.writeShellScriptBin "test-coverage" ''
          echo "📊 Generating Coverage Report"
          echo "============================"
          python -m pytest tests/test_backend.py --cov=app --cov-report=html --cov-report=term
          echo "📁 Coverage report: htmlcov/index.html"
        '';

        cleanTests = pkgs.writeShellScriptBin "clean-tests" ''
          echo "🧹 Cleaning Test Artifacts"
          echo "========================="
          rm -rf htmlcov/
          rm -rf .pytest_cache/
          rm -rf __pycache__/
          rm -rf .coverage
          rm -f *.xml
          rm -f *_test_report.html
          rm -f test_report.md
          echo "✅ Cleanup complete"
        '';

        checkCode = pkgs.writeShellScriptBin "check-code" ''
          echo "🔍 Running Code Quality Checks"
          echo "=============================="

          echo "Running Ruff (linting)..."
          ruff check .

          echo "Running MyPy (type checking)..."
          mypy . --ignore-missing-imports

          echo "Code quality checks complete!"
        '';

        formatCode = pkgs.writeShellScriptBin "format-code" ''
          echo "🎨 Formatting Python Code"
          echo "========================="

          echo "Running Ruff formatter..."
          ruff format .

          echo "Auto-fixing linting issues..."
          ruff check . --fix --unsafe-fixes

          echo "Code formatting complete!"
        '';

        setupDb = pkgs.writeShellScriptBin "setup-db" ''
          echo "🗄️  Setting up SABC Database"
          echo "==========================="

          if [ -f "sabc.db" ]; then
            echo "Database already exists. Use 'reset-db' to recreate."
            exit 1
          fi

          python -c "
from database import init_db, create_views
print('Creating database schema...')
init_db()
print('Creating database views...')
create_views()
print('Database setup complete!')
"
        '';

        resetDb = pkgs.writeShellScriptBin "reset-db" ''
          echo "🔄 Resetting SABC Database"
          echo "========================="

          if [ -f "sabc.db" ]; then
            rm sabc.db
            echo "Removed existing database."
          fi

          setup-db
        '';

        deployApp = pkgs.writeShellScriptBin "deploy-app" ''
          echo "🚀 Deploying SABC Application"
          echo "============================"

          # Run quality checks first
          check-code

          # Run tests
          run-tests

          echo "All checks passed! Ready for deployment."
          echo "Run: 'uvicorn app:app --host 0.0.0.0 --port 80' in production"
        '';

      in {
        devShells.default = pkgs.mkShell {
          name = "sabc-fastapi";

          buildInputs = [ pythonEnv ] ++ devPackages ++ [
            startApp
            runTests
            testBackend
            testFrontend
            testIntegration
            testQuick
            testCoverage
            cleanTests
            checkCode
            formatCode
            setupDb
            resetDb
            deployApp
          ];

          shellHook = ''
            echo "🎣 SABC FastAPI Development Environment"
            echo "======================================"
            echo ""
            echo "📦 Technology Stack:"
            echo "  • FastAPI ${python.pkgs.fastapi.version}"
            echo "  • Python ${python.version}"
            echo "  • SQLite ${pkgs.sqlite.version}"
            echo "  • SQLAlchemy ${python.pkgs.sqlalchemy.version}"
            echo ""
            echo "🚀 Available commands:"
            echo "  start-app        - Start FastAPI development server"
            echo "  setup-db         - Initialize database with schema and views"
            echo "  reset-db         - Reset database (delete and recreate)"
            echo ""
            echo "🧪 Testing commands:"
            echo "  run-tests        - Run complete test suite"
            echo "  test-backend     - Run backend tests only"
            echo "  test-frontend    - Run frontend tests only"
            echo "  test-integration - Run integration tests"
            echo "  test-quick       - Run quick test subset"
            echo "  test-coverage    - Generate coverage report"
            echo "  clean-tests      - Clean test artifacts"
            echo ""
            echo "🔧 Development commands:"
            echo "  check-code       - Run linting and type checking"
            echo "  format-code      - Auto-format Python code with ruff"
            echo "  deploy-app       - Run all checks for deployment"
            echo ""
            echo "💡 Quick start:"
            echo "  1. setup-db     # First time only"
            echo "  2. start-app    # Start development server"
            echo ""
            echo "🌐 App will be available at: http://localhost:8000"
            echo ""
          '';

          # Environment variables
          PYTHONPATH = ".";
          SABC_ENV = "development";
          SABC_DATABASE_URL = "sqlite:///sabc.db";
        };

        # Package the application for production
        packages.default = pkgs.python311Packages.buildPythonPackage {
          pname = "sabc-fastapi";
          version = "1.0.0";

          src = ./.;

          propagatedBuildInputs = with pkgs.python311Packages; [
            fastapi
            uvicorn
            jinja2
            sqlalchemy
            aiosqlite
            pydantic
            pyyaml
          ];

          # Skip tests for package build
          doCheck = false;

          meta = {
            description = "South Austin Bass Club Tournament Management System";
            license = "MIT";
          };
        };
      });
}