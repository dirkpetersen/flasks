#!/bin/bash

# A script for these instructions: 
# https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/linux/

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check system architecture
check_arch() {
    arch=$(uname -m)
    if [[ "$arch" != "x86_64" ]]; then
        log "Architecture $arch detected. Only x86_64 is supported for native installation. Will use Docker instead."
        return 1
    fi
    return 0
}

# Function to install Docker if needed
install_docker() {
    if ! command -v docker &> /dev/null; then
        log "Docker not found. Installing Docker..."
        if [[ -f /etc/debian_version ]]; then
            sudo apt-get update
            sudo apt-get install -y docker.io
        else
            sudo dnf -y install docker
        fi
        sudo systemctl enable docker
        sudo systemctl start docker
    fi
}

# Function to install Redis using Docker
install_redis_docker() {
    log "Installing Redis using Docker..."
    install_docker
    
    # Pull Redis Stack image
    sudo docker pull redis/redis-stack:latest
    
    # Create systemd service file
    sudo tee /etc/systemd/system/redis-stack-server.service <<EOF
[Unit]
Description=Redis Stack Server Container
After=docker.service
Requires=docker.service

[Service]
TimeoutStartSec=0
Restart=always
ExecStartPre=-/usr/bin/docker stop redis-stack
ExecStartPre=-/usr/bin/docker rm redis-stack
ExecStart=/usr/bin/docker run --rm --name redis-stack \
    -p 6379:6379 \
    -p 8001:8001 \
    redis/redis-stack:latest
ExecStop=/usr/bin/docker stop redis-stack

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable redis-stack-server
    sudo systemctl start redis-stack-server
    
    log "Redis Stack container service created and started. Access Redis Insight at http://localhost:8001"
    log "You can now use: systemctl {start|stop|restart|status} redis-stack-server"
}

# Function to install Redis on RHEL-based systems
install_redis_rhel() {
    log "Installing Redis on RHEL-based system..."
    
    # Install EPEL if RHEL 9
    if [[ "$1" == "rhel" ]]; then
        log "Installing EPEL repository..."
        sudo dnf -y install epel-release
    fi

    # Add Redis repository
    sudo tee /etc/yum.repos.d/redis.repo <<EOF
[Redis]
name=Redis
baseurl=https://packages.redis.io/rpm/rhel9
enabled=1
gpgcheck=1
gpgkey=https://packages.redis.io/gpg
EOF

    # Install Redis
    sudo dnf install -y redis-stack-server

    # Enable and start service
    sudo systemctl enable redis-stack-server
    sudo systemctl start redis-stack-server
    
    log "Redis installation completed. Checking service status..."
    sudo systemctl status redis-stack-server
}

# Function to install Redis on Debian-based systems
install_redis_debian() {
    log "Installing Redis on Debian-based system..."
    
    # Install prerequisites
    sudo apt-get update
    sudo apt-get install -y lsb-release curl gpg

    # Add Redis repository
    curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
    sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | \
        sudo tee /etc/apt/sources.list.d/redis.list

    # Install Redis
    sudo apt-get update
    sudo apt-get install -y redis-stack-server

    # Enable and start service
    sudo systemctl enable redis-stack-server
    sudo systemctl start redis-stack-server
    
    log "Redis installation completed. Checking service status..."
    sudo systemctl status redis-stack-server
}

# Main installation logic
main() {
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        log "This script must be run as root or with sudo"
        exit 1
    fi

    # Detect OS
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        os_type="$ID"
        os_version="$VERSION_ID"
    else
        log "Cannot detect OS type"
        exit 1
    fi

    log "Detected OS: $os_type $os_version"

    # Installation path decision
    case "$os_type" in
        "rhel"|"rocky"|"almalinux"|"amzn")
            if check_arch; then
                install_redis_rhel "$os_type"
            else
                install_redis_docker
            fi
            ;;
        "ubuntu"|"debian"|"linuxmint"|"elementary"|"kali"|"pop")
            if [[ "$os_type" == "ubuntu" && "$os_version" > "22.04" ]]; then
                log "Ubuntu version > 22.04 detected. Using Docker installation."
                install_redis_docker
            elif [[ "$os_type" == "debian" && "$os_version" > "11" ]]; then
                log "Debian version > 11 detected. Using Docker installation."
                install_redis_docker
            else
                if check_arch; then
                    install_redis_debian
                else
                    install_redis_docker
                fi
            fi
            ;;
        *)
            log "Unsupported OS type. Using Docker installation."
            install_redis_docker
            ;;
    esac
}

# Run main function
main "$@"
