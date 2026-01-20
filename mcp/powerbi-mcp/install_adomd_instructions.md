# Installing ADOMD.NET for Power BI XMLA Connectivity

ADOMD.NET is required for XMLA endpoint connectivity. Here are your options:

## Option 1: Install SQL Server Management Studio (SSMS) - Recommended ✅

**Easiest and most reliable method**

1. Download SSMS from: https://aka.ms/ssmsfullsetup
2. Run the installer
3. ADOMD.NET will be installed automatically at:
   - `C:\Program Files\Microsoft SQL Server\160\SDK\Assemblies\Microsoft.AnalysisServices.AdomdClient.dll`

**Pros:**
- Includes ADOMD.NET automatically
- Also gives you SSMS (useful tool)
- Most reliable installation

**Cons:**
- Larger download (~500MB)
- Installs full SSMS (if you don't need it)

---

## Option 2: Download ADOMD.NET Redistributable

**Direct download of just ADOMD.NET**

1. Go to: https://docs.microsoft.com/sql/analysis-services/client-libraries
2. Download "Microsoft Analysis Services OLE DB Provider" or "ADOMD.NET"
3. Run the installer
4. DLL will be installed to Program Files

**Pros:**
- Smaller download
- Only installs what you need

**Cons:**
- May need to find the exact download link
- Less commonly used

---

## Option 3: Use NuGet Package (For Development)

**If you have NuGet CLI installed**

```powershell
# Create a packages directory
mkdir packages
cd packages

# Download the NuGet package
nuget install Microsoft.AnalysisServices.AdomdClient -OutputDirectory .

# The DLL will be in:
# packages\Microsoft.AnalysisServices.AdomdClient.{version}\lib\net45\Microsoft.AnalysisServices.AdomdClient.dll
```

Then you can manually copy the DLL to a location the code can find, or set an environment variable.

**Pros:**
- No full installer needed
- Good for development

**Cons:**
- Requires NuGet CLI
- Manual setup needed

---

## Option 4: Manual Download from NuGet.org

1. Go to: https://www.nuget.org/packages/Microsoft.AnalysisServices.AdomdClient
2. Click "Download package"
3. Rename `.nupkg` to `.zip` and extract
4. Find DLL in `lib\net45\` folder
5. Copy to a known location (e.g., `C:\Program Files\Microsoft SQL Server\160\SDK\Assemblies\`)

---

## After Installation

1. Run the diagnostic script to verify:
   ```bash
   python find_adomd.py
   ```

2. If found, restart your Python environment and try again:
   ```bash
   python test_list_tables_with_dataset_id.py
   ```

---

## Quick Test

After installing, verify the DLL exists:
```powershell
Test-Path "C:\Program Files\Microsoft SQL Server\160\SDK\Assemblies\Microsoft.AnalysisServices.AdomdClient.dll"
```

If it returns `True`, you're good to go! 🎉

