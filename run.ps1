# Photocopy That Lied - Startup Script
# This script starts the FastAPI backend (serves React production build if available)
# Optionally starts React dev server for development

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
    $devServerPort = 5173

    $backendRunning = Test-OurServiceRunning -Port $backendPort -ServiceName "Backend"
    $devServerRunning = Test-OurServiceRunning -Port $devServerPort -ServiceName "React Dev Server"

    if ($backendRunning) {
        Write-ColorOutput "[INFO] Backend already running on port $backendPort" "Cyan"
    }

    if ($devServerRunning) {
        Write-ColorOutput "[INFO] React dev server already running on port $devServerPort" "Cyan"
    }

    # Check if ports are occupied by other services
    if (-not $backendRunning -and (Test-PortInUse -Port $backendPort)) {
        Write-ColorOutput "[ERROR] Port $backendPort is already in use by another application." "Red"
        Write-ColorOutput "Please stop the other application or change the backend port." "Yellow"
        exit 1
    }

    if (-not $devServerRunning -and (Test-PortInUse -Port $devServerPort)) {
        Write-ColorOutput "[ERROR] Port $devServerPort is already in use by another application." "Red"
        Write-ColorOutput "Please stop the other application or change the dev server port." "Yellow"
        exit 1
    }

    # Check for production build
    $frontendDist = Join-Path $projectRoot "frontend\dist"
    $hasProductionBuild = Test-Path (Join-Path $frontendDist "index.html")

    if ($hasProductionBuild) {
        Write-ColorOutput "[INFO] React production build found" "Cyan"
        Write-ColorOutput "       FastAPI will serve the frontend at http://localhost:8000" "Cyan"
    }
    else {
        Write-ColorOutput "[INFO] React production build not found" "Yellow"
        Write-ColorOutput "       Will check for development mode" "Yellow"
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

    # Start React dev server if no production build and not already running
    $devServerProcess = $null
    if (-not $hasProductionBuild -and -not $devServerRunning) {
        Write-ColorOutput "[5/5] Starting React development server..." "Yellow"

        # Check if npm is available
        try {
            $npmVersion = npm --version 2>&1
            if ($LASTEXITCODE -ne 0) {
                throw "npm not available"
            }
        }
        catch {
            Write-ColorOutput "[WARNING] npm not available, cannot start React dev server" "Yellow"
            Write-ColorOutput "           Backend will serve API only at http://localhost:8000" "Yellow"
            $devServerProcess = $null
        }

        if ($devServerProcess -ne $null -or $LASTEXITCODE -eq 0) {
            $frontendDir = Join-Path $projectRoot "frontend"

            $devServerArgs = @(
                "run", "dev"
            )

            # Create temporary log files in the project root
            $devServerOutLog = Join-Path $projectRoot "dev_server_out.log"
            $devServerErrLog = Join-Path $projectRoot "dev_server_err.log"

            $devServerProcess = Start-Process -FilePath "npm" -ArgumentList $devServerArgs -WorkingDirectory $frontendDir -PassThru -WindowStyle Hidden -RedirectStandardOutput $devServerOutLog -RedirectStandardError $devServerErrLog

            if (-not $devServerProcess) {
                Write-ColorOutput "[ERROR] Failed to start React dev server." "Red"

                # Stop backend if we started it
                if ($backendProcess -and -not $backendProcess.HasExited) {
                    Stop-Process -Id $backendProcess.Id -Force
                }
                exit 1
            }

            Write-ColorOutput "[OK] React dev server started (PID: $($devServerProcess.Id))" "Green"
            Write-ColorOutput "     http://localhost:5173" "Cyan"
            Write-Host ""
        }
    }
    elseif ($hasProductionBuild) {
        Write-ColorOutput "[5/5] Production build available, skipping dev server..." "Yellow"
        Write-Host ""
    }
    else {
        Write-ColorOutput "[5/5] React dev server already running, skipping start..." "Yellow"
        Write-Host ""
    }

    # Print success message
    Write-ColorOutput "========================================" "Cyan"
    Write-ColorOutput "      APPLICATION READY" "Green"
    Write-ColorOutput "========================================" "Cyan"
    Write-Host ""

    if ($hasProductionBuild) {
        Write-ColorOutput "Frontend (Production):" "Cyan"
        Write-ColorOutput "http://localhost:8000" "White"
        Write-Host ""
    }
    elseif ($devServerProcess -or $devServerRunning) {
        Write-ColorOutput "Frontend (Development):" "Cyan"
        Write-ColorOutput "http://localhost:5173" "White"
        Write-Host ""
    }
    else {
        Write-ColorOutput "Frontend:" "Cyan"
        Write-ColorOutput "Not available (npm not found or no build)" "Yellow"
        Write-Host ""
    }

    Write-ColorOutput "Backend API:" "Cyan"
    Write-ColorOutput "http://localhost:8000/api" "White"
    Write-Host ""
    Write-ColorOutput "API Docs:" "Cyan"
    Write-ColorOutput "http://localhost:8000/docs" "White"
    Write-Host ""
    Write-ColorOutput "Press Ctrl+C to stop the application." "Yellow"
    Write-Host ""

    # Wait a moment for frontend to fully start
    Start-Sleep -Seconds 3

    # Open browser
    try {
        if ($hasProductionBuild) {
            Start-Process "http://localhost:8000"
        }
        elseif ($devServerProcess -or $devServerRunning) {
            Start-Process "http://localhost:5173"
        }
        else {
            Start-Process "http://localhost:8000/api"
        }
    }
    catch {
        Write-ColorOutput "[WARNING] Could not open browser automatically." "Yellow"
        if ($hasProductionBuild) {
            Write-ColorOutput "Please open http://localhost:8000 manually." "Yellow"
        }
        elseif ($devServerProcess -or $devServerRunning) {
            Write-ColorOutput "Please open http://localhost:5173 manually." "Yellow"
        }
        else {
            Write-ColorOutput "Please open http://localhost:8000/api manually." "Yellow"
        }
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

            if ($devServerProcess -and $devServerProcess.HasExited) {
                Write-ColorOutput "[WARNING] React dev server process exited unexpectedly" "Yellow"
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

        if ($devServerProcess -and -not $devServerProcess.HasExited) {
            try {
                Stop-Process -Id $devServerProcess.Id -Force -ErrorAction SilentlyContinue
                Write-ColorOutput "[OK] React dev server stopped" "Green"
            }
            catch {
                Write-ColorOutput "[WARNING] Could not stop React dev server gracefully" "Yellow"
            }
        }
        elseif ($devServerRunning) {
            Write-ColorOutput "[INFO] React dev server was already running, leaving it active" "Cyan"
        }

        Write-ColorOutput "Application stopped." "Green"
    }
}
catch {
    Write-ColorOutput "[ERROR] An unexpected error occurred: $_" "Red"
    exit 1
}
