# GitHub Repository Configuration

## Branch Protection Rules

### Main Branch

Protect the `main` branch with the following rules:

1. **Require pull request reviews before merging**

   - Required approving reviews: 1
   - Dismiss stale pull request approvals when new commits are pushed

2. **Require status checks to pass before merging**

   - Require branches to be up to date before merging
   - Required status checks:
     - `Python Tests (Server & Agent)`
     - `Frontend Tests (Dashboard)`
     - `Security Vulnerability Scan`
     - `Verify Builds`

3. **Require conversation resolution before merging**

4. **Do not allow bypassing the above settings**

### Develop Branch

Similar protection rules as main, but allow direct commits from maintainers for development work.

## Repository Settings

### General

- **Default branch:** `main`
- **Merge button:** Allow squash merging
- **Automatically delete head branches:** Enabled

### Security & Analysis

- **Dependency graph:** Enabled
- **Dependabot alerts:** Enabled
- **Dependabot security updates:** Enabled
- **Code scanning:** Enabled (CodeQL)
- **Secret scanning:** Enabled

### Actions

- **Actions permissions:** Allow all actions and reusable workflows
- **Workflow permissions:** Read and write permissions
- **Allow GitHub Actions to create and approve pull requests:** Disabled

## Required Labels

Create the following labels for issue and PR management:

- `bug` - Something isn't working (red)
- `enhancement` - New feature or request (green)
- `documentation` - Improvements or additions to documentation (blue)
- `installation` - Installation-related issues (purple)
- `security` - Security-related issues (orange)
- `performance` - Performance improvements (yellow)
- `frontend` - Dashboard/UI related (cyan)
- `backend` - Server-side related (pink)
- `agent` - Agent-related issues (brown)
- `ml-engine` - ML/anomaly detection related (magenta)
- `good first issue` - Good for newcomers (light green)
- `help wanted` - Extra attention is needed (teal)
- `priority: high` - High priority (red)
- `priority: medium` - Medium priority (orange)
- `priority: low` - Low priority (yellow)

## Secrets Configuration

Add the following secrets for CI/CD:

- `DOCKER_USERNAME` - Docker Hub username (for future container builds)
- `DOCKER_PASSWORD` - Docker Hub password/token
- `NPM_TOKEN` - NPM token (if publishing packages)

## Automated Workflows

The repository includes the following GitHub Actions workflows:

1. **CI/CD Pipeline** (`.github/workflows/ci.yml`)

   - Runs on push to main, develop, deployment
   - Tests Python backend and agent
   - Tests TypeScript frontend
   - Security scanning
   - Build verification

2. **Dependency Review** (`.github/workflows/dependency-review.yml`)

   - Runs on pull requests
   - Reviews new dependencies for security issues

3. **Installer Tests** (`.github/workflows/installer-tests.yml`)

   - Validates installer scripts
   - ShellCheck linting
   - Syntax validation

4. **Documentation Check** (`.github/workflows/documentation.yml`)
   - Markdown linting
   - Link checking
   - README validation

## Notifications

Configure the following notifications:

1. **Email notifications:** For pull requests and issues
2. **Slack/Discord webhooks:** For deployment notifications (optional)
3. **Dependabot alerts:** Enable email notifications

## Apply Settings Script

To quickly apply these settings via GitHub CLI:

```bash
# Install GitHub CLI if not already installed
# See: https://cli.github.com/

# Enable branch protection for main
gh api repos/MokshitBindal/Aegis/branches/main/protection -X PUT \
  -f required_status_checks[strict]=true \
  -f required_status_checks[contexts][]=python-tests \
  -f required_status_checks[contexts][]=frontend-tests \
  -f required_pull_request_reviews[required_approving_review_count]=1 \
  -f required_pull_request_reviews[dismiss_stale_reviews]=true \
  -f enforce_admins=false \
  -f required_conversation_resolution=true

# Enable Dependabot
gh api repos/MokshitBindal/Aegis/vulnerability-alerts -X PUT

# Enable secret scanning
gh api repos/MokshitBindal/Aegis -X PATCH \
  -f security_and_analysis[secret_scanning][status]=enabled
```

## Manual Configuration Steps

Some settings require manual configuration via GitHub web UI:

1. Go to repository **Settings** > **Branches**
2. Add branch protection rule for `main`
3. Go to **Settings** > **Security & analysis**
4. Enable all available features
5. Go to **Settings** > **Actions** > **General**
6. Configure workflow permissions
