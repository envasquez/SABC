# Legacy shell.nix for compatibility
# This provides the same environment as flake.nix for users without flakes enabled

{ pkgs ? import <nixpkgs> { config = { allowBroken = true; }; } }:

let
  python = pkgs.python311;
  
  pythonEnv = python.withPackages (ps: with ps; [
    # Core Django dependencies
    django
    psycopg2
    pillow
    pytz
    pyyaml
    requests
    
    # Development tools
    pytest
    pytest-django
    pytest-cov
    coverage
    ruff
    
    # Django extensions  
    django-extensions
    django-crispy-forms
    django-phonenumber-field
    django-tables2
    
    # Additional packages
    names
  ]);

in pkgs.mkShell {
  name = "sabc-dev-legacy";
  
  buildInputs = with pkgs; [
    pythonEnv
    postgresql_15
    gcc
    pkg-config
    libpq
    git
    gnumake
    curl
    docker
    docker-compose
    nodejs_20
    poetry
  ];
  
  shellHook = ''
    echo "🎣 SABC Django Development Environment (Legacy)"
    echo "=============================================="
    echo "Note: Consider upgrading to flake.nix for better reproducibility"
    echo ""
    
    # Set up PostgreSQL
    export PGDATA="$PWD/.nix-postgresql"
    export PGHOST="localhost"
    export PGPORT="5432"
    export PGDATABASE="sabc"
    export PGUSER="$USER"
    
    # Python/Django environment
    export PYTHONPATH="$PWD/sabc:$PYTHONPATH"
    export DJANGO_SETTINGS_MODULE="sabc.settings"
    
    echo "💡 Manual setup required:"
    echo "  1. Initialize DB: initdb --auth-host=trust --auth-local=trust"
    echo "  2. Start DB: pg_ctl -l $PGDATA/log start"  
    echo "  3. Create DB: createdb sabc"
    echo "  4. Run server: cd sabc && python manage.py runserver"
  '';
}