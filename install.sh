#!/bin/bash

# ContextVault Installation Script
# For local AI enthusiasts who prefer command-line tools

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    ContextVault Installer                    ║"
    echo "║              AI Memory for Local AI Models                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${YELLOW}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed"
        return 1
    fi
    return 0
}

# Main installation
install_contextvault() {
    print_header
    
    print_step "Checking system requirements..."
    
    # Check Python
    if ! check_command python3; then
        print_error "Python 3 is required but not installed"
        print_info "Please install Python 3.8+ from https://python.org"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [ "$(echo "$PYTHON_VERSION < 3.8" | bc -l)" -eq 1 ]; then
        print_error "Python $PYTHON_VERSION found, but 3.8+ is required"
        exit 1
    fi
    
    print_success "Python $PYTHON_VERSION is compatible"
    
    # Check for Ollama
    if ! check_command ollama; then
        print_info "Ollama not found. Installing Ollama..."
        install_ollama
    else
        print_success "Ollama is already installed"
    fi
    
    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        print_info "Starting Ollama service..."
        start_ollama
    else
        print_success "Ollama is running"
    fi
    
    # Check for required Ollama models
    check_ollama_models
    
    print_step "Installing ContextVault dependencies..."
    
    # Install Python dependencies
    pip3 install -r requirements.txt
    
    print_success "Dependencies installed"
    
    print_step "Setting up ContextVault..."
    
    # Initialize ContextVault
    python3 -m contextvault.cli setup
    
    print_success "ContextVault setup complete!"
    
    # Show next steps
    echo ""
    echo -e "${GREEN}🎉 ContextVault installation complete!${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  1. Start ContextVault:"
    echo -e "     ${YELLOW}python3 -m contextvault.cli start${NC}"
    echo ""
    echo "  2. Test it works:"
    echo -e "     ${YELLOW}python3 -m contextvault.cli test${NC}"
    echo ""
    echo "  3. Run a demo:"
    echo -e "     ${YELLOW}python3 -m contextvault.cli demo${NC}"
    echo ""
    echo "  4. Use ContextVault:"
    echo "     Instead of: curl http://localhost:11434/api/generate ..."
    echo "     Use:        curl http://localhost:11435/api/generate ..."
    echo ""
    echo -e "${GREEN}ContextVault is ready to give your AI models persistent memory! 🧠${NC}"
}

install_ollama() {
    print_info "Installing Ollama..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if check_command brew; then
            brew install ollama
        else
            print_info "Installing Ollama via curl..."
            curl -fsSL https://ollama.ai/install.sh | sh
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        print_error "Unsupported operating system: $OSTYPE"
        print_info "Please install Ollama manually from https://ollama.ai"
        exit 1
    fi
    
    print_success "Ollama installed"
}

start_ollama() {
    print_info "Starting Ollama service..."
    
    # Start Ollama in background
    nohup ollama serve > /dev/null 2>&1 &
    
    # Wait for Ollama to start
    for i in {1..10}; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            print_success "Ollama started"
            return 0
        fi
        sleep 1
    done
    
    print_error "Failed to start Ollama"
    exit 1
}

check_ollama_models() {
    print_step "Checking Ollama models..."
    
    # Get available models
    MODELS=$(curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    models = [model['name'] for model in data.get('models', [])]
    print(' '.join(models))
except:
    print('')
")
    
    if [ -z "$MODELS" ]; then
        print_info "No Ollama models found. Installing mistral:latest..."
        ollama pull mistral:latest
        print_success "mistral:latest installed"
    else
        print_success "Found models: $MODELS"
        
        # Check if mistral:latest is available
        if [[ "$MODELS" == *"mistral:latest"* ]]; then
            print_success "mistral:latest is available"
        else
            print_info "Installing mistral:latest..."
            ollama pull mistral:latest
            print_success "mistral:latest installed"
        fi
    fi
}

# Main execution
main() {
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        print_error "Please do not run this installer as root"
        exit 1
    fi
    
    # Check if bc is available for version comparison
    if ! check_command bc; then
        print_info "Installing bc for version comparison..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            if check_command brew; then
                brew install bc
            else
                print_error "Please install bc manually or use Homebrew"
                exit 1
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo apt-get update && sudo apt-get install -y bc
        fi
    fi
    
    # Run installation
    install_contextvault
}

# Run main function
main "$@"
