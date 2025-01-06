#!/bin/bash

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Check if we're in the root of the git repository
REPO_ROOT_CHECK="$(git rev-parse --show-toplevel)"
if [ "$REPO_ROOT_CHECK" != "$(pwd)" ]; then
    echo "Error: Must run this script from the root of the git repository"
    echo "Current directory: $(pwd)"
    echo "Repository root: $REPO_ROOT_CHECK"
    exit 1
fi

REPO_ROOT="$(pwd)"
VENV_DIR="$REPO_ROOT/.venv"
CURRENT_DIR_MODE=false
PYTHON_COMMAND=""
APP_DIR=""
SERVICE_DESCRIPTION=""

# Handle different execution modes
if [ $# -eq 0 ]; then
    # No args - check for app.py in current directory
    if [ -f "app.py" ]; then
        CURRENT_DIR_MODE=true
        PYTHON_COMMAND="./app.py"
        SERVICE_DESCRIPTION="Flask application: $(basename "$(pwd)")"
        APP_DIR="."
    else
        echo "Error: No app.py found in current directory and no argument provided"
        exit 1
    fi
elif [ -f "$1" ] && [[ "$1" == *.py ]]; then
    # Direct .py file in current directory
    CURRENT_DIR_MODE=true
    PYTHON_COMMAND="./$1"
    SERVICE_DESCRIPTION="Flask application: $(basename "$(pwd)")"
    APP_DIR="."
else
    # Subdirectory mode
    APP_DIR="$1"
    if [ ! -d "$APP_DIR" ]; then
        echo "Error: Directory '$APP_DIR' does not exist"
        exit 1
    fi
    if [ ! -f "$APP_DIR/app.py" ]; then
        echo "Error: app.py not found in '$APP_DIR'"
        exit 1
    fi
    # Handle module path for Python, removing leading/trailing dots and normalizing separators
    MODULE_PATH=$(echo "$APP_DIR" | tr '/' '.' | sed 's/^\.//;s/\.$//;s/\.\.*/./g')
    PYTHON_COMMAND="-m ${MODULE_PATH}.app"
    SERVICE_DESCRIPTION="Flask application: $(basename "$APP_DIR")"
fi

# Check for .env file
if [ "$CURRENT_DIR_MODE" = true ]; then
    ENV_FILE=".env"
else
    ENV_FILE="$APP_DIR/.env"
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found at '$ENV_FILE'"
    exit 1
fi

# Determine if running as root
if [ "$EUID" -eq 0 ]; then
    SYSTEMD_DIR="/etc/systemd/system"
    echo "Running as root - installing system-wide service"
else
    SYSTEMD_DIR="$HOME/.config/systemd/user"
    echo "Running as user - installing user service"
    # Create user systemd directory if it doesn't exist
    mkdir -p "$SYSTEMD_DIR"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        exit 1
    fi
fi

# Install requirements
echo "Installing requirements..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$REPO_ROOT/requirements.txt"
if [ $? -ne 0 ]; then
    echo "Error: Failed to install requirements"
    exit 1
fi

# Create service name
if [ "$CURRENT_DIR_MODE" = true ]; then
    SERVICE_NAME="flask-$(basename "$PYTHON_COMMAND" .py)"
else
    # Remove any trailing slashes and get the base name
    SERVICE_NAME="flask-$(basename "$APP_DIR" | tr -d '/')"
fi

# Create systemd service file
SERVICE_FILE="$SYSTEMD_DIR/$SERVICE_NAME.service"

# Construct the ExecStart command
if [ "$CURRENT_DIR_MODE" = true ]; then
    EXEC_START="$VENV_DIR/bin/python3 $PYTHON_COMMAND"
else
    EXEC_START="$VENV_DIR/bin/python3 $PYTHON_COMMAND"
fi

cat > "$SERVICE_FILE" << EOL
[Unit]
Description=$SERVICE_DESCRIPTION
After=network.target

[Service]
Type=simple
WorkingDirectory=$REPO_ROOT/$APP_DIR
Environment=PYTHONPATH=$REPO_ROOT
EnvironmentFile=$REPO_ROOT/$ENV_FILE
ExecStart=$EXEC_START
Restart=always
RestartSec=10

[Install]
WantedBy=$([ "$EUID" -eq 0 ] && echo "multi-user.target" || echo "default.target")
EOL

if [ $? -ne 0 ]; then
    echo "Error: Failed to create service file"
    exit 1
fi

# Set appropriate permissions for the service file
if [ "$EUID" -eq 0 ]; then
    chmod 644 "$SERVICE_FILE"
fi

# Reload systemd daemon
if [ "$EUID" -eq 0 ]; then
    systemctl daemon-reload
else
    systemctl --user daemon-reload
fi

# Enable and start the service
if [ "$EUID" -eq 0 ]; then
    echo "Enabling and starting system service..."
    systemctl enable "$SERVICE_NAME"
    systemctl start "$SERVICE_NAME"
    echo "Service status:"
    systemctl status "$SERVICE_NAME"
else
    echo "Enabling and starting user service..."
    systemctl --user enable "$SERVICE_NAME"
    systemctl --user start "$SERVICE_NAME"
    echo "Service status:"
    systemctl --user status "$SERVICE_NAME"
fi

echo "Installation complete!"
echo "To check service status: $([ "$EUID" -eq 0 ] && echo "systemctl status $SERVICE_NAME" || echo "systemctl --user status $SERVICE_NAME")"
echo "To view logs: $([ "$EUID" -eq 0 ] && echo "journalctl -u $SERVICE_NAME" || echo "journalctl --user -u $SERVICE_NAME")"
