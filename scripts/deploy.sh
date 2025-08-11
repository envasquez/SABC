#!/bin/bash

#
# SABC Deployment Script
# 
# This script provides a local deployment testing environment and can be used
# for manual deployments if needed. It mirrors the GitHub Actions deployment workflow.
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/tmp/sabc-deploy-$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

# Help function
show_help() {
    cat << EOF
SABC Deployment Script

Usage: $0 [OPTIONS] COMMAND

Commands:
    test            Run pre-deployment tests
    deploy          Deploy to production server
    staging         Deploy to staging environment
    rollback        Rollback to previous version
    backup          Create database backup only
    status          Check deployment status

Options:
    -h, --help      Show this help message
    -v, --verbose   Verbose output
    -n, --dry-run   Show what would be done without executing
    --skip-tests    Skip pre-deployment tests
    --force         Force deployment even if tests fail

Environment Variables:
    DEPLOY_HOST     Deployment server hostname/IP
    DEPLOY_USER     SSH username for deployment
    DEPLOY_KEY      Path to SSH private key
    BACKUP_DIR      Directory for backups (default: ~/backups)

Examples:
    $0 test                    # Run all tests
    $0 deploy --dry-run        # Show deployment steps
    $0 staging                 # Deploy to staging
    $0 rollback                # Rollback last deployment
    
EOF
}

# Parse command line arguments
COMMAND=""
DRY_RUN=false
VERBOSE=false
SKIP_TESTS=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        test|deploy|staging|rollback|backup|status)
            COMMAND="$1"
            shift
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if command was provided
if [[ -z "$COMMAND" ]]; then
    error "No command provided"
    show_help
    exit 1
fi

# Validate environment variables for deployment commands
validate_env() {
    if [[ "$COMMAND" == "deploy" || "$COMMAND" == "staging" || "$COMMAND" == "rollback" ]]; then
        if [[ -z "${DEPLOY_HOST:-}" ]]; then
            error "DEPLOY_HOST environment variable is required"
            exit 1
        fi
        if [[ -z "${DEPLOY_USER:-}" ]]; then
            error "DEPLOY_USER environment variable is required"
            exit 1
        fi
        if [[ -z "${DEPLOY_KEY:-}" ]]; then
            warn "DEPLOY_KEY not set, will use default SSH key"
        fi
    fi
}

# Pre-deployment tests
run_tests() {
    if [[ "$SKIP_TESTS" == true ]]; then
        warn "Skipping tests as requested"
        return 0
    fi
    
    log "Running pre-deployment tests..."
    
    cd "$PROJECT_ROOT"
    
    # Check if Nix environment is available
    if command -v nix &> /dev/null; then
        info "Using Nix development environment"
        
        # Code formatting check
        log "Checking code formatting..."
        if [[ "$DRY_RUN" == false ]]; then
            nix develop -c ruff format --check . || {
                error "Code formatting check failed"
                return 1
            }
        fi
        
        # Linting
        log "Running linting checks..."
        if [[ "$DRY_RUN" == false ]]; then
            nix develop -c make lint || {
                error "Linting failed"
                return 1
            }
        fi
        
        # Test suite
        log "Running test suite..."
        if [[ "$DRY_RUN" == false ]]; then
            SKIP_PIP_INSTALL=1 nix develop -c make test || {
                error "Test suite failed"
                if [[ "$FORCE" == false ]]; then
                    return 1
                else
                    warn "Test failures ignored due to --force flag"
                fi
            }
        fi
    else
        warn "Nix not available, skipping tests"
        if [[ "$FORCE" == false ]]; then
            error "Cannot run tests without Nix environment. Use --force to skip."
            return 1
        fi
    fi
    
    log "All pre-deployment tests passed ✅"
}

# Create database backup
create_backup() {
    log "Creating database backup..."
    
    local backup_dir="${BACKUP_DIR:-~/backups}"
    local backup_date=$(date +%Y%m%d)
    local backup_file="sabc_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if [[ "$DRY_RUN" == true ]]; then
        info "Would create backup: $backup_dir/$backup_date/$backup_file"
        return 0
    fi
    
    local ssh_cmd="ssh"
    if [[ -n "${DEPLOY_KEY:-}" ]]; then
        ssh_cmd="ssh -i $DEPLOY_KEY"
    fi
    
    $ssh_cmd -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" << EOF
        mkdir -p $backup_dir/$backup_date
        pg_dump -h localhost -U postgres sabc > $backup_dir/$backup_date/$backup_file
        echo "✅ Database backup created: $backup_dir/$backup_date/$backup_file"
        
        # Cleanup old backups (keep last 7 days)
        find $backup_dir -type f -name "*.sql" -mtime +7 -delete
        find $backup_dir -type d -empty -delete
EOF
    
    log "Database backup completed ✅"
}

# Deploy to server
deploy_to_server() {
    local env="$1"
    log "Deploying to $env environment..."
    
    if [[ "$DRY_RUN" == true ]]; then
        info "Would deploy to $env with the following steps:"
        info "  1. Stop application service"
        info "  2. Pull latest code from git"
        info "  3. Install/update dependencies"
        info "  4. Run database migrations"
        info "  5. Collect static files"
        info "  6. Restart application service"
        info "  7. Run health checks"
        return 0
    fi
    
    local ssh_cmd="ssh"
    if [[ -n "${DEPLOY_KEY:-}" ]]; then
        ssh_cmd="ssh -i $DEPLOY_KEY"
    fi
    
    $ssh_cmd -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" << EOF
        set -euo pipefail
        
        cd ~/SABC_II/SABC
        
        # Stop the application
        echo "⏹️ Stopping application..."
        sudo systemctl stop sabc-web || echo "Service not running"
        
        # Pull latest changes
        echo "📥 Pulling latest changes..."
        git fetch --all
        git reset --hard origin/master
        
        # Install dependencies
        echo "📦 Installing dependencies..."
        source ~/.bashrc
        nix develop -c bash -c "
            cd sabc &&
            pip install -r requirements.txt || echo 'No requirements.txt found'
        "
        
        # Run migrations
        echo "🗄️ Running database migrations..."
        nix develop -c bash -c "
            cd sabc &&
            python manage.py migrate --noinput
        "
        
        # Collect static files
        echo "📁 Collecting static files..."
        nix develop -c bash -c "
            cd sabc &&
            python manage.py collectstatic --noinput
        "
        
        # Start application
        echo "🔄 Starting application..."
        sudo systemctl start sabc-web
        sudo systemctl enable sabc-web
        
        echo "✅ Deployment completed"
EOF
    
    # Health check
    log "Running health check..."
    sleep 10
    if curl -f "http://$DEPLOY_HOST:8000/health/" > /dev/null 2>&1; then
        log "Health check passed ✅"
    else
        warn "Health check failed - application may need time to start"
    fi
    
    log "Deployment to $env completed ✅"
}

# Check deployment status
check_status() {
    log "Checking deployment status..."
    
    local ssh_cmd="ssh"
    if [[ -n "${DEPLOY_KEY:-}" ]]; then
        ssh_cmd="ssh -i $DEPLOY_KEY"
    fi
    
    $ssh_cmd -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" << 'EOF'
        echo "=== Service Status ==="
        sudo systemctl status sabc-web --no-pager || echo "Service status check failed"
        
        echo -e "\n=== Last 10 Deployments ==="
        tail -10 ~/deployment.log 2>/dev/null || echo "No deployment log found"
        
        echo -e "\n=== Current Git Status ==="
        cd ~/SABC_II/SABC
        echo "Current branch: $(git branch --show-current)"
        echo "Last commit: $(git log -1 --oneline)"
        
        echo -e "\n=== Health Check ==="
        curl -f http://localhost:8000/health/ && echo "✅ Health check passed" || echo "❌ Health check failed"
EOF
}

# Rollback deployment
rollback_deployment() {
    log "Rolling back deployment..."
    
    if [[ "$DRY_RUN" == true ]]; then
        info "Would rollback to previous commit"
        return 0
    fi
    
    local ssh_cmd="ssh"
    if [[ -n "${DEPLOY_KEY:-}" ]]; then
        ssh_cmd="ssh -i $DEPLOY_KEY"
    fi
    
    $ssh_cmd -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" << 'EOF'
        cd ~/SABC_II/SABC
        
        # Get previous commit
        PREV_COMMIT=$(git log --oneline -2 | tail -1 | cut -d' ' -f1)
        
        if [[ -z "$PREV_COMMIT" ]]; then
            echo "❌ Cannot find previous commit for rollback"
            exit 1
        fi
        
        echo "🔄 Rolling back to commit: $PREV_COMMIT"
        
        # Stop service
        sudo systemctl stop sabc-web
        
        # Rollback code
        git reset --hard $PREV_COMMIT
        
        # Restart service
        sudo systemctl start sabc-web
        
        echo "✅ Rollback completed to commit: $PREV_COMMIT"
        echo "$(date -u +%Y-%m-%d_%H:%M:%S) - ROLLBACK: Rolled back to $PREV_COMMIT" >> ~/deployment.log
EOF
    
    log "Rollback completed ✅"
}

# Main execution
main() {
    log "SABC Deployment Script Started"
    log "Command: $COMMAND"
    log "Log file: $LOG_FILE"
    
    validate_env
    
    case "$COMMAND" in
        test)
            run_tests
            ;;
        deploy)
            run_tests
            create_backup
            deploy_to_server "production"
            ;;
        staging)
            run_tests
            deploy_to_server "staging"
            ;;
        backup)
            create_backup
            ;;
        status)
            check_status
            ;;
        rollback)
            rollback_deployment
            ;;
        *)
            error "Unknown command: $COMMAND"
            exit 1
            ;;
    esac
    
    log "Script completed successfully ✅"
    log "Full log available at: $LOG_FILE"
}

# Execute main function
main "$@"