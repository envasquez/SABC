# SABC Database Backup & Recovery Strategy

## Overview

This document outlines the comprehensive backup and recovery strategy for the South Austin Bass Club (SABC) Django application database. It includes automated backup procedures, migration testing, and disaster recovery protocols.

## 🎯 Key Principles

1. **Safety First**: Every production operation must have a tested rollback plan
2. **Zero Data Loss**: Comprehensive backup coverage with integrity verification  
3. **Minimal Downtime**: Optimized procedures to minimize service interruption
4. **Automated Testing**: All migrations tested on production data copies before deployment

## 📁 Backup Scripts Location

All backup scripts are located in `/scripts/` directory:
- `backup_database.sh` - Creates timestamped database backups
- `restore_database.sh` - Safely restores database backups  
- `test_migration.sh` - Tests migrations on production data copies

## 🔄 Backup Procedures

### Automated Daily Backups

```bash
# Development environment
./scripts/backup_database.sh dev

# Staging environment  
./scripts/backup_database.sh staging

# Production environment
./scripts/backup_database.sh production
```

### Backup Features

- **Timestamped Files**: Format `sabc_backup_{env}_{YYYYMMDD_HHMMSS}.sql.gz`
- **Compression**: All backups automatically compressed with gzip
- **Integrity Checks**: Automatic verification of backup file integrity
- **Retention Policy**: Keeps 7 days of backups, automatically purges older files
- **Logging**: Detailed logs for each backup operation

### Backup Storage Structure

```
backups/
├── sabc_backup_dev_20250810_143022.sql.gz
├── sabc_backup_staging_20250810_120000.sql.gz  
├── sabc_backup_production_20250810_060000.sql.gz
├── backup_dev_20250810_143022.log
├── backup_staging_20250810_120000.log
└── backup_production_20250810_060000.log
```

## 🔧 Migration Testing Protocol

### Before Any Production Migration

1. **Create Production Backup**
   ```bash
   ./scripts/backup_database.sh production
   ```

2. **Test Migration on Copy**
   ```bash
   ./scripts/test_migration.sh /path/to/production_backup.sql.gz
   ```

3. **Review Test Report**
   - Check data integrity results
   - Verify table count changes
   - Review any warnings or issues

### Migration Test Features

- Creates isolated test database with production data copy
- Runs complete migration sequence
- Performs data integrity checks
- Tests basic application functionality
- Generates detailed test report
- Automatic cleanup of test resources

## 🚨 Disaster Recovery Procedures

### Emergency Restore Process

1. **Immediate Assessment**
   - Identify scope of data loss/corruption
   - Determine last known good backup
   - Estimate downtime requirements

2. **Preparation**
   ```bash
   # List available backups
   ls -la backups/sabc_backup_production_*.sql.gz
   
   # Verify backup integrity
   gunzip -t backups/sabc_backup_production_YYYYMMDD_HHMMSS.sql.gz
   ```

3. **Execute Restore**
   ```bash
   ./scripts/restore_database.sh backups/sabc_backup_production_YYYYMMDD_HHMMSS.sql.gz production
   ```

4. **Post-Restore Verification**
   - Run Django system checks
   - Test critical user workflows
   - Verify data consistency
   - Monitor application performance

### Recovery Time Objectives (RTO)

- **Development**: 15 minutes maximum
- **Staging**: 30 minutes maximum  
- **Production**: 60 minutes maximum

### Recovery Point Objectives (RPO)

- **Development**: 24 hours (daily backups)
- **Staging**: 24 hours (daily backups)
- **Production**: 24 hours (daily backups)

## 🔒 Security Considerations

### Access Control
- Database credentials stored in environment variables
- Backup files have restricted file permissions (600)
- Production backups require explicit confirmation prompts

### Data Protection
- Backups exclude user sessions and temporary data
- No sensitive credentials stored in backup scripts
- Compressed backups to minimize storage footprint

### Audit Trail
- All backup and restore operations logged with timestamps
- Retention of operation logs matches backup retention (7 days)
- Failed operations trigger immediate alerts

## 🌐 Environment-Specific Configuration

### Development Environment
- **Database**: Local PostgreSQL or SQLite
- **User**: `env` (development user)
- **Host**: `localhost`
- **Backup Frequency**: On-demand
- **Safety Checks**: Minimal confirmation prompts

### Staging Environment  
- **Database**: Staging PostgreSQL instance
- **User**: Configured via `POSTGRES_USER` environment variable
- **Host**: Configured via `DEPLOYMENT_HOST` environment variable
- **Backup Frequency**: Daily at 12:00 PM
- **Safety Checks**: Standard confirmation prompts

### Production Environment
- **Database**: Production PostgreSQL instance
- **User**: Configured via `POSTGRES_USER` environment variable  
- **Host**: Configured via `DEPLOYMENT_HOST` environment variable
- **Backup Frequency**: Daily at 6:00 AM
- **Safety Checks**: Enhanced confirmation prompts and warnings

## 📋 Pre-Deployment Checklist

### Every Production Deployment

- [ ] Create fresh production backup
- [ ] Test migration on production data copy
- [ ] Review migration test report for issues
- [ ] Verify rollback procedure is documented
- [ ] Confirm maintenance window scheduling
- [ ] Notify stakeholders of planned deployment

### Critical Migrations (Schema Changes)

- [ ] All of the above, plus:
- [ ] Extended testing period (24-48 hours)
- [ ] Blue-green deployment preparation  
- [ ] Database performance impact assessment
- [ ] Rollback testing with production data volumes

## 🚀 Blue-Green Deployment Support

### Parallel Environment Strategy
1. **Blue Environment**: Current production system
2. **Green Environment**: New version with migrations applied
3. **Cutover Process**: DNS/load balancer switch
4. **Rollback Capability**: Immediate switch back to blue environment

### Implementation Steps
1. Deploy green environment with new code
2. Apply migrations to green database (copy of production)
3. Validate green environment functionality
4. Switch traffic from blue to green
5. Monitor green environment performance
6. Maintain blue environment as rollback option (24 hours)

## 📊 Monitoring & Alerts

### Backup Success Monitoring
- Daily verification of backup completion
- File size and integrity validation
- Alert on backup failures or size anomalies

### Migration Monitoring  
- Pre/post migration table counts
- Performance impact measurements
- Error rate monitoring during deployment window

### Recovery Testing
- Monthly restore testing on non-production environments
- Quarterly disaster recovery drills
- Annual full recovery procedure testing

## 📚 Usage Examples

### Quick Reference Commands

```bash
# Create development backup
./scripts/backup_database.sh dev

# Test migration with latest production backup
./scripts/test_migration.sh backups/sabc_backup_production_*.sql.gz

# Restore staging from production backup
./scripts/restore_database.sh backups/sabc_backup_production_20250810_060000.sql.gz staging

# Emergency production restore
./scripts/restore_database.sh backups/sabc_backup_production_20250809_060000.sql.gz production
```

## 🔄 Maintenance Schedule

### Daily (Automated)
- Production backup at 6:00 AM Central
- Staging backup at 12:00 PM Central  
- Cleanup of backups older than 7 days

### Weekly
- Backup integrity verification testing
- Log file review and cleanup
- Disk space monitoring for backup storage

### Monthly
- Disaster recovery procedure review
- Backup script testing on non-production environments
- Documentation updates based on operational experience

### Quarterly  
- Full disaster recovery drill
- Recovery time objective validation
- Backup retention policy review

---

## 📞 Emergency Contacts

**Database Issues**: Development Team Lead  
**Infrastructure Issues**: Systems Administrator  
**Business Continuity**: SABC Club Leadership

---

*Last Updated: August 10, 2025*  
*Next Review: September 10, 2025*