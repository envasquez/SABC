# SABC Documentation

Welcome to the South Austin Bass Club Tournament Management System documentation. This directory contains comprehensive documentation for developers, administrators, and end users.

---

## Quick Links

| Document | Description | Audience |
|----------|-------------|----------|
| [Architecture](ARCHITECTURE.md) | System design and component overview | Developers |
| [Development](DEVELOPMENT.md) | Local development setup and workflow | Developers |
| [API Reference](API_REFERENCE.md) | Complete API endpoint documentation | Developers |
| [Deployment](DEPLOYMENT.md) | Production deployment guide | Admins |
| [User Guide](USER_GUIDE.md) | How to use the application | End Users |
| [Testing](TESTING.md) | Test suite and testing practices | Developers |
| [Components](COMPONENTS.md) | Frontend/backend component reference | Developers |
| [Database Migrations](DATABASE_MIGRATIONS.md) | Alembic migration guide | Developers |
| [Monitoring](MONITORING.md) | Sentry and Prometheus setup | Admins |
| [Email Setup](EMAIL_SETUP.md) | SMTP configuration | Admins |

---

## Documentation Overview

### For Developers

Start here if you're contributing to the codebase:

1. **[Development Guide](DEVELOPMENT.md)** - Set up your local environment
2. **[Architecture](ARCHITECTURE.md)** - Understand the system design
3. **[Components](COMPONENTS.md)** - Learn about reusable components
4. **[API Reference](API_REFERENCE.md)** - Explore available endpoints
5. **[Testing](TESTING.md)** - Write and run tests
6. **[Database Migrations](DATABASE_MIGRATIONS.md)** - Manage schema changes

Also see:
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [CLAUDE.md](../CLAUDE.md) - AI development guidelines

### For Administrators

If you're deploying or managing the system:

1. **[Deployment Guide](DEPLOYMENT.md)** - Deploy to production
2. **[Monitoring](MONITORING.md)** - Set up error tracking and metrics
3. **[Email Setup](EMAIL_SETUP.md)** - Configure email notifications
4. **[Security Policy](../SECURITY.md)** - Security practices and incident response

### For End Users

If you're a club member using the application:

1. **[User Guide](USER_GUIDE.md)** - Complete guide to using the system

---

## Document Summaries

### Architecture (`ARCHITECTURE.md`)

Comprehensive overview of the system architecture including:
- Technology stack
- Directory structure
- Core components
- Data flow diagrams
- Database schema
- Design decisions

### Development (`DEVELOPMENT.md`)

Everything needed for local development:
- Quick start guide
- Environment setup (Nix and manual)
- Development workflow
- Code standards
- Database development
- Frontend development
- Debugging tips

### API Reference (`API_REFERENCE.md`)

Complete API documentation including:
- Authentication endpoints
- Public page routes
- Member-only routes
- Admin routes
- JSON API endpoints
- Error responses
- Rate limiting

### Deployment (`DEPLOYMENT.md`)

Production deployment guide covering:
- Server requirements
- Docker Compose setup
- Environment variables
- SSL/TLS configuration
- Database management
- Backup and recovery
- Troubleshooting

### User Guide (`USER_GUIDE.md`)

End-user documentation including:
- Getting started (registration, login)
- Profile management
- Tournament calendar
- Voting on polls
- Viewing results
- AoY standings
- FAQ

### Testing (`TESTING.md`)

Test suite documentation:
- Test structure
- Test categories (unit, integration, security)
- Writing tests
- Running tests
- Coverage reports
- CI/CD integration

### Components (`COMPONENTS.md`)

Reusable component reference:
- Jinja2 macros
- JavaScript utilities
- Backend helpers
- CRUD operations
- Best practices

### Database Migrations (`DATABASE_MIGRATIONS.md`)

Alembic migration guide:
- Creating migrations
- Applying migrations
- Rollback procedures
- Best practices

### Monitoring (`MONITORING.md`)

Observability setup:
- Sentry error tracking
- Prometheus metrics
- Alerting configuration
- Dashboard examples

### Email Setup (`EMAIL_SETUP.md`)

Email configuration:
- SMTP settings
- Email templates
- Testing email delivery
- Troubleshooting

---

## Additional Resources

### Root-Level Documents

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | Project overview and quick start |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | How to contribute |
| [SECURITY.md](../SECURITY.md) | Security policy |
| [CLAUDE.md](../CLAUDE.md) | AI development guidelines |
| [LICENSE](../LICENSE) | MIT License |

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [HTMX Documentation](https://htmx.org/)
- [Bootstrap 5 Documentation](https://getbootstrap.com/docs/5.3/)
- [Chart.js Documentation](https://www.chartjs.org/docs/)

---

## Documentation Standards

When updating documentation:

1. **Keep it current** - Update docs when code changes
2. **Be concise** - Clear and to the point
3. **Use examples** - Show, don't just tell
4. **Include dates** - Add "Last Updated" to documents
5. **Link related docs** - Connect related topics

### Markdown Guidelines

- Use ATX-style headers (`#`, `##`, `###`)
- Use fenced code blocks with language identifiers
- Include table of contents for long documents
- Use tables for structured data
- Use relative links for internal references

---

## Getting Help

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Documentation Issues**: Report doc problems via GitHub issues

---

**Last Updated**: 2024-11-30
