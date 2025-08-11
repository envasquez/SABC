# SABC GitHub Actions CI/CD Pipeline

This directory contains the complete CI/CD pipeline for the South Austin Bass Club (SABC) Django application, implementing automated testing, security scanning, and deployment workflows.

## 🚀 Workflows Overview

### 1. **ci.yml** - Basic CI (Fast Check)
**Triggers**: Push to master/main/develop, Pull Requests
**Purpose**: Quick validation for fast feedback

- ✅ Code formatting check (ruff)
- ✅ Linting and type checking (ruff + pyright)
- ✅ Basic test suite execution
- 🔄 ~3-5 minutes execution time

### 2. **ci-enhanced.yml** - Comprehensive CI/CD
**Triggers**: Push to master/main/develop, Pull Requests
**Purpose**: Thorough testing with matrix strategy

**Features**:
- 🧪 **Matrix Testing**: Python 3.11 & 3.12 across unit/integration/performance tests
- 🔒 **Security Scanning**: Bandit, Trivy vulnerability scanning
- 📊 **Coverage Reporting**: Codecov integration with detailed coverage metrics
- 🗄️ **PostgreSQL Testing**: Real database testing environment
- 🏗️ **Build Validation**: Static file collection and deployment checks
- 📈 **Performance Testing**: Automated performance regression detection

### 3. **deploy.yml** - Production Deployment
**Triggers**: Push to master, Tagged releases, Manual dispatch
**Purpose**: Automated production deployment with safety checks

**Safety Features**:
- 🛡️ **Pre-deployment Backup**: Automatic database backup before deployment
- 🔄 **Automatic Rollback**: Rollback on deployment failure
- ✅ **Health Checks**: Post-deployment verification
- 📝 **Deployment Logging**: Comprehensive deployment tracking

### 4. **staging.yml** - Staging Environment
**Triggers**: Push to develop, PR labels
**Purpose**: Staging environment for testing changes

**Features**:
- 🚀 **Automatic Deployment**: Deploy develop branch to staging
- 🧪 **Smoke Testing**: Basic functionality verification
- 💬 **PR Comments**: Automatic staging URL comments on PRs

### 5. **maintenance.yml** - Automated Maintenance
**Triggers**: Weekly schedule, Manual dispatch
**Purpose**: Regular maintenance and health monitoring

**Tasks**:
- 📦 **Dependency Updates**: Automated dependency checking and updates
- 🔒 **Security Auditing**: Weekly security vulnerability scans
- ⚡ **Performance Monitoring**: Performance regression testing
- 🗄️ **Database Maintenance**: Database optimization recommendations

### 6. **codeql-analysis.yml** - Security Analysis
**Triggers**: Push, Pull Requests, Weekly schedule
**Purpose**: GitHub's CodeQL security analysis

## 📋 Required Secrets

Configure these secrets in your GitHub repository settings:

### Deployment Secrets
```
DEPLOY_HOST         # Your Digital Ocean droplet IP/domain
DEPLOY_USER         # SSH username for deployment
DEPLOY_SSH_KEY      # Private SSH key for deployment access
```

### Optional Secrets (for enhanced features)
```
CODECOV_TOKEN       # For coverage reporting integration
SLACK_WEBHOOK       # For deployment notifications (if added)
```

## 🔧 Environment Setup

### GitHub Environments
Create these environments in your repository settings:

1. **production**
   - Protection rules: Require review from CODEOWNERS
   - Deployment branches: master only
   - Environment secrets: deployment credentials

2. **staging** 
   - Protection rules: None (automatic deployment)
   - Deployment branches: develop
   - Environment secrets: staging credentials

### SSH Key Setup
1. Generate SSH key pair:
   ```bash
   ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key
   ```

2. Add public key to server:
   ```bash
   ssh-copy-id -i deploy_key.pub user@your-server.com
   ```

3. Add private key as GitHub secret `DEPLOY_SSH_KEY`

## 🎯 Workflow Execution Matrix

| Event | Basic CI | Enhanced CI | Deploy | Staging | Maintenance |
|-------|----------|-------------|---------|---------|-------------|
| Push to master | ✅ | ✅ | ✅ | ❌ | ❌ |
| Push to develop | ✅ | ✅ | ❌ | ✅ | ❌ |
| Pull Request | ✅ | ✅ | ❌ | ✅* | ❌ |
| Tagged release | ❌ | ❌ | ✅ | ❌ | ❌ |
| Weekly schedule | ❌ | ❌ | ❌ | ❌ | ✅ |
| Manual dispatch | ❌ | ❌ | ✅ | ✅ | ✅ |

\* Only when PR is labeled with "deploy-staging"

## 📊 Test Strategy

### Test Types
- **Unit Tests**: Fast, isolated component testing
- **Integration Tests**: Database and service integration
- **Performance Tests**: Query performance and load testing
- **Security Tests**: Vulnerability and security scanning
- **Smoke Tests**: Basic functionality verification

### Coverage Goals
- **Overall**: 80%+ code coverage
- **Service Layer**: 95%+ coverage (business logic)
- **Models**: 90%+ coverage
- **Views**: 70%+ coverage (UI layer)

## 🚀 Deployment Process

### Automatic Deployment (master branch)
1. Code pushed to master
2. Enhanced CI pipeline runs full test suite
3. Security scans complete successfully
4. Database backup created automatically
5. Application deployed with zero-downtime strategy
6. Health checks verify deployment
7. Rollback triggered automatically on failure

### Manual Deployment
1. Navigate to Actions → Deploy to Production
2. Click "Run workflow"
3. Select environment (production/staging)
4. Monitor deployment progress
5. Verify deployment success via health checks

## 🛠️ Development Workflow

### For Feature Development
1. Create feature branch from `develop`
2. Make changes and commit
3. Push to feature branch
4. Basic CI runs automatically
5. Create PR to `develop`
6. Enhanced CI runs comprehensive tests
7. Add "deploy-staging" label to test on staging
8. Merge to `develop` after review
9. Staging environment auto-deploys

### For Production Release
1. Create PR from `develop` to `master`
2. All CI pipelines must pass
3. Code review and approval required
4. Merge to `master`
5. Production deployment runs automatically
6. Monitor deployment and health checks

## 📈 Monitoring & Alerts

### Automatic Notifications
- ✅ **Success**: Deployment completion notifications
- ❌ **Failure**: Immediate alerts for failed deployments
- 🔄 **Rollback**: Automatic rollback notifications
- 📊 **Weekly Reports**: Maintenance and security summaries

### Manual Monitoring
- GitHub Actions tab for pipeline status
- Production server logs via SSH
- Application health checks: `/health/`
- Performance monitoring via logs

## 🔧 Troubleshooting

### Common Issues

**Tests failing in CI but pass locally**
- Check environment differences (Python version, dependencies)
- Verify database migrations are up to date
- Check for missing environment variables

**Deployment failures**
- Verify SSH credentials and connectivity
- Check disk space on deployment server
- Verify database connectivity
- Review deployment logs in Actions tab

**Performance test failures**
- Check if performance baseline needs updating
- Verify test database has sufficient data
- Review slow query logs

### Emergency Procedures

**Manual Rollback**
```bash
ssh user@server
cd ~/SABC_II/SABC
git log --oneline -5  # Find previous commit
git reset --hard COMMIT_HASH
sudo systemctl restart sabc-web
```

**Skip CI Checks** (emergency only)
- Add `[skip ci]` to commit message
- Use admin override for required checks
- Document reasoning in commit message

## 🎯 Next Steps

### Planned Enhancements
1. **Blue-Green Deployments**: Zero-downtime deployment strategy
2. **Canary Releases**: Gradual rollout for reduced risk
3. **Container Deployments**: Docker/Kubernetes integration
4. **Advanced Monitoring**: Prometheus/Grafana metrics
5. **Automated Performance Baselines**: Dynamic performance thresholds

### Configuration Files
- `.github/CODEOWNERS` - Code review assignments
- `.github/dependabot.yml` - Automated dependency updates
- `.github/issue_template/` - Issue templates
- `.github/pull_request_template.md` - PR templates

---

For questions or issues with the CI/CD pipeline, please create an issue in the repository or contact the development team.