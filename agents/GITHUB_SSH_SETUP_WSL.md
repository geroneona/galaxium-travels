# GitHub SSH Setup Guide for WSL

## Step 1: Generate SSH Key in WSL

Open your WSL terminal and run:

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

**Replace `your_email@example.com` with your actual GitHub email address.**

When prompted:
- Press Enter to accept the default file location (`/home/yourusername/.ssh/id_ed25519`)
- Enter a passphrase (optional but recommended)
- Confirm the passphrase

## Step 2: Start SSH Agent

```bash
eval "$(ssh-agent -s)"
```

You should see output like: `Agent pid 12345`

## Step 3: Add SSH Key to Agent

```bash
ssh-add ~/.ssh/id_ed25519
```

## Step 4: Copy Your Public Key

Display your public key:

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy the entire output (starts with `ssh-ed25519` and ends with your email).

## Step 5: Add SSH Key to GitHub

1. Go to GitHub.com and log in
2. Click your profile picture (top right) → **Settings**
3. In the left sidebar, click **SSH and GPG keys**
4. Click **New SSH key** (green button)
5. Give it a title (e.g., "WSL Ubuntu")
6. Paste your public key into the "Key" field
7. Click **Add SSH key**

## Step 6: Test the Connection

```bash
ssh -T git@github.com
```

You should see:
```
Hi username! You've successfully authenticated, but GitHub does not provide shell access.
```

## Step 7: Configure Git (if not already done)

```bash
git config --global user.name "Your Name"
git config --global user.email "your_email@example.com"
```

## Troubleshooting

### Permission Denied Error

If you get "Permission denied (publickey)", check:

1. **Verify SSH key was added to agent:**
   ```bash
   ssh-add -l
   ```

2. **Check SSH key permissions:**
   ```bash
   chmod 600 ~/.ssh/id_ed25519
   chmod 644 ~/.ssh/id_ed25519.pub
   ```

3. **Verify the key is on GitHub:**
   - Go to GitHub Settings → SSH and GPG keys
   - Make sure your key is listed

### Using the Correct Remote URL

When cloning or setting up remotes, use SSH format:
```bash
git clone git@github.com:username/repository.git
```

NOT HTTPS format:
```bash
# Don't use this:
git clone https://github.com/username/repository.git
```

### Change Existing Remote from HTTPS to SSH

If you already have a repository cloned with HTTPS:

```bash
# Check current remote
git remote -v

# Change to SSH
git remote set-url origin git@github.com:username/repository.git

# Verify the change
git remote -v
```

## Quick Reference Commands

```bash
# Generate new SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Start SSH agent
eval "$(ssh-agent -s)"

# Add key to agent
ssh-add ~/.ssh/id_ed25519

# Display public key (to copy to GitHub)
cat ~/.ssh/id_ed25519.pub

# Test GitHub connection
ssh -T git@github.com

# List keys in agent
ssh-add -l
```

## Notes

- Your SSH keys are stored in `~/.ssh/` in WSL (separate from Windows)
- You need to add the SSH key to the agent each time you start a new WSL session (unless you configure it to auto-start)
- Keep your private key (`id_ed25519`) secure - never share it
- Only share the public key (`id_ed25519.pub`)