#!/usr/bin/env node

/**
 * Photocopy That Lied - Development Startup Script
 * 
 * This script automatically:
 * 1. Checks for .venv Python environment
 * 2. Checks if backend is already running on port 8000
 * 3. Starts backend if not running
 * 4. Waits for backend health check
 * 5. Starts Vite frontend
 */

const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const VENV_PYTHON = path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe');

// Handle both Windows and Unix-style paths
const getVenvPython = () => {
  if (process.platform === 'win32') {
    return path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe');
  } else {
    return path.join(PROJECT_ROOT, '.venv', 'bin', 'python');
  }
};
const BACKEND_PORT = 8000;
const FRONTEND_PORT = 5173;
const HEALTH_CHECK_URL = `http://127.0.0.1:${BACKEND_PORT}/api/health`;
const MAX_HEALTH_CHECK_ATTEMPTS = 20;
const HEALTH_CHECK_INTERVAL = 3000;

let backendProcess = null;
let frontendProcess = null;

// ANSI color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

function checkPortInUse(port) {
  return new Promise((resolve) => {
    const server = http.createServer();
    server.once('error', () => {
      resolve(true);
    });
    server.once('listening', () => {
      server.close();
      resolve(false);
    });
    server.listen(port);
  });
}

function checkBackendHealth() {
  return new Promise((resolve) => {
    http.get(HEALTH_CHECK_URL, (res) => {
      if (res.statusCode === 200) {
        resolve(true);
      } else {
        resolve(false);
      }
    }).on('error', () => {
      resolve(false);
    });
  });
}

async function waitForBackendHealth() {
  log('Waiting for backend health check...', colors.cyan);
  
  for (let i = 0; i < MAX_HEALTH_CHECK_ATTEMPTS; i++) {
    const isHealthy = await checkBackendHealth();
    if (isHealthy) {
      log('Backend health check passed', colors.green);
      return true;
    }
    process.stdout.write('.');
    await new Promise(resolve => setTimeout(resolve, HEALTH_CHECK_INTERVAL));
  }
  
  console.log('');
  return false;
}

function startBackend() {
  return new Promise((resolve, reject) => {
    log('Starting FastAPI backend...', colors.yellow);
    
    const venvPython = getVenvPython();
    const backendArgs = [
      '-m', 'uvicorn',
      'backend.main:app',
      '--reload',
      '--port', BACKEND_PORT.toString()
    ];

    backendProcess = spawn(venvPython, backendArgs, {
      cwd: PROJECT_ROOT,
      stdio: 'inherit',
      shell: true
    });

    backendProcess.on('error', (err) => {
      log(`Failed to start backend: ${err.message}`, colors.red);
      reject(err);
    });

    backendProcess.on('exit', (code) => {
      if (code !== 0 && code !== null) {
        log(`Backend exited with code ${code}`, colors.red);
      }
    });

    // Give it a moment to start
    setTimeout(() => {
      log(`Backend started (PID: ${backendProcess.pid})`, colors.green);
      log(`http://127.0.0.1:${BACKEND_PORT}`, colors.cyan);
      resolve();
    }, 1000);
  });
}

function startFrontend() {
  return new Promise((resolve, reject) => {
    log('Starting Vite frontend...', colors.yellow);
    
    const frontendDir = path.join(PROJECT_ROOT, 'frontend');
    
    frontendProcess = spawn('npm', ['run', 'dev'], {
      cwd: frontendDir,
      stdio: 'inherit',
      shell: true
    });

    frontendProcess.on('error', (err) => {
      log(`Failed to start frontend: ${err.message}`, colors.red);
      reject(err);
    });

    frontendProcess.on('exit', (code) => {
      if (code !== 0 && code !== null) {
        log(`Frontend exited with code ${code}`, colors.red);
      }
    });

    // Give it a moment to start
    setTimeout(() => {
      log(`Frontend started (PID: ${frontendProcess.pid})`, colors.green);
      log(`http://127.0.0.1:${FRONTEND_PORT}`, colors.cyan);
      resolve();
    }, 2000);
  });
}

function cleanup() {
  log('\nShutting down...', colors.yellow);
  
  if (backendProcess) {
    log('Stopping backend...', colors.yellow);
    backendProcess.kill('SIGTERM');
  }
  
  if (frontendProcess) {
    log('Stopping frontend...', colors.yellow);
    frontendProcess.kill('SIGTERM');
  }
  
  log('Shutdown complete', colors.green);
  process.exit(0);
}

async function main() {
  log('========================================', colors.cyan);
  log('      PHOTOCOPY THAT LIED', colors.cyan);
  log('      Starting Development', colors.cyan);
  log('========================================', colors.cyan);
  console.log('');

  // Check for .venv
  log('[1/5] Checking virtual environment...', colors.yellow);
  const venvPython = getVenvPython();
  if (!fs.existsSync(venvPython)) {
    log('[ERROR] Virtual environment not found', colors.red);
    log('Create it with: python -m venv .venv', colors.yellow);
    log('Then install dependencies: .venv/Scripts/python.exe -m pip install -r requirements.txt', colors.yellow);
    process.exit(1);
  }
  log('[OK] .venv found', colors.green);
  console.log('');

  // Check ports
  log('[2/5] Checking ports...', colors.yellow);
  const backendPortInUse = await checkPortInUse(BACKEND_PORT);
  const frontendPortInUse = await checkPortInUse(FRONTEND_PORT);

  if (backendPortInUse) {
    const isOurBackend = await checkBackendHealth();
    if (isOurBackend) {
      log('[INFO] Backend already running on port 8000', colors.cyan);
    } else {
      log('[ERROR] Port 8000 is in use by another application', colors.red);
      process.exit(1);
    }
  }

  if (frontendPortInUse) {
    log('[INFO] Port 5173 is in use, Vite will choose another port', colors.cyan);
  }
  console.log('');

  // Start backend if not running
  if (!backendPortInUse) {
    log('[3/5] Starting backend...', colors.yellow);
    await startBackend();
    console.log('');

    log('[4/5] Waiting for backend health check...', colors.yellow);
    const isHealthy = await waitForBackendHealth();
    if (!isHealthy) {
      log('[ERROR] Backend failed to start or health check failed', colors.red);
      if (backendProcess) {
        backendProcess.kill('SIGTERM');
      }
      process.exit(1);
    }
    console.log('');
  } else {
    log('[3/5] Backend already running, skipping start...', colors.yellow);
    log('[4/5] Backend health check skipped (already running)', colors.yellow);
    console.log('');
  }

  // Start frontend
  log('[5/5] Starting frontend...', colors.yellow);
  await startFrontend();
  console.log('');

  // Success message
  log('========================================', colors.cyan);
  log('      DEVELOPMENT READY', colors.green);
  log('========================================', colors.cyan);
  console.log('');
  log('Frontend:', colors.cyan);
  log(`http://127.0.0.1:${FRONTEND_PORT}`, colors.reset);
  console.log('');
  log('Backend API:', colors.cyan);
  log(`http://127.0.0.1:${BACKEND_PORT}/api`, colors.reset);
  console.log('');
  log('API Docs:', colors.cyan);
  log(`http://127.0.0.1:${BACKEND_PORT}/docs`, colors.reset);
  console.log('');
  log('Press Ctrl+C to stop', colors.yellow);
  console.log('');

  // Handle cleanup on exit
  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);

  // Keep the process running
  process.stdin.resume();
}

main().catch((err) => {
  log(`Fatal error: ${err.message}`, colors.red);
  process.exit(1);
});
