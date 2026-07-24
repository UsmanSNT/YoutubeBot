# 🚀 NAS Deployment Guide

This guide provides a complete solution for deploying VideoGrabberBot (and other Docker applications) on Synology NAS with automatic container updates via `git push`.

## 📋 Overview

**Goal**: Set up automated deployment where `git push nas` triggers automatic Docker container rebuild and restart on your NAS.

**Benefits**:
- ✅ One-command deployment
- ✅ Automatic Docker container management
- ✅ Secure secrets management
- ✅ Easy rollbacks and backups
- ✅ Works with any Docker-based project

## 🛠 Prerequisites

### NAS Requirements
- Synology NAS (DS423+ or similar) with DSM 7.0+
- SSH access enabled
- Container Manager package installed
- Git package installed
- User with docker group membership

### Local Machine Requirements
- Git configured
- SSH key pair generated (`ssh-keygen -t ed25519`)
- SSH access to NAS configured

## 🏗 Project Structure

Your project needs these files for NAS deployment:

```
your-project/
├── .nas_deploy.env.example      # Configuration template
├── .nas_deploy.env              # Actual config (git-ignored)
├── scripts/
│   ├── nas_bootstrap.sh         # Setup automation script  
│   └── nas_exec.sh             # Remote command execution
├── Makefile                    # Deployment commands
├── docker-compose.yml          # Container definition
├── .env.example               # App config template
└── NAS_DEPLOY_GUIDE.md        # This guide
```

## 🚀 Quick Setup

### Step 1: Project Files Setup

1. **Copy deployment files** to your project:
   ```bash
   # Copy from VideoGrabberBot or create based on examples below
   cp scripts/nas_*.sh your-project/scripts/
   cp .nas_deploy.env.example your-project/
   # Add NAS-related Makefile targets
   ```

2. **Configure your deployment**:
   ```bash
   cp .nas_deploy.env.example .nas_deploy.env
   # Edit .nas_deploy.env with your NAS details
   ```

3. **Add to .gitignore**:
   ```bash
   echo ".nas_deploy.env" >> .gitignore
   ```

### Step 2: NAS User Setup

Create a dedicated user for deployments:

```bash
# On NAS (via SSH as admin)
sudo adduser deploy
sudo usermod -aG docker deploy
sudo mkdir -p /volume1/docker /volume1/git
sudo chown deploy:users /volume1/docker /volume1/git
```

### Step 3: SSH Configuration

Add to your `~/.ssh/config`:

```
Host nas
    HostName your-nas-hostname-or-ip
    User deploy
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

Test SSH access:
```bash
ssh nas 'echo "Connection OK"'
```

### Step 4: Bootstrap Deployment

Run the automated setup:

```bash
make nas-init
# OR manually:
# make nas-bootstrap
```

This will:
- Create git repository on NAS
- Install post-receive hook
- Configure git remote
- Set up deployment directories

### Step 5: First Deployment

```bash
make nas-push
# Configure secrets on NAS
ssh nas 'nano /volume1/docker/your-app/.env'
make nas-restart
```

## 📁 Template Files

### .nas_deploy.env.example
```bash
# NAS Deployment Configuration Template
NAS_HOST=your_nas_hostname_or_ip
NAS_USER=deploy
NAS_ALIAS=nas
APP_DIR=/volume1/docker/apps/your-app
GIT_DIR=/volume1/git/your-app.git
BRANCH=main
```

### scripts/nas_bootstrap.sh (Core Script)
```bash
#!/usr/bin/env bash
set -euo pipefail

# Bootstrap NAS autodeploy: creates bare repo, installs post-receive hook
ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
ENV_FILE="${1:-$ROOT_DIR/.nas_deploy.env}"

if [[ -f "$ENV_FILE" ]]; then
  source "$ENV_FILE"
fi

# Required variables validation
for var in NAS_HOST NAS_USER APP_DIR GIT_DIR; do
  if [[ -z "${!var:-}" ]]; then
    echo "ERROR: $var is required in $ENV_FILE" >&2
    exit 1
  fi
done

# SSH connectivity check
SSH_TARGET="${NAS_ALIAS:-$NAS_USER@$NAS_HOST}"
ssh -o ConnectTimeout=5 "$SSH_TARGET" 'echo ok' >/dev/null || {
  echo "ERROR: SSH to $SSH_TARGET failed" >&2
  exit 2
}

# Create directories and initialize bare repo
ssh "$SSH_TARGET" "mkdir -p '$APP_DIR' '$GIT_DIR' && git init --bare '$GIT_DIR'"

# Install post-receive hook
ssh "$SSH_TARGET" "cat > '$GIT_DIR/hooks/post-receive'" <<'HOOK'
#!/bin/sh
set -eu
read oldrev newrev refname
[ "$refname" = "refs/heads/main" ] || exit 0

echo "[deploy] Checking out main -> $APP_DIR"
GIT_WORK_TREE="$APP_DIR" git --git-dir="$GIT_DIR" checkout -f main

cd "$APP_DIR"
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
  echo "[deploy] Created .env from template"
fi

# Docker Compose detection
if docker compose version >/dev/null 2>&1; then 
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then 
  DC="docker-compose"
else 
  echo "[deploy] ERROR: docker compose not found"
  exit 1
fi

echo "[deploy] Building and starting containers..."
$DC build --pull && $DC up -d --remove-orphans
docker image prune -f >/dev/null 2>&1 || true
echo "[deploy] Deployment complete!"
HOOK

ssh "$SSH_TARGET" "chmod +x '$GIT_DIR/hooks/post-receive'"

# Configure local git
git remote add nas "$SSH_TARGET:$GIT_DIR" 2>/dev/null || git remote set-url nas "$SSH_TARGET:$GIT_DIR"
git config alias.push_nas 'push nas main:main'

echo "Bootstrap complete! Use 'git push nas' to deploy."
```

### Makefile Targets
```makefile
# NAS deployment targets
nas-init: ## Initialize NAS deployment (full setup)
	@bash scripts/nas_bootstrap.sh

nas-push: ## Deploy to NAS (git push)
	@git push nas main:main

nas-status: ## Show service status  
	@bash scripts/nas_exec.sh -- 'docker compose ps'

nas-logs: ## Show service logs
	@bash scripts/nas_exec.sh -- 'docker compose logs -f --tail=100 app'

nas-restart: ## Restart service
	@bash scripts/nas_exec.sh -- 'docker compose restart app'

nas-backup: ## Create deployment backup
	@bash scripts/nas_exec.sh -- 'tar -czf /tmp/backup-$(date +%Y%m%d-%H%M%S).tar.gz .'
	@scp nas:/tmp/backup-*.tar.gz ./backups/
	@bash scripts/nas_exec.sh -- 'rm -f /tmp/backup-*.tar.gz'
```

## 🔧 Customization for Different Projects

### For Web Applications
- Change container name in docker-compose.yml
- Adjust port mappings
- Update health checks

### For Databases
- Add volume mounts for persistent data
- Configure backup scripts
- Set up log rotation

### For Multiple Services  
- Use docker-compose services
- Create separate deployment environments
- Configure service dependencies

## 🛡 Security Best Practices

1. **User Isolation**: Use dedicated deployment user, not admin
2. **SSH Keys**: Never use passwords, always SSH keys
3. **Secrets Management**: Keep secrets only on NAS, not in git
4. **Network Security**: Use VPN or firewall rules for NAS access
5. **Backup Strategy**: Regular backups of both code and data

## 🚨 Troubleshooting

### SSH Connection Issues
```bash
# Test connection
ssh -vvv nas 'echo test'

# Check SSH config
ssh-config nas

# Verify SSH agent
ssh-add -l
```

### Docker Permission Issues  
```bash
# On NAS: check user groups
ssh nas 'groups'

# Add user to docker group if missing
ssh nas 'sudo usermod -aG docker $(whoami)'
```

### Deployment Hook Failures
```bash
# Check hook logs on NAS
ssh nas 'tail -f /volume1/git/your-app.git/hooks/post-receive.log'

# Test hook manually
ssh nas 'cd /volume1/git/your-app.git && ./hooks/post-receive'
```

### Container Build Issues
```bash
# Check Docker status on NAS
ssh nas 'docker version && docker compose version'

# Manual build test
ssh nas 'cd /volume1/docker/your-app && docker compose build --no-cache'
```

## 📊 Management Commands

| Command | Purpose |
|---------|---------|
| `make nas-init` | Initial setup (SSH + bootstrap) |
| `make nas-push` | Deploy latest changes |
| `make nas-status` | Check service status |
| `make nas-logs` | View live logs |
| `make nas-restart` | Restart services |
| `make nas-backup` | Create backup |
| `make nas-clean` | Clean up old images |
| `make nas-info` | Show deployment info |

## 🔄 Workflow Examples

### Daily Development
```bash
# Make changes
git add .
git commit -m "Add new feature"

# Deploy to NAS
make nas-push

# Check status
make nas-status
make nas-logs
```

### Emergency Rollback
```bash
# Revert to previous commit
git revert HEAD
git push nas main:main

# Or rollback to specific commit
git reset --hard commit-hash
git push nas main:main --force
```

### Maintenance
```bash
# Create backup before changes
make nas-backup

# Clean up resources
make nas-clean

# Monitor deployment
make nas-info
```

## 🎯 Advanced Features

### Multi-Environment Setup
```bash
# Production
NAS_HOST=nas-prod
APP_DIR=/volume1/docker/apps/app-prod
GIT_DIR=/volume1/git/app-prod.git

# Staging  
NAS_HOST=nas-staging
APP_DIR=/volume1/docker/apps/app-staging
GIT_DIR=/volume1/git/app-staging.git
```

### Blue-Green Deployments
```bash
# Switch between versions
docker compose -f docker-compose.blue.yml up -d
docker compose -f docker-compose.green.yml down
```

### Automated Testing
```bash
# Add to post-receive hook
echo "[deploy] Running tests..."
$DC run --rm app pytest
if [ $? -ne 0 ]; then
  echo "[deploy] Tests failed, rolling back"
  exit 1
fi
```

---

## 📚 Additional Resources

- [Synology Docker Guide](https://www.synology.com/en-us/dsm/packages/Docker)
- [Git Hooks Documentation](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [SSH Configuration Guide](https://www.ssh.com/academy/ssh/config)

---

This guide is based on the VideoGrabberBot deployment system and can be adapted for any Docker-based project. Happy deploying! 🚀