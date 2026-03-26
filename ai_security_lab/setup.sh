#!/bin/bash
# AI Security Lab Setup Script

echo "🤖 AI Security Lab - Environment Setup"
echo "======================================"
echo "⚠️  This tool is for EDUCATIONAL PURPOSES only!"
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
if [[ $(echo "$python_version < 3.8" | bc) -eq 1 ]]; then
    echo "❌ Python 3.8+ required"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
echo "📚 Installing required packages..."
pip install -r requirements.txt

# Create directories
echo "📁 Creating project directories..."
mkdir -p models
mkdir -p datasets
mkdir -p results
mkdir -p logs
mkdir -p lab_env

# Create sample wordlist
echo "📝 Creating sample wordlist..."
cat > datasets/subdomains.txt << 'EOF'
www
api
admin
dev
test
staging
mail
blog
shop
portal
login
secure
vpn
backup
ftp
ssh
monitor
analytics
cdn
static
EOF

# Train initial models
echo "🤖 Training initial ML models..."
python3 -c "
from core.ai_engine import AISecurityEngine
engine = AISecurityEngine()
engine.save_models()
print('✅ Models trained successfully')
"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. source venv/bin/activate"
echo "2. python main.py --help"
echo "3. python main.py --target example.com --module subdomain --safe-mode"
echo ""
echo "⚠️  Remember: Only test systems you own or have permission!"