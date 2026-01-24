#!/bin/bash

# Define paths
SOURCE_DIR="/Users/shourjosmac/Documents/Gainsly"
DEST_DIR="/Users/shourjosmac/Documents/alloy"

echo "🚀 Starting clean copy..."
echo "Source: $SOURCE_DIR"
echo "Destination: $DEST_DIR"

# Create destination directory
mkdir -p "$DEST_DIR"

# Copy files using rsync
# Excludes .venv, node_modules, .git, and other temp files
rsync -av --progress "$SOURCE_DIR/" "$DEST_DIR/" \
    --exclude '.venv' \
    --exclude 'frontend/node_modules' \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '.DS_Store' \
    --exclude '.idea' \
    --exclude '.vscode'

echo "✅ Files copied successfully!"

# Create .env file for alloy with correct database port
echo "Creating .env file for Alloy..."
cat > "$DEST_DIR/.env" << EOL
# Alloy Project Configuration
DATABASE_URL=postgresql+asyncpg://gainsly:gainslypass@localhost:5433/gainslydb
APP_NAME="Alloy"
DEBUG=True
EOL

# Create frontend .env file
echo "Creating frontend/.env file for Alloy..."
cat > "$DEST_DIR/frontend/.env" << EOL
VITE_API_URL=http://localhost:8000
EOL

echo "🎉 Done! Your clean copy is ready at: $DEST_DIR"
echo ""
echo "Next steps:"
echo "1. cd $DEST_DIR"
echo "2. python3 -m venv .venv"
echo "3. source .venv/bin/activate"
echo "4. pip install -r requirements.txt"
echo "5. cd frontend && npm install"
