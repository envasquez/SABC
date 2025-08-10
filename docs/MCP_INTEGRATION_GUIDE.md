# MCP (Model Context Protocol) Integration Guide for SABC

This guide covers available MCP tools in Claude Code and how to configure additional services for enhanced development workflow.

## Currently Available MCP Tools in Claude Code

Based on the documentation, I have access to several built-in tools, but specific third-party MCP integrations would need to be configured.

### Built-in Claude Code Tools
- **File Operations**: Read, Write, Edit, MultiEdit, Glob, LS
- **Code Execution**: Bash, NotebookEdit  
- **Web Operations**: WebFetch, WebSearch
- **Development**: Task (agent delegation), TodoWrite
- **Project Management**: ExitPlanMode

### Available Third-Party MCP Services

The following MCP services can be configured:

#### **Development & DevOps**
- **Sentry**: Error monitoring and debugging
- **Socket**: Security scanning and vulnerability detection
- **GitHub**: Repository management and CI/CD
- **GitLab**: Alternative repository and pipeline management

#### **Project Management** 
- **Asana**: Task and project tracking
- **Linear**: Issue tracking and project management  
- **Notion**: Documentation and knowledge management
- **Jira**: Enterprise project management

#### **Business & Commerce**
- **PayPal**: Payment processing integration
- **Stripe**: Payment and subscription management
- **Square**: Point of sale and payment systems

#### **Design & Content**
- **Figma**: Design collaboration and prototyping
- **invideo**: Video content creation

#### **Databases & Analytics**
- Various database connectors (specific ones not detailed in docs)
- Analytics and reporting tools

## Configuring MCP Services for SABC

### 1. Assessment of Useful MCP Services for SABC

Given our production readiness goals, these MCP services would be most valuable:

#### **High Priority**
```bash
# Sentry - Critical for production error monitoring
claude mcp add --transport sse sentry https://mcp.sentry.dev/sse

# GitHub - For automated repository management
claude mcp add --transport stdio github /path/to/github-mcp-server

# Linear or Asana - For project management integration
claude mcp add --transport http linear https://api.linear.app/mcp
```

#### **Medium Priority**
```bash  
# Socket - For security vulnerability scanning
claude mcp add --transport http socket https://socket.dev/api/mcp

# Notion - For documentation management
claude mcp add --transport sse notion https://api.notion.com/mcp
```

### 2. Configuration Methods

#### **Local stdio servers**
For tools that run as local processes:

```bash
# Example: Local GitHub MCP server
claude mcp add --transport stdio github-local \
  --command "npx @modelcontextprotocol/github-server" \
  --args "--token $GITHUB_TOKEN"
```

#### **Remote SSE (Server-Sent Events) servers**
For cloud-based services with real-time updates:

```bash
# Example: Sentry integration
claude mcp add --transport sse sentry \
  --url "https://mcp.sentry.dev/sse" \
  --auth-token "$SENTRY_AUTH_TOKEN"
```

#### **Remote HTTP servers**
For standard REST API integrations:

```bash
# Example: Linear integration
claude mcp add --transport http linear \
  --url "https://api.linear.app/mcp" \
  --auth-header "Authorization: Bearer $LINEAR_TOKEN"
```

### 3. Configuration Scopes

#### **Project-level** (Recommended for SABC)
```bash
# Configure for the SABC project specifically
cd /path/to/SABC
claude mcp add --scope project sentry https://mcp.sentry.dev/sse
```

#### **User-level** (For cross-project tools)
```bash
# Configure for all your projects
claude mcp add --scope user github /path/to/github-server
```

## Recommended MCP Setup for SABC Production Readiness

### 1. Error Monitoring Integration
```bash
# Set up Sentry for production error tracking
export SENTRY_DSN="your-sentry-dsn"
export SENTRY_ORG="south-austin-bass-club"
export SENTRY_PROJECT="sabc-django"

claude mcp add --transport sse sentry-prod \
  --url "https://mcp.sentry.dev/sse" \
  --config '{"dsn": "'$SENTRY_DSN'", "org": "'$SENTRY_ORG'", "project": "'$SENTRY_PROJECT'"}'
```

### 2. GitHub Integration for CI/CD
```bash
# GitHub integration for automated workflows
export GITHUB_TOKEN="your-github-token"
export GITHUB_REPO="envasquez/SABC"

claude mcp add --transport stdio github-sabc \
  --command "github-mcp-server" \
  --config '{"token": "'$GITHUB_TOKEN'", "repo": "'$GITHUB_REPO'"}'
```

### 3. Project Management Integration
```bash
# Linear for issue tracking (if you use Linear)
export LINEAR_TOKEN="your-linear-token"
export LINEAR_TEAM="sabc-development"

claude mcp add --transport http linear-sabc \
  --url "https://api.linear.app/mcp" \
  --config '{"token": "'$LINEAR_TOKEN'", "team": "'$LINEAR_TEAM'"}'
```

## Creating Custom MCP Services for SABC

### 1. Database Monitoring MCP Service
Create a custom MCP server for PostgreSQL monitoring:

```python
# custom-mcp-servers/sabc-db-monitor.py
import json
import sys
from mcp import Server
import psycopg2

app = Server("sabc-db-monitor")

@app.tool()
def check_database_health():
    """Check SABC database health and performance"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            database=os.getenv('POSTGRES_DB'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD')
        )
        cursor = conn.cursor()
        
        # Check database size
        cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        db_size = cursor.fetchone()[0]
        
        # Check slow queries
        cursor.execute("""
            SELECT query, mean_time, calls 
            FROM pg_stat_statements 
            WHERE mean_time > 1000 
            ORDER BY mean_time DESC LIMIT 5
        """)
        slow_queries = cursor.fetchall()
        
        return {
            "status": "healthy",
            "database_size": db_size,
            "slow_queries": slow_queries
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    app.run(transport="stdio")
```

### 2. Tournament Statistics MCP Service
```python  
# custom-mcp-servers/sabc-tournament-stats.py
import os
import django
from mcp import Server

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sabc.settings')
django.setup()

from tournaments.models import Tournament, Result

app = Server("sabc-tournament-stats")

@app.tool()
def get_tournament_analytics(year: int = None):
    """Get comprehensive tournament statistics"""
    tournaments = Tournament.objects.all()
    if year:
        tournaments = tournaments.filter(event__year=year)
    
    stats = {
        "total_tournaments": tournaments.count(),
        "completed_tournaments": tournaments.filter(complete=True).count(),
        "total_participants": Result.objects.filter(
            tournament__in=tournaments
        ).values('angler').distinct().count(),
        "average_participants_per_tournament": Result.objects.filter(
            tournament__in=tournaments
        ).count() / tournaments.count() if tournaments.count() > 0 else 0
    }
    
    return stats

if __name__ == "__main__":
    app.run(transport="stdio")
```

### 3. Register Custom MCP Services
```bash
# Register the custom database monitor
claude mcp add --transport stdio sabc-db-monitor \
  --command "python custom-mcp-servers/sabc-db-monitor.py" \
  --scope project

# Register the tournament statistics service
claude mcp add --transport stdio sabc-tournament-stats \
  --command "python custom-mcp-servers/sabc-tournament-stats.py" \
  --scope project
```

## Security Considerations

### 1. Token Management
```bash
# Use environment variables for sensitive data
export SENTRY_AUTH_TOKEN="your-token"
export GITHUB_TOKEN="your-token"
export LINEAR_TOKEN="your-token"

# Or use a secure credential store
claude mcp add --auth-provider "system-keychain" sentry
```

### 2. Network Security
```bash
# Restrict MCP access to specific networks
claude mcp add --transport http secure-service \
  --url "https://internal-api.company.com/mcp" \
  --network-policy "internal-only"
```

### 3. Permission Scoping
```bash
# Limit MCP permissions to specific operations
claude mcp add --permissions "read-only" monitoring-service
claude mcp add --permissions "write:issues,read:repo" github-service
```

## Integration with Nix Development Environment

Add MCP configuration to your Nix shell:

```nix
# In flake.nix, add to shellHook:
shellHook = ''
  # ... existing shellHook content ...
  
  # Configure MCP services for development
  if command -v claude >/dev/null 2>&1; then
    echo "🔌 Configuring MCP services..."
    
    # Only add if not already configured
    if ! claude mcp list | grep -q "sabc-dev-db"; then
      claude mcp add --transport stdio sabc-dev-db \
        --command "python scripts/mcp-db-monitor.py" \
        --scope project
    fi
  fi
'';
```

## Usage Examples

Once MCP services are configured, you can interact with them through Claude Code:

### 1. Monitor Database Performance
"Check the database health and show any slow queries"

### 2. Create GitHub Issues  
"Create a GitHub issue for the authentication vulnerability we found in polls/views.py"

### 3. Update Project Management
"Update our Linear ticket about production readiness with the current status"

### 4. Error Analysis
"Show me the latest errors from Sentry for the production SABC application"

## Troubleshooting MCP Configuration

### 1. List Configured Services
```bash
claude mcp list
```

### 2. Test Service Connection
```bash
claude mcp test sentry-prod
```

### 3. Remove Misconfigured Service
```bash
claude mcp remove sentry-prod
```

### 4. View Service Logs
```bash
claude mcp logs sabc-db-monitor
```

## Next Steps

1. **Evaluate MCP Services**: Determine which services align with SABC's production readiness goals
2. **Set Up Core Services**: Start with Sentry and GitHub integrations
3. **Create Custom Services**: Build SABC-specific MCP tools for database and tournament monitoring
4. **Integration Testing**: Ensure MCP services work with the Nix development environment
5. **Documentation**: Document MCP workflows for the development team

---

*This integration will enhance development productivity by providing direct access to external services and custom tools through Claude Code's unified interface.*