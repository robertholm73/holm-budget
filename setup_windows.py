#!/usr/bin/env python3
"""
Setup script to run desktop_app.py in Windows PowerShell
This bypasses WSL2/Qt issues entirely
"""
import subprocess
import sys
import os
from pathlib import Path

def check_python():
    """Check if Python is available in Windows"""
    try:
        result = subprocess.run(['python', '--version'], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✓ Windows Python found: {result.stdout.strip()}")
            return True
    except:
        pass
    
    try:
        result = subprocess.run(['py', '--version'], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✓ Windows Python (py) found: {result.stdout.strip()}")
            return True
    except:
        pass
    
    print("✗ Python not found in Windows PATH")
    print("Please install Python for Windows from https://python.org")
    return False

def check_pyside6():
    """Check if PySide6 is installed in Windows Python"""
    try:
        result = subprocess.run(['python', '-c', 'import PySide6; print("PySide6 version:", PySide6.__version__)'], 
                              capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✓ PySide6 found: {result.stdout.strip()}")
            return True
    except:
        pass
    
    try:
        result = subprocess.run(['py', '-c', 'import PySide6; print("PySide6 version:", PySide6.__version__)'], 
                              capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✓ PySide6 found: {result.stdout.strip()}")
            return True
    except:
        pass
    
    print("✗ PySide6 not found in Windows Python")
    return False

def check_pg8000():
    """Check if pg8000 is installed in Windows Python"""
    try:
        result = subprocess.run(['python', '-c', 'import pg8000; print("pg8000 available")'], 
                              capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print("✓ pg8000 found")
            return True
    except:
        pass
    
    try:
        result = subprocess.run(['py', '-c', 'import pg8000; print("pg8000 available")'], 
                              capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print("✓ pg8000 found")
            return True
    except:
        pass
    
    print("✗ pg8000 not found in Windows Python")
    return False

def install_requirements():
    """Install required packages in Windows Python"""
    print("\nInstalling required packages...")
    
    packages = ['PySide6', 'pg8000']
    
    for package in packages:
        print(f"Installing {package}...")
        try:
            result = subprocess.run(['python', '-m', 'pip', 'install', package], 
                                  capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                print(f"✓ {package} installed successfully")
            else:
                print(f"✗ Failed to install {package}: {result.stderr}")
                # Try with py instead
                result = subprocess.run(['py', '-m', 'pip', 'install', package], 
                                      capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    print(f"✓ {package} installed successfully (using py)")
                else:
                    print(f"✗ Failed to install {package} with py: {result.stderr}")
        except Exception as e:
            print(f"✗ Error installing {package}: {e}")

def create_windows_launcher():
    """Create a Windows batch file to launch the app"""
    
    # Get the Windows path to the current directory
    current_dir = Path.cwd()
    windows_path = str(current_dir).replace('/mnt/c/', 'C:\\').replace('/', '\\')
    
    batch_content = f'''@echo off
cd /d "{windows_path}"
echo Starting Budget Desktop App...
echo.
python desktop_app.py
if errorlevel 1 (
    echo.
    echo Failed to run with 'python', trying 'py'...
    py desktop_app.py
)
pause
'''
    
    batch_file = current_dir / 'run_desktop_windows.bat'
    with open(batch_file, 'w') as f:
        f.write(batch_content)
    
    print(f"✓ Created Windows launcher: {batch_file}")
    print(f"✓ Windows path: {windows_path}")
    
    return windows_path

def create_powershell_launcher():
    """Create a PowerShell script to launch the app"""
    
    current_dir = Path.cwd()
    windows_path = str(current_dir).replace('/mnt/c/', 'C:\\').replace('/', '\\')
    
    ps1_content = f'''# Budget Desktop App Launcher
Set-Location "{windows_path}"
Write-Host "Starting Budget Desktop App..." -ForegroundColor Green
Write-Host ""

try {{
    python desktop_app.py
}} catch {{
    Write-Host "Failed to run with 'python', trying 'py'..." -ForegroundColor Yellow
    py desktop_app.py
}}

Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
'''
    
    ps1_file = current_dir / 'run_desktop_windows.ps1'
    with open(ps1_file, 'w') as f:
        f.write(ps1_content)
    
    print(f"✓ Created PowerShell launcher: {ps1_file}")
    return windows_path

if __name__ == '__main__':
    print("Setting up Budget Desktop App for Windows...")
    print("=" * 50)
    
    if not check_python():
        sys.exit(1)
    
    needs_install = []
    if not check_pyside6():
        needs_install.append('PySide6')
    if not check_pg8000():
        needs_install.append('pg8000')
    
    if needs_install:
        print(f"\nMissing packages: {', '.join(needs_install)}")
        install_requirements()
    
    windows_path = create_windows_launcher()
    create_powershell_launcher()
    
    print("\n" + "=" * 50)
    print("✓ Setup complete!")
    print("\nTo run the app in Windows:")
    print("1. Open PowerShell as Administrator")
    print("2. Navigate to your project folder:")
    print(f"   cd '{windows_path}'")
    print("3. Run the app:")
    print("   python desktop_app.py")
    print("\nOr double-click: run_desktop_windows.bat")
    print("Or run in PowerShell: .\\run_desktop_windows.ps1")