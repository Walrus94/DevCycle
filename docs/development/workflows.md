# Development Workflows

This document outlines the development workflows and processes used in the DevCycle project to ensure efficient collaboration, code quality, and reliable deployments.

## Table of Contents

- [Git Workflow](#git-workflow)
- [Branch Strategy](#branch-strategy)
- [Issue Management](#issue-management)
- [Development Process](#development-process)
- [Testing Workflow](#testing-workflow)
- [Code Review Process](#code-review-process)
- [Deployment Workflow](#deployment-workflow)
- [Release Process](#release-process)
- [Hotfix Process](#hotfix-process)

## Git Workflow

### Repository Structure

We use a **Git Flow** approach with the following main branches:

- **`main`**: Production-ready code
- **`develop`**: Integration branch for features
- **`feature/*`**: Feature development branches
- **`hotfix/*`**: Critical bug fixes
- **`release/*`**: Release preparation branches

### Branch Naming Convention

```bash
# Feature branches
feature/DOTM-123-add-user-authentication
feature/DOTM-456-improve-agent-performance

# Bug fix branches
bugfix/DOTM-789-fix-message-routing
bugfix/DOTM-101-fix-database-connection

# Hotfix branches
hotfix/DOTM-202-critical-security-patch

# Release branches
release/v1.2.0
release/v2.0.0-beta
```

### Commit Message Format

We follow the **Conventional Commits** specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Types

- **`feat`**: New feature
- **`fix`**: Bug fix
- **`docs`**: Documentation changes
- **`style`**: Code style changes (formatting, etc.)
- **`refactor`**: Code refactoring
- **`test`**: Adding or updating tests
- **`chore`**: Maintenance tasks
- **`perf`**: Performance improvements
- **`ci`**: CI/CD changes

#### Examples

```bash
# Feature
feat(agents): add agent heartbeat monitoring

# Bug fix
fix(messages): resolve message queue deadlock

# Documentation
docs(api): update authentication guide

# Breaking change
feat(api)!: change agent registration endpoint

BREAKING CHANGE: The agent registration endpoint now requires
additional fields for security validation.
```

## Branch Strategy

### Feature Development

1. **Create feature branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/DOTM-123-add-user-authentication
   ```

2. **Develop feature** with regular commits:
   ```bash
   git add .
   git commit -m "feat(auth): implement JWT token validation"
   git push origin feature/DOTM-123-add-user-authentication
   ```

3. **Keep branch updated** with develop:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout feature/DOTM-123-add-user-authentication
   git rebase develop
   ```

4. **Create pull request** to `develop` branch

### Bug Fixes

1. **Create bugfix branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b bugfix/DOTM-789-fix-message-routing
   ```

2. **Fix the bug** and test thoroughly:
   ```bash
   git add .
   git commit -m "fix(messages): resolve routing algorithm edge case"
   ```

3. **Create pull request** to `develop` branch

### Hotfixes

For critical production issues:

1. **Create hotfix branch** from `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b hotfix/DOTM-202-critical-security-patch
   ```

2. **Apply minimal fix**:
   ```bash
   git add .
   git commit -m "fix(security): patch authentication bypass vulnerability"
   ```

3. **Create pull request** to both `main` and `develop`

## Issue Management

### Linear Integration

We use Linear for issue tracking with the following workflow:

1. **Create issue** in Linear with:
   - Clear title and description
   - Appropriate labels and priority
   - Acceptance criteria
   - Estimated effort

2. **Link to branch**:
   ```bash
   # Linear automatically creates branch name
   git checkout -b arsnazarov94/dotm-123-feature-name
   ```

3. **Update issue status** as work progresses:
   - `Backlog` → `In Progress` → `In Review` → `Done`

### Issue Types

- **`Feature`**: New functionality
- **`Bug`**: Defects to fix
- **`Enhancement`**: Improvements to existing features
- **`Documentation`**: Documentation updates
- **`Technical Debt`**: Code quality improvements

### Issue Templates

#### Feature Request Template

```markdown
## Feature Description
Brief description of the feature.

## User Story
As a [user type], I want [functionality] so that [benefit].

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Considerations
- Dependencies
- Performance impact
- Security considerations

## Definition of Done
- [ ] Code implemented and tested
- [ ] Documentation updated
- [ ] Code reviewed and approved
- [ ] Tests passing
```

#### Bug Report Template

```markdown
## Bug Description
Clear description of the bug.

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen.

## Actual Behavior
What actually happens.

## Environment
- OS:
- Python version:
- DevCycle version:

## Additional Context
Screenshots, logs, etc.
```

## Development Process

### 1. Planning Phase

- **Review requirements** and acceptance criteria
- **Estimate effort** and complexity
- **Identify dependencies** and blockers
- **Plan implementation** approach

### 2. Development Phase

- **Set up development environment**:
  ```bash
  # Clone repository
  git clone https://github.com/devcycle/devcycle.git
  cd devcycle

  # Install dependencies
  poetry install

  # Set up environment
  cp config/development.env.example config/development.env
  # Edit configuration as needed

  # Start services
  docker-compose up -d
  ```

- **Follow coding standards** (see [Coding Standards](standards.md))
- **Write tests** as you develop (TDD approach)
- **Commit frequently** with descriptive messages
- **Keep branches updated** with develop

### 3. Testing Phase

- **Run unit tests**:
  ```bash
  poetry run pytest tests/unit/
  ```

- **Run integration tests**:
  ```bash
  poetry run pytest tests/integration/
  ```

- **Run end-to-end tests**:
  ```bash
  poetry run pytest tests/e2e/
  ```

- **Check code coverage**:
  ```bash
  poetry run pytest --cov=devcycle --cov-report=html
  ```

- **Run linting and formatting**:
  ```bash
  poetry run black .
  poetry run isort .
  poetry run flake8 .
  poetry run mypy .
  ```

### 4. Code Review Phase

- **Create pull request** with:
  - Clear title and description
  - Link to Linear issue
  - Screenshots for UI changes
  - Testing instructions

- **Request review** from appropriate team members
- **Address feedback** promptly
- **Ensure all checks pass** (CI/CD, tests, linting)

### 5. Integration Phase

- **Merge to develop** after approval
- **Verify integration** tests pass
- **Update documentation** if needed
- **Close Linear issue**

## Testing Workflow

### Test-Driven Development (TDD)

1. **Write failing test**:
   ```python
   def test_create_agent_with_valid_data():
       # Arrange
       agent_data = {
           "name": "test_agent",
           "type": "business_analyst"
       }

       # Act
       result = create_agent(agent_data)

       # Assert
       assert result.name == "test_agent"
       assert result.status == "registered"
   ```

2. **Run test** (should fail):
   ```bash
   poetry run pytest tests/unit/test_agents.py::test_create_agent_with_valid_data -v
   ```

3. **Write minimal code** to make test pass:
   ```python
   def create_agent(data: dict) -> Agent:
       return Agent(
           name=data["name"],
           type=data["type"],
           status="registered"
       )
   ```

4. **Refactor** while keeping tests green

### Test Categories

#### Unit Tests
- **Location**: `tests/unit/`
- **Purpose**: Test individual functions and classes
- **Coverage**: 80% minimum
- **Run**: `poetry run pytest tests/unit/`

#### Integration Tests
- **Location**: `tests/integration/`
- **Purpose**: Test component interactions
- **Coverage**: Critical paths only
- **Run**: `poetry run pytest tests/integration/`

#### End-to-End Tests
- **Location**: `tests/e2e/`
- **Purpose**: Test complete user workflows
- **Coverage**: Main user journeys
- **Run**: `poetry run pytest tests/e2e/`

### Test Data Management

```python
# Use factories for test data
import factory
from devcycle.core.models import Agent

class AgentFactory(factory.Factory):
    class Meta:
        model = Agent

    name = factory.Sequence(lambda n: f"test_agent_{n}")
    type = "business_analyst"
    status = "registered"
    version = "1.0.0"

# Use in tests
def test_agent_creation():
    agent = AgentFactory()
    assert agent.name.startswith("test_agent")
```

## Code Review Process

### Review Checklist

#### For Authors
- [ ] Code follows project standards
- [ ] Tests are comprehensive and pass
- [ ] Documentation is updated
- [ ] No sensitive data in code
- [ ] Performance implications considered
- [ ] Security considerations addressed

#### For Reviewers
- [ ] Code is readable and maintainable
- [ ] Logic is correct and efficient
- [ ] Error handling is appropriate
- [ ] Tests cover edge cases
- [ ] No breaking changes without notice
- [ ] Dependencies are justified

### Review Guidelines

#### Be Constructive
```markdown
# Good feedback
The error handling here could be more specific. Consider catching
ValidationError separately from generic exceptions to provide
better error messages to users.

# Bad feedback
This is wrong.
```

#### Be Specific
```markdown
# Good feedback
Line 45: The variable name `data` is too generic. Consider
renaming to `agent_config` to be more descriptive.

# Bad feedback
Variable names are confusing.
```

#### Suggest Improvements
```markdown
# Good feedback
This function is doing too much. Consider extracting the
validation logic into a separate `validate_agent_data()`
function to improve readability and testability.
```

### Review Timeline

- **Initial review**: Within 24 hours
- **Follow-up reviews**: Within 4 hours
- **Critical issues**: Immediate attention
- **Non-blocking issues**: Can be addressed in follow-up PR

## Deployment Workflow

### Environment Strategy

- **Development**: Local development environment
- **Staging**: Pre-production testing environment
- **Production**: Live production environment

### Deployment Process

#### 1. Staging Deployment

```bash
# Merge to develop branch
git checkout develop
git pull origin develop
git merge feature/DOTM-123-add-user-authentication

# Deploy to staging
./scripts/deploy-staging.sh
```

#### 2. Production Deployment

```bash
# Create release branch
git checkout develop
git checkout -b release/v1.2.0

# Update version numbers
poetry version patch

# Create pull request to main
# After approval and merge, deploy to production
./scripts/deploy-production.sh
```

### Deployment Scripts

#### Staging Deployment
```bash
#!/bin/bash
# scripts/deploy-staging.sh

set -e

echo "Deploying to staging..."

# Build Docker image
docker build -t devcycle:staging .

# Deploy to staging
docker-compose -f docker-compose.staging.yml up -d

# Run health checks
./scripts/health-check.sh staging

echo "Staging deployment complete!"
```

#### Production Deployment
```bash
#!/bin/bash
# scripts/deploy-production.sh

set -e

echo "Deploying to production..."

# Backup current deployment
./scripts/backup-production.sh

# Deploy new version
docker-compose -f docker-compose.production.yml up -d

# Run health checks
./scripts/health-check.sh production

# Verify deployment
./scripts/verify-deployment.sh

echo "Production deployment complete!"
```

## Release Process

### Release Planning

1. **Feature freeze** on develop branch
2. **Create release branch** from develop
3. **Update version numbers** and changelog
4. **Run full test suite**
5. **Deploy to staging** for final testing
6. **Create pull request** to main
7. **Deploy to production** after approval

### Version Numbering

We follow **Semantic Versioning** (SemVer):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

Examples:
- `1.0.0` → `1.0.1` (patch)
- `1.0.1` → `1.1.0` (minor)
- `1.1.0` → `2.0.0` (major)

### Changelog Format

```markdown
# Changelog

## [1.2.0] - 2024-01-15

### Added
- Agent heartbeat monitoring system
- Message priority levels (normal, high, urgent)
- API rate limiting

### Changed
- Improved agent registration validation
- Updated authentication token expiration to 15 minutes

### Fixed
- Fixed message queue deadlock issue
- Resolved agent status update race condition

### Security
- Enhanced JWT token validation
- Added input sanitization for agent names
```

## Hotfix Process

### When to Use Hotfixes

- **Critical security vulnerabilities**
- **Production-breaking bugs**
- **Data corruption issues**
- **Performance degradation**

### Hotfix Workflow

1. **Create hotfix branch** from main:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b hotfix/DOTM-202-critical-security-patch
   ```

2. **Apply minimal fix**:
   ```bash
   git add .
   git commit -m "fix(security): patch authentication bypass vulnerability"
   ```

3. **Test thoroughly**:
   ```bash
   poetry run pytest tests/unit/
   poetry run pytest tests/integration/
   ```

4. **Create pull request** to main
5. **Deploy to production** immediately after approval
6. **Merge back to develop**:
   ```bash
   git checkout develop
   git merge hotfix/DOTM-202-critical-security-patch
   ```

### Emergency Procedures

For critical production issues:

1. **Immediate response** (within 15 minutes)
2. **Assess impact** and communicate to stakeholders
3. **Apply hotfix** following hotfix workflow
4. **Monitor deployment** and verify fix
5. **Post-incident review** within 24 hours

## Continuous Integration/Continuous Deployment (CI/CD)

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install Poetry
      uses: snok/install-poetry@v1

    - name: Install dependencies
      run: poetry install

    - name: Run linting
      run: |
        poetry run black --check .
        poetry run isort --check-only .
        poetry run flake8 .
        poetry run mypy .

    - name: Run tests
      run: poetry run pytest --cov=devcycle

    - name: Upload coverage
      uses: codecov/codecov-action@v3

  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'

    steps:
    - uses: actions/checkout@v3
    - name: Deploy to staging
      run: ./scripts/deploy-staging.sh

  deploy-production:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3
    - name: Deploy to production
      run: ./scripts/deploy-production.sh
```

## Best Practices

### Development

- **Start with tests** (TDD approach)
- **Commit frequently** with descriptive messages
- **Keep branches small** and focused
- **Update documentation** as you develop
- **Use meaningful variable names**
- **Handle errors gracefully**

### Collaboration

- **Communicate early** about blockers
- **Ask questions** when requirements are unclear
- **Share knowledge** through code reviews
- **Document decisions** and rationale
- **Be respectful** in all interactions

### Quality Assurance

- **Test thoroughly** before submitting PR
- **Review your own code** before requesting review
- **Address feedback** promptly and constructively
- **Keep dependencies updated**
- **Monitor production** after deployments

## Tools and Resources

### Development Tools

- **IDE**: VS Code with Python extension
- **Version Control**: Git with GitHub
- **Package Management**: Poetry
- **Testing**: pytest with coverage
- **Linting**: Black, isort, flake8, mypy
- **Documentation**: MkDocs with Material theme

### Monitoring and Observability

- **Logging**: Structured logging with Python logging
- **Metrics**: Prometheus and Grafana
- **Tracing**: OpenTelemetry
- **Error Tracking**: Sentry
- **Health Checks**: Custom health check endpoints

### Communication

- **Issue Tracking**: Linear
- **Code Reviews**: GitHub Pull Requests
- **Documentation**: GitHub Wiki and MkDocs
- **Team Chat**: Slack
- **Video Calls**: Zoom

## Conclusion

Following these workflows ensures:

- **Consistent development process** across the team
- **High code quality** through automated checks
- **Reliable deployments** with proper testing
- **Effective collaboration** through clear processes
- **Rapid response** to production issues

Remember: **Processes should serve the team, not the other way around**. Adapt these workflows as needed to fit your team's needs and constraints.
