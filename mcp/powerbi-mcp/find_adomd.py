"""
Script to find ADOMD.NET DLL on Windows system
Run this to locate ADOMD.NET libraries for XMLA connectivity
"""
import os
import sys
from pathlib import Path

def search_adomd_dll():
    """Search for ADOMD.NET DLL in common locations"""
    print("=" * 70)
    print(" Searching for ADOMD.NET DLL...")
    print("=" * 70)
    
    possible_paths = [
        # ADOMD.NET standalone installation (common location)
        Path(r"C:\Program Files\Microsoft.NET\ADOMD.NET\160"),
        Path(r"C:\Program Files\Microsoft.NET\ADOMD.NET\150"),
        Path(r"C:\Program Files\Microsoft.NET\ADOMD.NET\140"),
        Path(r"C:\Program Files (x86)\Microsoft.NET\ADOMD.NET\160"),
        Path(r"C:\Program Files (x86)\Microsoft.NET\ADOMD.NET\150"),
        Path(r"C:\Program Files (x86)\Microsoft.NET\ADOMD.NET\140"),
        # NuGet package locations
        Path(os.path.expandvars(r"%USERPROFILE%\.nuget\packages\microsoft.analysisservices.adomdclient.retail.amd64")),
        Path(os.path.expandvars(r"%USERPROFILE%\.nuget\packages\microsoft.analysisservices.adomdclient")),
        # SQL Server Management Studio installations
        Path(r"C:\Program Files\Microsoft SQL Server\160\SDK\Assemblies"),
        Path(r"C:\Program Files\Microsoft SQL Server\150\SDK\Assemblies"),
        Path(r"C:\Program Files\Microsoft SQL Server\140\SDK\Assemblies"),
        Path(r"C:\Program Files\Microsoft SQL Server\130\SDK\Assemblies"),
        # x86 versions
        Path(r"C:\Program Files (x86)\Microsoft SQL Server\160\SDK\Assemblies"),
        Path(r"C:\Program Files (x86)\Microsoft SQL Server\150\SDK\Assemblies"),
        Path(r"C:\Program Files (x86)\Microsoft SQL Server\140\SDK\Assemblies"),
        Path(r"C:\Program Files (x86)\Microsoft SQL Server\130\SDK\Assemblies"),
        # Power BI Desktop (if installed)
        Path(r"C:\Program Files\Microsoft Power BI Desktop\bin"),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Power BI Desktop\bin")),
        # Windows Store Power BI
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps")),
    ]
    
    # Search Update Cache
    update_cache_paths = [
        Path(r"C:\Program Files\Microsoft SQL Server\160\Setup Bootstrap\Update Cache"),
        Path(r"C:\Program Files\Microsoft SQL Server\150\Setup Bootstrap\Update Cache"),
    ]
    
    for cache_path in update_cache_paths:
        if cache_path.exists():
            update_folders = list(cache_path.glob("*/GDR/x64"))
            if update_folders:
                possible_paths.extend(sorted(update_folders))
    
    # Also search Program Files recursively (slower but thorough)
    print("\nChecking common installation paths...")
    found_paths = []
    
    for path in possible_paths:
        if path.exists():
            dll_file = path / "Microsoft.AnalysisServices.AdomdClient.dll"
            if dll_file.exists():
                print(f"✅ FOUND: {dll_file}")
                found_paths.append(path)
            else:
                print(f"  ⚠️  Path exists but DLL not found: {path}")
        else:
            print(f"  ❌ Not found: {path}")
    
    # Recursive search in Program Files (if nothing found)
    if not found_paths:
        print("\n" + "=" * 70)
        print(" Performing recursive search in Program Files...")
        print(" (This may take a minute)")
        print("=" * 70)
        
        search_dirs = [
            Path(r"C:\Program Files\Microsoft.NET"),  # ADOMD.NET standalone installation
            Path(r"C:\Program Files (x86)\Microsoft.NET"),  # ADOMD.NET standalone installation (x86)
            Path(r"C:\Program Files\Microsoft SQL Server"),
            Path(r"C:\Program Files (x86)\Microsoft SQL Server"),
            Path(r"C:\Program Files\Microsoft Power BI Desktop"),
        ]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                print(f"\nSearching in: {search_dir}")
                for dll_file in search_dir.rglob("Microsoft.AnalysisServices.AdomdClient.dll"):
                    print(f"✅ FOUND: {dll_file}")
                    found_paths.append(dll_file.parent)
    
    print("\n" + "=" * 70)
    if found_paths:
        print(f"✅ Found {len(found_paths)} location(s) with ADOMD.NET DLL:")
        for path in found_paths:
            print(f"   {path}")
        print("\nThe code should automatically detect these paths.")
    else:
        print("❌ ADOMD.NET DLL not found!")
        print("\n📥 To install ADOMD.NET, choose one of the following:")
        print("\n1. Install SQL Server Management Studio (SSMS) - Recommended")
        print("   Download: https://aka.ms/ssmsfullsetup")
        print("   (This includes ADOMD.NET libraries)")
        print("\n2. Install ADOMD.NET Redistributable")
        print("   Download: https://docs.microsoft.com/sql/analysis-services/client-libraries")
        print("\n3. Install via NuGet (for development)")
        print("   Run: nuget install Microsoft.AnalysisServices.AdomdClient -OutputDirectory packages")
    print("=" * 70)
    
    return found_paths

if __name__ == "__main__":
    search_adomd_dll()

