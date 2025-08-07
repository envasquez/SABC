{
  description = "SABC Django Development Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config = {
            allowBroken = true;
          };
        };
        
        # Python with specific version
        python = pkgs.python311;
        
        # Python packages for development
        pythonEnv = python.withPackages (ps: with ps; [
          # Core Django dependencies
          django
          psycopg2
          pillow
          pytz
          pyyaml
          requests
          urllib3
          
          # Development tools
          pytest
          pytest-django
          pytest-cov
          coverage
          ruff
          
          # Django extensions
          django-crispy-forms
          crispy-bootstrap4
          django-phonenumber-field
          django-tables2
          
          # Additional packages
          names
        ]);

        # Development dependencies
        devPackages = with pkgs; [
          # Database
          postgresql_15
          
          # System dependencies
          gcc
          pkg-config
          libpq
          
          # Development tools
          git
          gnumake
          curl
          docker
          docker-compose
          pyright
          python.pkgs.pip
          
          # Optional: Node.js for frontend tooling
          nodejs_20
          
          # Poetry for dependency management (optional)
          poetry
        ];

        # Shell scripts for common tasks
        startDB = pkgs.writeShellScriptBin "start-db" ''
          # Initialize PostgreSQL if needed
          if [ ! -d "$PGDATA" ]; then
            echo "Initializing PostgreSQL database..."
            initdb --auth-host=trust --auth-local=trust
          fi
          
          # Start PostgreSQL
          pg_ctl -l "$PGDATA/log" start
          
          # Create database if it doesn't exist
          if ! psql -lqt | cut -d \| -f 1 | grep -qw sabc; then
            createdb sabc
            echo "Created database 'sabc'"
          fi
          
          echo "PostgreSQL is running on port 5432"
          echo "Database: sabc"
          echo "To stop: pg_ctl stop"
        '';
        
        stopDB = pkgs.writeShellScriptBin "stop-db" ''
          pg_ctl stop
        '';
        
        runTests = pkgs.writeShellScriptBin "run-tests" ''
          export UNITTEST=1
          export DJANGO_SETTINGS_MODULE="sabc.settings"
          cd sabc
          coverage run --branch --source=. -m pytest --capture=no -vv
          coverage report --show-missing
        '';
        
        devServer = pkgs.writeShellScriptBin "dev-server" ''
          export DJANGO_DEBUG=1
          export DJANGO_SECRET_KEY="dev-secret-key-change-in-production"
          export POSTGRES_DB="sabc"
          export POSTGRES_USER="$USER"
          export POSTGRES_PASSWORD=""
          cd sabc
          python manage.py migrate
          python manage.py runserver 0.0.0.0:8000
        '';

      in {
        devShells.default = pkgs.mkShell {
          name = "sabc-dev";
          
          buildInputs = [ pythonEnv ] ++ devPackages ++ [
            startDB
            stopDB  
            runTests
            devServer
          ];
          
          shellHook = ''
            echo "🎣 SABC Django Development Environment"
            echo "=================================="
            
            # Install betterforms via pip since it's not in nixpkgs
            if ! python -c "import betterforms" 2>/dev/null; then
              echo "Installing django-betterforms via pip..."
              pip install --user django-betterforms --break-system-packages
            fi
            
            # Ensure user-installed packages are in Python path
            export PYTHONPATH="$HOME/.local/lib/python3.11/site-packages:$PYTHONPATH"
            
            # Set up PostgreSQL data directory
            export PGDATA="$PWD/.nix-postgresql"
            export PGHOST="localhost"
            export PGPORT="5432"
            export PGDATABASE="sabc"
            export PGUSER="$USER"
            
            # Python/Django environment
            export PYTHONPATH="$PWD/sabc:$PYTHONPATH"
            export DJANGO_SETTINGS_MODULE="sabc.settings"
            
            echo "📦 Available commands:"
            echo "  start-db     - Start PostgreSQL database"
            echo "  stop-db      - Stop PostgreSQL database"  
            echo "  dev-server   - Start Django development server"
            echo "  run-tests    - Run test suite with coverage"
            echo ""
            echo "🔧 Development tools available:"
            echo "  Python ${python.version}"
            echo "  PostgreSQL ${pkgs.postgresql_15.version}"
            echo "  Django $(python -c 'import django; print(django.VERSION)' 2>/dev/null || echo 'not installed')"
            echo ""
            echo "💡 Quick start:"
            echo "  1. start-db"
            echo "  2. dev-server"
            echo ""
            
            # Create .env file template if it doesn't exist
            if [ ! -f .env.dev ]; then
              cat > .env.dev << EOF
# SABC Development Environment Variables
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=dev-secret-key-change-in-production
POSTGRES_DB=sabc
POSTGRES_USER=$USER
POSTGRES_PASSWORD=
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
EOF
              echo "📄 Created .env.dev template"
            fi
          '';
          
          # Environment variables for development
          DJANGO_SETTINGS_MODULE = "sabc.settings";
          PYTHONPATH = "$PWD/sabc";
        };
        
        # Package the application
        packages.default = pkgs.python311Packages.buildPythonPackage {
          pname = "sabc";
          version = "0.1.0";
          
          src = ./.;
          
          propagatedBuildInputs = with pkgs.python311Packages; [
            django
            psycopg2
            pillow
            pytz
            pyyaml
            requests
          ];
          
          # Skip tests for package build
          doCheck = false;
        };
      });
}