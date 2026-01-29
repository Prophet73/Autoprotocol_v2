#!/bin/bash
# =============================================================================
# WhisperX Server Initial Setup Script
# =============================================================================
# Run this on a fresh Ubuntu/Debian server with NVIDIA GPU
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/.../server-setup.sh | bash
#   OR
#   ./scripts/server-setup.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   WhisperX Server Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Note: Some commands may require sudo${NC}"
fi

# Update system
echo -e "${BLUE}[1/6] Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo -e "${BLUE}[2/6] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo -e "${GREEN}Docker installed${NC}"
else
    echo -e "${GREEN}Docker already installed${NC}"
fi

# Install Docker Compose
echo -e "${BLUE}[3/6] Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose installed${NC}"
else
    echo -e "${GREEN}Docker Compose already installed${NC}"
fi

# Install NVIDIA Container Toolkit
echo -e "${BLUE}[4/6] Installing NVIDIA Container Toolkit...${NC}"
if ! command -v nvidia-container-cli &> /dev/null; then
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    sudo systemctl restart docker
    echo -e "${GREEN}NVIDIA Container Toolkit installed${NC}"
else
    echo -e "${GREEN}NVIDIA Container Toolkit already installed${NC}"
fi

# Test NVIDIA Docker
echo -e "${BLUE}[5/6] Testing NVIDIA Docker...${NC}"
if docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi; then
    echo -e "${GREEN}NVIDIA Docker working!${NC}"
else
    echo -e "${RED}NVIDIA Docker test failed${NC}"
    echo -e "${YELLOW}Make sure NVIDIA drivers are installed${NC}"
fi

# Install useful tools
echo -e "${BLUE}[6/6] Installing utilities...${NC}"
sudo apt-get install -y htop iotop ncdu git curl wget jq

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Server Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Clone the repository:"
echo -e "     ${BLUE}git clone <your-repo-url> whisperx${NC}"
echo -e ""
echo -e "  2. Configure environment:"
echo -e "     ${BLUE}cd whisperx${NC}"
echo -e "     ${BLUE}cp docker/.env.production.example docker/.env.production${NC}"
echo -e "     ${BLUE}nano docker/.env.production${NC}"
echo -e ""
echo -e "  3. Deploy:"
echo -e "     ${BLUE}./deploy.sh${NC}"
echo ""
echo -e "${YELLOW}Note: You may need to log out and back in for Docker group changes to take effect${NC}"
