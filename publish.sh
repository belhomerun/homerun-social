#!/bin/bash
# Publish dashboard to GitHub Pages.
# Usage: bash publish.sh
# Run python3 social-dashboard/dashboard.py first.
set -e
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
DASHBOARD="$REPO_ROOT/social-dashboard/dashboard.html"

if [ ! -f "$DASHBOARD" ]; then
  echo "Error: dashboard.html not found. Run this first:"
  echo "  python3 social-dashboard/dashboard.py"
  exit 1
fi

echo "Stashing uncommitted changes..."
git -C "$REPO_ROOT" stash --include-untracked 2>/dev/null || true

echo "Switching to gh-pages..."
git -C "$REPO_ROOT" checkout gh-pages

echo "Copying dashboard.html..."
cp "$DASHBOARD" "$REPO_ROOT/dashboard.html"
git -C "$REPO_ROOT" add dashboard.html
git -C "$REPO_ROOT" commit -m "Update dashboard $(date +%Y-%m-%d)"
git -C "$REPO_ROOT" push origin gh-pages

echo "Switching back to main..."
git -C "$REPO_ROOT" checkout main
git -C "$REPO_ROOT" stash pop 2>/dev/null || true

echo ""
echo "Published! https://belhomerun.github.io/homerun-social/dashboard.html"
