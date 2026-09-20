# Photocopy That Lied - Startup Script
# This script starts both the FastAPI backend and Streamlit frontend

$ErrorActionPreference = "Stop"

# Function to write colored output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Function to check if a port is in use
function Test-PortInUse {
    param(
        [int]$Port
    )
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("localhost", $Port)
        $connection.Close()
        return $true
    }
    catch {
        return $false
    }
}

# Function to check if the port is used by our application
function Test-OurServiceRunning {
    param(
        [int]$Port,
        [string]$ServiceName
    )
    if (Test-PortInUse -Port $Port) {
        try {
            if ($Port -eq 8000) {
                $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
                if ($response.StatusCode -eq 200) {
                    return $true
                }
            }
            elseif ($Port -eq 8501) {
                $response = Invoke-WebRequest -Uri "http://localhost:8501" -UseBasicParsing -TimeoutSec 2
                if ($response.StatusCode -eq 200) {
                    return $true
                }
            }
        }
        catch {
            # Port is in use but not by our service
            return $false
        }
    }
    return $false
}

# Function to check backend health
function Test-BackendHealth {
    param(
        [int]$TimeoutSeconds = 60
    )
    $startTime = Get-Date
    $endTime = $startTime.AddSeconds($TimeoutSeconds)
    
    Write-ColorOutput "     Waiting for backend to be healthy..." "Cyan"
    
    while ((Get-Date) -lt $endTime) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                return $true
            }
        }
        catch {
            # Backend not ready yet
            Write-Host "." -NoNewline
        }
        Start-Sleep -Seconds 3
    }
    Write-Host ""
    return $false
}

# Main script
try {
    # Print header
    Write-ColorOutput "========================================" "Cyan"
    Write-ColorOutput "      PHOTOCOPY THAT LIED" "Cyan"
    Write-ColorOutput "      Starting Application" "Cyan"
    Write-ColorOutput "========================================" "Cyan"
    Write-Host ""

    # Get script directory (project root)
    $projectRoot = $PSScriptRoot
    if (-not $projectRoot) {
        $projectRoot = Get-Location
    }
    
    Write-ColorOutput "[1/5] Checking virtual environment..." "Yellow"
    
    # Check for .venv
    $venvPath = Join-Path $projectRoot ".venv"
    $pythonExe = Join-Path $venvPath "Scripts\python.exe"
    
    if (-not (Test-Path $venvPath)) {
        Write-ColorOutput "[ERROR] Virtual environment not found." "Red"
        Write-Host ""
        Write-ColorOutput "Create it with:" "Yellow"
        Write-Host "python -m venv .venv"
        Write-Host ""
        Write-ColorOutput "Then install dependencies:" "Yellow"
        Write-Host ".venv\Scripts\python.exe -m pip install -r requirements.txt"
        exit 1
    }
    
    if (-not (Test-Path $pythonExe)) {
        Write-ColorOutput "[ERROR] Python executable not found in .venv" "Red"
        exit 1
    }
    
    Write-ColorOutput "[OK] .venv found" "Green"
    Write-Host ""

    # Check ports
    Write-ColorOutput "[2/5] Checking ports..." "Yellow"
    
    $backendPort = 8000
    $frontendPort = 8501
    
    $backendRunning = Test-OurServiceRunning -Port $backendPort -ServiceName "Backend"
    $frontendRunning = Test-OurServiceRunning -Port $frontendPort -ServiceName "Frontend"
    
    if ($backendRunning) {
        Write-ColorOutput "[INFO] Backend already running on port $backendPort" "Cyan"
    }
    
    if ($frontendRunning) {
        Write-ColorOutput "[INFO] Streamlit already running on port $frontendPort" "Cyan"
    }
    
    # Check if ports are occupied by other services
    if (-not $backendRunning -and (Test-PortInUse -Port $backendPort)) {
        Write-ColorOutput "[ERROR] Port $backendPort is already in use by another application." "Red"
        Write-ColorOutput "Please stop the other application or change the backend port." "Yellow"
        exit 1
    }
    
    if (-not $frontendRunning -and (Test-PortInUse -Port $frontendPort)) {
        Write-ColorOutput "[ERROR] Port $frontendPort is already in use by another application." "Red"
        Write-ColorOutput "Please stop the other application or change the Streamlit port." "Yellow"
        exit 1
    }
    
    Write-Host ""

    # Start backend if not running
    $backendProcess = $null
    if (-not $backendRunning) {
        Write-ColorOutput "[3/5] Starting FastAPI backend..." "Yellow"
        
        $backendArgs = @(
            "-m", "uvicorn",
            "backend.main:app",
            "--host", "0.0.0.0",
            "--port", "8000"
        )
        
        # Create temporary log files in the project root
        $backendOutLog = Join-Path $projectRoot "backend_startup_out.log"
        $backendErrLog = Join-Path $projectRoot "backend_startup_err.log"
        
        $backendProcess = Start-Process -FilePath $pythonExe -ArgumentList $backendArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput $backendOutLog -RedirectStandardError $backendErrLog
        
        if (-not $backendProcess) {
            Write-ColorOutput "[ERROR] Failed to start backend process." "Red"
            exit 1
        }
        
        Write-ColorOutput "[OK] Backend started (PID: $($backendProcess.Id))" "Green"
        Write-ColorOutput "     http://localhost:8000" "Cyan"
        Write-Host ""
        
        # Wait for backend to be healthy
        Write-ColorOutput "[4/5] Waiting for backend health check..." "Yellow"
        
        if (-not (Test-BackendHealth -TimeoutSeconds 60)) {
            Write-ColorOutput "[ERROR] Backend failed to start or health check failed." "Red"
            Write-ColorOutput "Check the backend process for details." "Yellow"
            Write-ColorOutput "Logs: $backendOutLog, $backendErrLog" "Yellow"
            
            # Stop the backend process
            if ($backendProcess -and -not $backendProcess.HasExited) {
                Stop-Process -Id $backendProcess.Id -Force
            }
            exit 1
        }
        
        Write-ColorOutput "[OK] Backend health check passed" "Green"
        Write-Host ""
    }
    else {
        Write-ColorOutput "[4/5] Backend already running, skipping start..." "Yellow"
        Write-Host ""
    }

    # Start Streamlit if not running
    $frontendProcess = $null
    if (-not $frontendRunning) {
        Write-ColorOutput "[5/5] Starting Streamlit..." "Yellow"
        
        $frontendArgs = @(
            "-m", "streamlit",
            "run", "streamlit_app.py",
            "--server.port", "8501"
        )
        
        # Create temporary log files in the project root
        $streamlitOutLog = Join-Path $projectRoot "streamlit_startup_out.log"
        $streamlitErrLog = Join-Path $projectRoot "streamlit_startup_err.log"
        
        $frontendProcess = Start-Process -FilePath $pythonExe -ArgumentList $frontendArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput $streamlitOutLog -RedirectStandardError $streamlitErrLog
        
        if (-not $frontendProcess) {
            Write-ColorOutput "[ERROR] Failed to start Streamlit process." "Red"
            
            # Stop backend if we started it
            if ($backendProcess -and -not $backendProcess.HasExited) {
                Stop-Process -Id $backendProcess.Id -Force
            }
            exit 1
        }
        
        Write-ColorOutput "[OK] Streamlit started (PID: $($frontendProcess.Id))" "Green"
        Write-ColorOutput "     http://localhost:8501" "Cyan"
        Write-Host ""
    }
    else {
        Write-ColorOutput "[5/5] Streamlit already running, skipping start..." "Yellow"
        Write-Host ""
    }

    # Print success message
    Write-ColorOutput "========================================" "Cyan"
    Write-ColorOutput "      APPLICATION READY" "Green"
    Write-ColorOutput "========================================" "Cyan"
    Write-Host ""
    Write-ColorOutput "Frontend:" "Cyan"
    Write-ColorOutput "http://localhost:8501" "White"
    Write-Host ""
    Write-ColorOutput "Backend:" "Cyan"
    Write-ColorOutput "http://localhost:8000" "White"
    Write-Host ""
    Write-ColorOutput "API Docs:" "Cyan"
    Write-ColorOutput "http://localhost:8000/docs" "White"
    Write-Host ""
    Write-ColorOutput "Press Ctrl+C to stop the application." "Yellow"
    Write-Host ""

    # Wait a moment for Streamlit to fully start
    Start-Sleep -Seconds 3

    # Open browser
    try {
        Start-Process "http://localhost:8501"
    }
    catch {
        Write-ColorOutput "[WARNING] Could not open browser automatically." "Yellow"
        Write-ColorOutput "Please open http://localhost:8501 manually." "Yellow"
    }

    # Keep script running and handle Ctrl+C
    try {
        # Wait for processes to finish
        while ($true) {
            Start-Sleep -Seconds 1
            
            # Check if processes are still running
            if ($backendProcess -and $backendProcess.HasExited) {
                Write-ColorOutput "[WARNING] Backend process exited unexpectedly" "Yellow"
                break
            }
            
            if ($frontendProcess -and $frontendProcess.HasExited) {
                Write-ColorOutput "[WARNING] Streamlit process exited unexpectedly" "Yellow"
                break
            }
        }
    }
    catch [System.Management.Automation.PipelineStoppedException] {
        # Ctrl+C was pressed
    }
    finally {
        # Cleanup
        Write-Host ""
        Write-ColorOutput "Stopping Photocopy That Lied..." "Yellow"
        
        if ($backendProcess -and -not $backendProcess.HasExited) {
            try {
                Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
                Write-ColorOutput "[OK] Backend stopped" "Green"
            }
            catch {
                Write-ColorOutput "[WARNING] Could not stop backend gracefully" "Yellow"
            }
        }
        elseif ($backendRunning) {
            Write-ColorOutput "[INFO] Backend was already running, leaving it active" "Cyan"
        }
        
        if ($frontendProcess -and -not $frontendProcess.HasExited) {
            try {
                Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
                Write-ColorOutput "[OK] Streamlit stopped" "Green"
            }
            catch {
                Write-ColorOutput "[WARNING] Could not stop Streamlit gracefully" "Yellow"
            }
        }
        elseif ($frontendRunning) {
            Write-ColorOutput "[INFO] Streamlit was already running, leaving it active" "Cyan"
        }
        
        Write-ColorOutput "Application stopped." "Green"
    }
}
catch {
    Write-ColorOutput "[ERROR] An unexpected error occurred: $_" "Red"
    exit 1
}
