#!/usr/bin/env bash
set -euo pipefail
git init
git config core.autocrlf input
git config core.filemode true
echo "Git repository initialized for WSL/Linux development."
echo "Set your identity if needed:"
echo '  git config --global user.name "Your Name"'
echo '  git config --global user.email "you@example.com"'
