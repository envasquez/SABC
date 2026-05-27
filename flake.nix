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

        python = pkgs.python312;

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

          # Data processing and validation
          pandas  # Data manipulation for points calculation
          pydantic  # Data validation and parsing
          email-validator  # Required for Pydantic EmailStr

          # Web scraping for data ingestion
          requests  # HTTP client for API/web requests
          beautifulsoup4  # HTML parsing for tournament data import

          # Image processing
          pillow  # For photo gallery thumbnails and EXIF handling

          # Markdown rendering
          markdown  # For rendering markdown content as HTML

          # Monitoring & observability (hard dependencies)
          sentry-sdk  # Error monitoring
          prometheus-client  # Metrics collection

          # Testing
          pytest
          pytest-cov
          pytest-xdist  # Parallel test execution (-n auto)
          httpx  # Required by FastAPI TestClient

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
          docker compose -f docker-compose.dev.yml up -d postgres

          # Wait for PostgreSQL to be ready
          echo "Waiting for PostgreSQL to be ready..."
          until docker compose -f docker-compose.dev.yml exec postgres pg_isready -U postgres; do
            echo "PostgreSQL is unavailable - sleeping"
            sleep 1
          done
          echo "✓ PostgreSQL is ready!"

          # Run database migrations if needed
          echo "Running database migrations..."
          alembic upgrade head
          echo "✓ Database migrations complete"

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
          # Schema is owned by Alembic — see docs/DATABASE_MIGRATIONS.md.
          alembic upgrade head
          echo "Database setup complete!"
        '';

        resetDb = pkgs.writeShellScriptBin "reset-db" ''
          echo "🔄 Resetting SABC PostgreSQL Database"
          echo "==================================="
          # Tear the schema down and rebuild it from Alembic migrations.
          # `alembic downgrade base` reverses every migration; `upgrade head`
          # reapplies them, giving the same end state as the original
          # drop-all/create-all without any non-migration code path.
          alembic downgrade base
          alembic upgrade head
          echo "Database reset complete!"
        '';

        deployApp = pkgs.writeShellScriptBin "deploy-app" ''
          echo "🚀 Deploying SABC Application"
          echo "============================"

          # Run quality checks first
          check-code

          echo "All checks passed! Ready for deployment."
          echo "Run: 'uvicorn app:app --host 0.0.0.0 --port 80' in production"
        '';

        runTests = pkgs.writeShellScriptBin "run-tests" ''
          echo "🧪 Running SABC Test Suite"
          echo "=========================="
          echo ""

          # Tests use file-based SQLite, configured in tests/conftest.py — no
          # external PostgreSQL is required. Clear any stale per-worker DB files
          # left behind by a previous (possibly interrupted) parallel run.
          rm -f test_sabc*.db test_sabc*.db-journal test_sabc*.db-wal test_sabc*.db-shm

          # Run pytest with any arguments passed
          if [ "$1" == "--coverage" ]; then
              shift
              echo "📊 Running tests with coverage..."
              pytest tests/ --ignore=tests/e2e --cov=core --cov=routes --cov-report=html --cov-report=term --cov-report=xml --cov-fail-under=70 "$@"
              echo ""
              echo "📄 Coverage report saved to: htmlcov/index.html"
          elif [ "$1" == "--smoke" ]; then
              shift
              echo "💨 Running smoke tests only..."
              pytest tests/test_routes_smoke.py "$@"
          elif [ "$1" == "--e2e" ]; then
              shift
              echo "🌐 Running Playwright end-to-end tests..."
              echo "   Requires the dev server running at http://localhost:8000."
              if ! curl -s -o /dev/null -w "" --max-time 2 http://localhost:8000/login; then
                  echo "❌ Dev server is not reachable at http://localhost:8000."
                  echo "   Start it in another terminal:  nix develop -c start-app"
                  exit 1
              fi
              npx playwright test "$@"
          elif [ "$1" == "--all" ]; then
              shift
              echo "🧪 Running Python tests..."
              pytest tests/ --ignore=tests/e2e "$@"
              echo ""
              echo "🌐 Running Playwright end-to-end tests..."
              if ! curl -s -o /dev/null -w "" --max-time 2 http://localhost:8000/login; then
                  echo "❌ Dev server is not reachable at http://localhost:8000."
                  echo "   Start it in another terminal:  nix develop -c start-app"
                  exit 1
              fi
              npx playwright test
          else
              echo "🧪 Running tests..."
              pytest tests/ --ignore=tests/e2e "$@"
          fi

          echo ""
          echo "✅ Tests complete!"
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
            runTests
          ];

          shellHook = ''
            # A few packages (slowapi, starlette-csrf, astral) are not reliably
            # available as nixpkgs attrs, so they are vendored into
            # .nix-python-packages (which is on PYTHONPATH below). This step
            # bootstraps them automatically and is idempotent: if the marker
            # file matches the current pin set, it is skipped on subsequent
            # `nix develop` invocations. Delete .nix-python-packages/.pip-marker
            # (or the whole dir) to force a reinstall.
            EXTRA_PIP_PKGS="starlette-csrf==3.0.0 slowapi==0.1.9 astral==3.2"
            PIP_MARKER=".nix-python-packages/.pip-marker"
            if [ "$(cat "$PIP_MARKER" 2>/dev/null)" != "$EXTRA_PIP_PKGS" ]; then
              echo "📦 Installing vendored pip packages into .nix-python-packages ..."
              if python3.12 -m pip install --quiet --target .nix-python-packages $EXTRA_PIP_PKGS; then
                echo "$EXTRA_PIP_PKGS" > "$PIP_MARKER"
                echo "✓ Vendored packages ready."
              else
                echo "⚠️  pip install failed — run manually:"
                echo "   python3.12 -m pip install --target .nix-python-packages $EXTRA_PIP_PKGS"
              fi
            fi

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
            echo "  run-tests        - Run test suite (--coverage for coverage report)"
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
          PYTHONPATH = ".:.nix-python-packages";
          SABC_ENV = "development";
          DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/sabc";
        };

        # Package the application for production
        packages.default = pkgs.python312Packages.buildPythonPackage {
          pname = "sabc-fastapi";
          version = "1.0.0";

          src = ./.;

          propagatedBuildInputs = with pkgs.python312Packages; [
            fastapi
            uvicorn
            jinja2
            sqlalchemy
            psycopg2
            python-multipart
            itsdangerous
            bcrypt
            pandas
            pydantic
            email-validator
            requests
            beautifulsoup4
            markdown
            sentry-sdk
            prometheus-client
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
