#!/bin/bash
# Windows VM Testing Setup Script
# This script sets up a Windows VM for local testing

echo "Setting up Windows VM for BlackBlaze B2 Backup Tool testing..."

# Check if VirtualBox is installed
if ! command -v vboxmanage &> /dev/null; then
    echo "VirtualBox not found. Installing VirtualBox..."
    sudo apt update
    sudo apt install -y virtualbox virtualbox-ext-pack
fi

# Check if Vagrant is installed
if ! command -v vagrant &> /dev/null; then
    echo "Vagrant not found. Installing Vagrant..."
    wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
    sudo apt update
    sudo apt install -y vagrant
fi

# Create Windows VM directory
mkdir -p windows-vm-testing
cd windows-vm-testing

# Create Vagrantfile for Windows 11
cat > Vagrantfile << 'EOF'
Vagrant.configure("2") do |config|
  config.vm.box = "gusztavvargadr/windows-11"
  config.vm.guest = :windows
  config.vm.communicator = "winrm"

  config.vm.network "forwarded_port", guest: 3389, host: 3389, id: "rdp", auto_correct: true
  config.vm.network "forwarded_port", guest: 5985, host: 5985, id: "winrm", auto_correct: true

  config.vm.provider "virtualbox" do |vb|
    vb.gui = true
    vb.memory = "4096"
    vb.cpus = 2
    vb.name = "BlackBlaze-Windows-Testing"
  end

  config.vm.provision "shell", inline: <<-SHELL
    # Install Python 3.12
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe" -OutFile "python-installer.exe"
    Start-Process -FilePath "python-installer.exe" -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait

    # Install Git
    Invoke-WebRequest -Uri "https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.2/Git-2.42.0.2-64-bit.exe" -OutFile "git-installer.exe"
    Start-Process -FilePath "git-installer.exe" -ArgumentList "/SILENT" -Wait

    # Install Visual Studio Build Tools
    Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vs_buildtools.exe" -OutFile "vs-buildtools.exe"
    Start-Process -FilePath "vs-buildtools.exe" -ArgumentList "--quiet", "--wait", "--add", "Microsoft.VisualStudio.Workload.VCTools" -Wait

    # Install uv
    Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -OutFile "install-uv.ps1"
    PowerShell -ExecutionPolicy Bypass -File "install-uv.ps1"

    # Create testing directory
    New-Item -ItemType Directory -Path "C:\blackblaze-testing" -Force

    # Copy test scripts
    Copy-Item -Path "C:\vagrant\scripts\*" -Destination "C:\blackblaze-testing\" -Recurse -Force

    Write-Host "Windows VM setup completed successfully!"
  SHELL
end
EOF

# Create scripts directory
mkdir -p scripts

# Copy our Windows testing scripts
cp ../scripts/windows_error_collector.py scripts/
cp ../scripts/windows_test_suite.py scripts/

# Create Windows test runner script
cat > scripts/run_windows_tests.ps1 << 'EOF'
# Windows Test Runner for BlackBlaze B2 Backup Tool
# This script runs comprehensive tests on Windows

Write-Host "Starting BlackBlaze B2 Backup Tool Windows Testing..." -ForegroundColor Green

# Set error action preference
$ErrorActionPreference = "Continue"

# Function to run test
function Run-Test {
    param(
        [string]$TestName,
        [scriptblock]$TestScript
    )

    Write-Host "Running test: $TestName" -ForegroundColor Yellow

    try {
        $result = & $TestScript
        if ($result) {
            Write-Host "✓ $TestName PASSED" -ForegroundColor Green
            return $true
        } else {
            Write-Host "✗ $TestName FAILED" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "✗ $TestName ERROR: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Test 1: Check if executable exists
$Test1 = Run-Test "Executable Exists" {
    Test-Path "C:\blackblaze-testing\dist\BlackBlaze-Backup-Tool.exe"
}

# Test 2: Test single instance protection
$Test2 = Run-Test "Single Instance Protection" {
    $proc1 = Start-Process -FilePath "C:\blackblaze-testing\dist\BlackBlaze-Backup-Tool.exe" -PassThru
    Start-Sleep -Seconds 3

    $proc2 = Start-Process -FilePath "C:\blackblaze-testing\dist\BlackBlaze-Backup-Tool.exe" -PassThru
    Start-Sleep -Seconds 2

    $result = $proc2.HasExited
    $proc1.Kill()
    if ($proc2.HasExited -eq $false) { $proc2.Kill() }

    return $result
}

# Test 3: Test system tray
$Test3 = Run-Test "System Tray" {
    $proc = Start-Process -FilePath "C:\blackblaze-testing\dist\BlackBlaze-Backup-Tool.exe" -PassThru
    Start-Sleep -Seconds 5

    $result = -not $proc.HasExited
    $proc.Kill()

    return $result
}

# Test 4: Test window focus
$Test4 = Run-Test "Window Focus" {
    $proc = Start-Process -FilePath "C:\blackblaze-testing\dist\BlackBlaze-Backup-Tool.exe" -PassThru
    Start-Sleep -Seconds 3

    Add-Type -TypeDefinition @"
        using System;
        using System.Runtime.InteropServices;
        public class Win32 {
            [DllImport("user32.dll")]
            public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
            [DllImport("user32.dll")]
            public static extern bool SetForegroundWindow(IntPtr hWnd);
        }
"@

    $hwnd = [Win32]::FindWindow($null, "BlackBlaze B2 Backup Tool")
    $result = $hwnd -ne [IntPtr]::Zero

    if ($result) {
        [Win32]::SetForegroundWindow($hwnd)
    }

    $proc.Kill()
    return $result
}

# Generate test report
$TestResults = @{
    "Executable Exists" = $Test1
    "Single Instance Protection" = $Test2
    "System Tray" = $Test3
    "Window Focus" = $Test4
}

$PassedTests = ($TestResults.Values | Where-Object { $_ -eq $true }).Count
$TotalTests = $TestResults.Count

Write-Host "`nTest Results Summary:" -ForegroundColor Cyan
Write-Host "Passed: $PassedTests/$TotalTests" -ForegroundColor $(if ($PassedTests -eq $TotalTests) { "Green" } else { "Red" })

foreach ($test in $TestResults.GetEnumerator()) {
    $status = if ($test.Value) { "PASSED" } else { "FAILED" }
    $color = if ($test.Value) { "Green" } else { "Red" }
    Write-Host "  $($test.Key): $status" -ForegroundColor $color
}

# Save results to file
$TestResults | ConvertTo-Json | Out-File -FilePath "C:\blackblaze-testing\test_results.json" -Encoding UTF8

Write-Host "`nTest results saved to C:\blackblaze-testing\test_results.json" -ForegroundColor Cyan
Write-Host "Windows testing completed!" -ForegroundColor Green
EOF

echo "Windows VM testing setup completed!"
echo ""
echo "To start Windows VM testing:"
echo "1. cd windows-vm-testing"
echo "2. vagrant up"
echo "3. vagrant rdp (to connect via RDP)"
echo "4. Run tests in the VM"
echo ""
echo "To stop the VM:"
echo "vagrant halt"
echo ""
echo "To destroy the VM:"
echo "vagrant destroy"
