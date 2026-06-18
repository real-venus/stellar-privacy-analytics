# GitHub Environments Setup

The CI/CD pipeline (`.github/workflows/ci.yml`) uses **GitHub Environments** to enforce a manual approval gate before deploying to production or staging.

This guide walks you through creating and configuring those environments.

---

## Prerequisites

You need **Admin** access on the repository (`connect-boiz/stellar-privacy-analytics`) to manage environments. Write or triage access is not sufficient.

---

## Option 1: Setup Script (faster, requires a PAT)

If you have a GitHub Personal Access Token with `repo` scope (full control of private repositories):

```bash
# Export your PAT
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Run the setup script
bash scripts/setup-environments.sh
```

Then skip to **[Step 3: Add Required Reviewers](#3-add-required-reviewers)**.

---

## Option 2: Manual Setup via GitHub UI

### 1. Create the Environment

1. Go to your repository on GitHub.
2. Click **Settings** (top tab).
3. In the left sidebar, click **Environments**.
4. Click **New environment**.

### 2. Configure Protection Rules

For each environment, configure the following settings:

#### Production Environment

| Setting | Value |
|---------|-------|
| **Environment name** | `production` |
| **Wait timer** | `10` minutes (gives time to cancel after approval) |
| **Deployment branches** | Select **Selected branches** → Add `main` |
| **Required reviewers** | (See step 3) |

#### Staging Environment

| Setting | Value |
|---------|-------|
| **Environment name** | `staging` |
| **Wait timer** | `5` minutes |
| **Deployment branches** | Select **All branches** (or **Selected branches** → Add `develop`, `main`) |
| **Required reviewers** | (See step 3) |

### 3. Add Required Reviewers

This is the key step for the **manual approval gate**:

1. Inside the environment settings, find **Required reviewers**.
2. Click **Add someone...** and search for:
   - Individual GitHub usernames (e.g., `akordavid373`)
   - Or a GitHub Team (e.g., `@connect-boiz/engineering`)
3. Click **Save protection rules**.

> **How it works:** When the `deploy` job in the CI pipeline targets this environment, GitHub will:
> 1. Pause the workflow
> 2. Notify the required reviewers
> 3. Wait for **all** required reviewers to approve
> 4. Only then proceed with the deployment steps

---

## Verifying It Works

After configuring the environments:

1. Push a commit to the `main` branch (or trigger a `workflow_dispatch`).
2. Go to the repository's **Actions** tab.
3. You should see the `deploy` job with a **Review pending** badge.
4. Click **Review deployments** and approve to proceed.

### Pipeline Flow

```
quality (lint, type-check, tests)
  │
  ▼
build (compile all packages)
  │
  ▼
deploy ⬅ Manual approval required here
  │
  ▼
Production/Staging
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Deploy job is skipped entirely | Check the `if:` condition: it only runs on `main` pushes or `workflow_dispatch` |
| "Resource not accessible by integration" | The GITHUB_TOKEN doesn't have admin scope. Use `workflow_dispatch` instead, or update the token |
| Review prompt doesn't appear | Ensure required reviewers are added to the environment AND that they're org members / collaborators |
| Deploy runs without approval | Verify the environment name in the workflow matches **exactly** (`production`, not `prod`) |
