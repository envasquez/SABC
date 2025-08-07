# SABC Nix Development Environment

This guide helps you transition from the Docker devcontainer to a Nix-based development environment for better reproducibility and performance.

## Why Nix over Devcontainer?

- **Performance**: No container overhead, native speed
- **Reproducibility**: Exact same environment across all developers
- **Isolation**: Dependencies don't pollute your system
- **Flexibility**: Easy to customize and extend
- **Cross-platform**: Works on Linux, macOS, and Windows (WSL)

## Prerequisites

### 1. Install Nix
```bash
# Multi-user installation (recommended)
curl -L https://nixos.org/nix/install | sh -s -- --daemon

# Or single-user installation
curl -L https://nixos.org/nix/install | sh

# Restart your shell or source the profile
source /nix/var/nix/profiles/default/etc/profile.d/nix.sh
```

### 2. Enable Flakes (Recommended)
```bash
# Add to ~/.config/nix/nix.conf (create if needed)
echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
```

### 3. Install Direnv (Optional but Recommended)
```bash
# macOS
brew install direnv

# Ubuntu/Debian
apt install direnv

# Or via Nix
nix profile install nixpkgs#direnv

# Add to your shell rc file (~/.bashrc, ~/.zshrc)
eval "$(direnv hook bash)"  # for bash
eval "$(direnv hook zsh)"   # for zsh
```

## Quick Start

### Option 1: With Flakes + Direnv (Recommended)
```bash
cd /path/to/SABC
direnv allow  # This will automatically enter the dev environment
start-db      # Start PostgreSQL
dev-server    # Start Django development server
```

### Option 2: With Flakes Only
```bash
cd /path/to/SABC
nix develop   # Enter the development shell
start-db      # Start PostgreSQL
dev-server    # Start Django development server
```

### Option 3: Legacy Nix (Without Flakes)
```bash
cd /path/to/SABC
nix-shell     # Enter the development shell
# Manual setup required (see shell output)
```

## Available Commands

Once in the Nix shell, you have access to these custom commands:

- **`start-db`**: Initialize and start PostgreSQL database
- **`stop-db`**: Stop PostgreSQL database
- **`dev-server`**: Start Django development server with proper environment
- **`run-tests`**: Run the complete test suite with coverage

## Development Workflow

### 1. Database Setup (First Time)
```bash
start-db  # This will initialize and start PostgreSQL automatically
```

### 2. Django Setup
```bash
dev-server  # This will run migrations and start the server
```

### 3. Running Tests
```bash
run-tests  # Runs pytest with coverage reporting
```

### 4. Code Quality
```bash
# Format code
ruff format .

# Check code quality
ruff check .

# Type checking
pyright
```

## Environment Variables

The development environment automatically sets up:

```bash
# Database
PGDATA=$PWD/.nix-postgresql
PGHOST=localhost
PGPORT=5432
PGDATABASE=sabc
PGUSER=$USER

# Django
PYTHONPATH=$PWD/sabc
DJANGO_SETTINGS_MODULE=sabc.settings
DJANGO_DEBUG=1
```

Additional variables can be set in `.env.dev` (automatically created).

## Troubleshooting

### Database Issues
```bash
# Reset database
stop-db
rm -rf .nix-postgresql
start-db
```

### Python Dependencies
```bash
# Update dependencies in flake.nix, then
nix flake update  # Update flake.lock
nix develop --reload-cache  # Reload the environment
```

### Port Conflicts
```bash
# Check what's using port 5432
lsof -i :5432

# Or use a different port
export PGPORT=5433
start-db
```

## Customizing the Environment

### Adding Python Packages
Edit `flake.nix` and add packages to the `pythonEnv` section:

```nix
pythonEnv = python.withPackages (ps: with ps; [
  # existing packages...
  your-new-package
]);
```

### Adding System Dependencies
Add to the `devPackages` list in `flake.nix`:

```nix
devPackages = with pkgs; [
  # existing packages...
  your-new-system-package
];
```

### Custom Shell Commands
Add new commands to the `flake.nix` let binding:

```nix
myCommand = pkgs.writeShellScriptBin "my-command" ''
  echo "Custom command"
  # Your script here
'';
```

## Migration from Devcontainer

### 1. Remove Devcontainer Files
```bash
rm -rf .devcontainer
```

### 2. Update Documentation
Update any references to devcontainer in:
- README.md
- CONTRIBUTING.md
- CI/CD configurations

### 3. Update VS Code Settings
Create/update `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "./result/bin/python",
  "python.terminal.activateEnvironment": false
}
```

## IDE Integration

### VS Code
1. Install the Nix IDE extension
2. Set Python interpreter to the Nix environment
3. Configure the terminal to use `nix develop`

### PyCharm
1. Configure Python interpreter: `which python` (from inside nix-shell)
2. Set project root to include the Nix shell environment

## Performance Tips

1. **Use Direnv**: Automatically enters/exits environment
2. **Pin Nixpkgs**: Use a specific commit hash for consistency
3. **Use Binary Cache**: Add Cachix for faster dependency downloads
4. **Garbage Collection**: Run `nix-collect-garbage -d` periodically

## Comparison: Devcontainer vs Nix

| Feature | Devcontainer | Nix |
|---------|-------------|-----|
| Performance | Container overhead | Native speed |
| Disk Usage | Images + containers | Shared store |
| Reproducibility | Good | Excellent |
| Network | Port forwarding | Direct access |
| Integration | VS Code focused | Universal |
| Learning Curve | Easy | Moderate |

## Next Steps

1. Try the new development environment
2. Update the CI/CD to use Nix for consistency
3. Consider using Nix for production deployments
4. Explore advanced Nix features like overlays and modules

## Resources

- [Nix Manual](https://nixos.org/manual/nix/stable/)
- [Nix Pills](https://nixos.org/guides/nix-pills/) - Great tutorial series
- [Nix Package Search](https://search.nixos.org/packages)
- [Direnv Documentation](https://direnv.net/)

---

*Need help? Check the Nix community resources or ask in the project's discussion board.*