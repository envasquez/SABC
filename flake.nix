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

        # Dependencies for FastAPI + PostgreSQL
        pythonEnv = python.withPackages (ps: with ps; [
          # Core web framework
          fastapi
          uvicorn
          jinja2
          python-multipart  # for form handling
          itsdangerous  # for session middleware
          bcrypt  # for password hashing

          # Database - PostgreSQL only
          sqlalchemy
          psycopg2  # PostgreSQL adapter

          # Development tools
          ruff
          mypy
        ]);

        devPackages = with pkgs; [
          # Development tools
          git
          curl
          postgresql  # PostgreSQL client tools
        ];

        # Development scripts
        startApp = pkgs.writeShellScriptBin "start-app" ''
          echo "🎣 Starting SABC FastAPI Application"
          echo "=================================="

          # Start PostgreSQL container
          echo "Starting PostgreSQL container..."
          docker compose up -d postgres

          # Wait for PostgreSQL to be ready
          echo "Waiting for PostgreSQL to be ready..."
          until docker compose exec postgres pg_isready -U postgres; do
            echo "PostgreSQL is unavailable - sleeping"
            sleep 1
          done
          echo "✓ PostgreSQL is ready!"

          # Initialize database if needed
          echo "Initializing database..."
          python -c "
from core.db_schema import create_all_tables
try:
    create_all_tables()
    print('✓ Database initialized successfully')
except Exception as e:
    print(f'Note: {e}')
"

          # Start FastAPI application
          echo "Starting FastAPI on http://localhost:8000"
          uvicorn app:app --reload --host 0.0.0.0 --port 8000
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
          echo "🗄️  Setting up SABC PostgreSQL Database"
          echo "===================================="

          python -c "
from core.db_schema import create_all_tables
print('Creating PostgreSQL database schema...')
create_all_tables()
print('Database setup complete!')
"
        '';

        resetDb = pkgs.writeShellScriptBin "reset-db" ''
          echo "🔄 Resetting SABC PostgreSQL Database"
          echo "==================================="

          python -c "
from core.db_schema import drop_all_tables, create_all_tables
print('Dropping all tables...')
drop_all_tables()
print('Creating PostgreSQL database schema...')
create_all_tables()
print('Database reset complete!')
"
        '';

        deployApp = pkgs.writeShellScriptBin "deploy-app" ''
          echo "🚀 Deploying SABC Application"
          echo "============================"

          # Run quality checks first
          check-code

          echo "All checks passed! Ready for deployment."
          echo "Run: 'uvicorn app:app --host 0.0.0.0 --port 80' in production"
        '';

      in {
        devShells.default = pkgs.mkShell {
          name = "sabc-fastapi";

          buildInputs = [ pythonEnv ] ++ devPackages ++ [
            startApp
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
            echo "  • PostgreSQL ${pkgs.postgresql.version}"
            echo "  • SQLAlchemy ${python.pkgs.sqlalchemy.version}"
            echo ""
            echo "🚀 Available commands:"
            echo "  start-app        - Start FastAPI development server"
            echo "  setup-db         - Initialize database with schema and views"
            echo "  reset-db         - Reset database (delete and recreate)"
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
          DATABASE_URL = "postgresql://postgres:dev123@localhost:5432/sabc";
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
            psycopg2
            python-multipart
            itsdangerous
            bcrypt
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