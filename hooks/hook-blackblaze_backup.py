"""
PyInstaller hook to handle Windows API library warnings
"""
from PyInstaller.utils.hooks import collect_dynamic_libs

# Suppress warnings about Windows API libraries
def hook(hook_api):
    # These libraries are part of Windows and don't need to be bundled
    excluded_libs = [
        'api-ms-win-core-path-l1-1-0.dll',
        'api-ms-win-shcore-scaling-l1-1-1.dll',
        'api-ms-win-core-winrt-string-l1-1-0.dll',
        'api-ms-win-core-winrt-l1-1-0.dll',
        'api-ms-win-core-synch-l1-2-0.dll',
        'api-ms-win-core-sysinfo-l1-2-1.dll',
        'api-ms-win-core-processthreads-l1-1-2.dll',
    ]
    
    # Filter out problematic libraries from binaries
    if hasattr(hook_api, 'binaries'):
        filtered_binaries = []
        for binary in hook_api.binaries:
            if not any(excluded in binary[0] for excluded in excluded_libs):
                filtered_binaries.append(binary)
        hook_api.binaries = filtered_binaries
