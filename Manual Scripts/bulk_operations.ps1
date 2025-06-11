# STL Collection Bulk Operations Script
# This script provides functions to process image files from directory structures
# and perform bulk operations on the SQLite database

# Requires: PSSQLite module
# Install with: Install-Module -Name PSSQLite -Scope CurrentUser

param(
    [Parameter(Mandatory=$false)]
    [string]$DatabasePath = ".\db.sqlite3",
    
    [Parameter(Mandatory=$false)]
    [string]$SourceDirectory = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Action = "List"
)

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Level] $Message"
}

function Test-Dependencies {
    if (-not (Get-Module -ListAvailable -Name PSSQLite)) {
        Write-Log "PSSQLite module is not installed. Please install it with: Install-Module -Name PSSQLite -Scope CurrentUser" "ERROR"
        return $false
    }
    return $true
}

function Connect-Database {
    param([string]$DbPath)
    
    try {
        if (-not (Test-Path $DbPath)) {
            Write-Log "Database file not found: $DbPath" "ERROR"
            return $null
        }
        
        Import-Module PSSQLite
        $connection = New-SQLiteConnection -DataSource $DbPath
        Write-Log "Connected to database: $DbPath"
        return $connection
    }
    catch {
        Write-Log "Failed to connect to database: $($_.Exception.Message)" "ERROR"
        return $null
    }
}

function Get-ImageFiles {
    param([string]$Directory)
    
    if (-not (Test-Path $Directory)) {
        Write-Log "Source directory not found: $Directory" "ERROR"
        return @()
    }
    
    $supportedExtensions = @("*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.webp")
    $imageFiles = @()
    
    foreach ($ext in $supportedExtensions) {
        $files = Get-ChildItem -Path $Directory -Filter $ext -Recurse -File
        $imageFiles += $files
    }
    
    Write-Log "Found $($imageFiles.Count) image files in $Directory"
    return $imageFiles
}

function Extract-MetadataFromPath {
    param([System.IO.FileInfo]$File, [string]$BaseDirectory)
    
    $relativePath = $File.FullName.Replace($BaseDirectory, "").TrimStart("\")
    $pathParts = $relativePath.Split("\")
    
    # Try to extract publisher and range from path structure
    # Assumes structure like: Publisher\Range\Subfolder\File.ext
    $publisher = ""
    $range = ""
    
    if ($pathParts.Length -ge 2) {
        $publisher = $pathParts[0]
        $range = $pathParts[1]
    }
    elseif ($pathParts.Length -eq 1) {
        $publisher = Split-Path $BaseDirectory -Leaf
    }
    
    return @{
        Name = [System.IO.Path]::GetFileNameWithoutExtension($File.Name)
        Publisher = $publisher
        Range = $range
        FolderLocation = $File.DirectoryName
        FileName = $File.Name
        FullPath = $File.FullName
        RelativePath = $relativePath
    }
}

function Add-ImageToDatabase {
    param(
        [object]$Connection,
        [hashtable]$ImageData,
        [string]$MediaDirectory = ".\media\uploaded_images"
    )
    
    try {
        # Copy file to media directory if specified
        if ($MediaDirectory -and (Test-Path $MediaDirectory)) {
            $destFile = Join-Path $MediaDirectory $ImageData.FileName
            if (-not (Test-Path $destFile)) {
                Copy-Item $ImageData.FullPath $destFile
                Write-Log "Copied file: $($ImageData.FileName)"
            }
            $imagePath = "uploaded_images/$($ImageData.FileName)"
        }
        else {
            $imagePath = $ImageData.RelativePath
        }
        
        # Insert into database
        $query = @"
INSERT INTO image_upload_image (
    name, publisher, range, folder_location, upload_date, notes, image
) VALUES (
    @name, @publisher, @range, @folder_location, @upload_date, @notes, @image
)
"@
        
        $parameters = @{
            name = $ImageData.Name
            publisher = $ImageData.Publisher
            range = $ImageData.Range
            folder_location = $ImageData.FolderLocation
            upload_date = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            notes = "Bulk imported via PowerShell"
            image = $imagePath
        }
        
        Invoke-SQLiteQuery -SQLiteConnection $Connection -Query $query -SqlParameters $parameters
        Write-Log "Added to database: $($ImageData.Name)"
        return $true
    }
    catch {
        Write-Log "Failed to add image to database: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Get-DatabaseStats {
    param([object]$Connection)
    
    try {
        $imageCount = Invoke-SQLiteQuery -SQLiteConnection $Connection -Query "SELECT COUNT(*) as count FROM image_upload_image"
        $tagCount = Invoke-SQLiteQuery -SQLiteConnection $Connection -Query "SELECT COUNT(*) as count FROM tags_tag"
        
        Write-Host ""
        Write-Host "=== Database Statistics ===" -ForegroundColor Green
        Write-Host "Total Images: $($imageCount.count)"
        Write-Host "Total Tags: $($tagCount.count)"
        
        # Publisher stats
        $publisherStats = Invoke-SQLiteQuery -SQLiteConnection $Connection -Query @"
SELECT publisher, COUNT(*) as count 
FROM image_upload_image 
WHERE publisher IS NOT NULL AND publisher != '' 
GROUP BY publisher 
ORDER BY count DESC
"@
        
        if ($publisherStats) {
            Write-Host ""
            Write-Host "Publishers:" -ForegroundColor Cyan
            foreach ($pub in $publisherStats) {
                Write-Host "  - $($pub.publisher): $($pub.count) images"
            }
        }
        
        # Range stats
        $rangeStats = Invoke-SQLiteQuery -SQLiteConnection $Connection -Query @"
SELECT range, COUNT(*) as count 
FROM image_upload_image 
WHERE range IS NOT NULL AND range != '' 
GROUP BY range 
ORDER BY count DESC
"@
        
        if ($rangeStats) {
            Write-Host ""
            Write-Host "Ranges:" -ForegroundColor Cyan
            foreach ($rng in $rangeStats) {
                Write-Host "  - $($rng.range): $($rng.count) images"
            }
        }
    }
    catch {
        Write-Log "Failed to get database stats: $($_.Exception.Message)" "ERROR"
    }
}

function Start-BulkImport {
    param([string]$SourceDir, [object]$Connection)
    
    Write-Log "Starting bulk import from: $SourceDir"
    
    $imageFiles = Get-ImageFiles -Directory $SourceDir
    if ($imageFiles.Count -eq 0) {
        Write-Log "No image files found to import" "WARNING"
        return
    }
    
    $successCount = 0
    $errorCount = 0
    
    foreach ($file in $imageFiles) {
        $metadata = Extract-MetadataFromPath -File $file -BaseDirectory $SourceDir
        
        if (Add-ImageToDatabase -Connection $Connection -ImageData $metadata) {
            $successCount++
        }
        else {
            $errorCount++
        }
    }
    
    Write-Log "Bulk import completed. Success: $successCount, Errors: $errorCount"
}

# Main execution
Write-Log "STL Collection Bulk Operations Script"
Write-Log "Action: $Action"

if (-not (Test-Dependencies)) {
    exit 1
}

$connection = Connect-Database -DbPath $DatabasePath
if (-not $connection) {
    exit 1
}

try {
    switch ($Action.ToLower()) {
        "list" {
            Get-DatabaseStats -Connection $connection
        }
        "import" {
            if (-not $SourceDirectory) {
                Write-Log "SourceDirectory parameter is required for import action" "ERROR"
                exit 1
            }
            Start-BulkImport -SourceDir $SourceDirectory -Connection $connection
        }
        default {
            Write-Log "Unknown action: $Action" "ERROR"
            Write-Log "Available actions: List, Import"
        }
    }
}
finally {
    if ($connection) {
        $connection.Close()
        Write-Log "Database connection closed"
    }
}

# Usage Examples:
# .\bulk_operations.ps1 -Action List
# .\bulk_operations.ps1 -Action Import -SourceDirectory "C:\MySTLFiles"
