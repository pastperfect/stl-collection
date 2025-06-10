# PowerShell Script to rename existing uploaded files to match the new camelCase format
# and update the SQLite database accordingly.
#
# New format: {publisher}_{range}_{name}_initial.{ext}
# All components are converted to camelCase.

param(
    [string]$DatabasePath = ".\database\db.sqlite3",
    [string]$MediaPath = ".\media\uploaded_images",
    [switch]$DryRun = $false,
    [switch]$Force = $false
)

# Import SQLite module
try {
    Import-Module PSSQLite -ErrorAction Stop
}
catch {
    Write-Error "PSSQLite module is required. Install it with: Install-Module PSSQLite"
    exit 1
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARNING" { "Yellow" }
        "SUCCESS" { "Green" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

function ConvertTo-CamelCase {
    param([string]$Text)
    
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return "unknown"
    }
    
    # Remove special characters and split by spaces/underscores/hyphens
    $words = $Text.Trim() -split '[^a-zA-Z0-9]+'
    
    # Filter out empty strings
    $words = $words | Where-Object { $_ -ne "" }
    
    if ($words.Count -eq 0) {
        return "unknown"
    }
    
    # First word lowercase, rest title case
    $camelCase = $words[0].ToLower()
    for ($i = 1; $i -lt $words.Count; $i++) {
        $camelCase += $words[$i].Substring(0,1).ToUpper() + $words[$i].Substring(1).ToLower()
    }
    
    return $camelCase
}

function New-CamelCaseFilename {
    param(
        [string]$Publisher,
        [string]$Range,
        [string]$Name,
        [string]$Extension
    )
    
    $publisherCamel = ConvertTo-CamelCase -Text $Publisher
    $rangeCamel = ConvertTo-CamelCase -Text $Range
    $nameCamel = ConvertTo-CamelCase -Text $Name
    
    return "${publisherCamel}_${rangeCamel}_${nameCamel}_initial${Extension}"
}

function Test-NewFormat {
    param([string]$Filename)
    
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($Filename)
    return $baseName.EndsWith("_initial")
}

function Get-DatabaseImages {
    param([string]$DbPath)
    
    try {
        $query = @"
SELECT id, image, name, publisher, range, upload_date 
FROM image_upload_image 
ORDER BY upload_date
"@
        
        $connection = New-SQLiteConnection -DataSource $DbPath
        $images = Invoke-SQLiteQuery -SQLiteConnection $connection -Query $query
        $connection.Close()
        
        return $images
    }
    catch {
        Write-Log "Failed to query database: $($_.Exception.Message)" "ERROR"
        return @()
    }
}

function Update-DatabaseImagePath {
    param(
        [string]$DbPath,
        [int]$ImageId,
        [string]$NewImagePath
    )
    
    try {
        $query = "UPDATE image_upload_image SET image = @newPath WHERE id = @id"
        $parameters = @{
            newPath = $NewImagePath
            id = $ImageId
        }
        
        $connection = New-SQLiteConnection -DataSource $DbPath
        Invoke-SQLiteQuery -SQLiteConnection $connection -Query $query -SqlParameters $parameters
        $connection.Close()
        
        return $true
    }
    catch {
        Write-Log "Failed to update database for image ID $ImageId`: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Rename-ImageFile {
    param(
        [object]$ImageRecord,
        [string]$MediaPath,
        [string]$DatabasePath,
        [bool]$DryRun = $true
    )
    
    if ([string]::IsNullOrWhiteSpace($ImageRecord.image)) {
        Write-Log "Skipping '$($ImageRecord.name)' - No file path in database" "WARNING"
        return $false
    }
    
    # Get current file info
    $currentFileName = Split-Path $ImageRecord.image -Leaf
    $currentFilePath = Join-Path $MediaPath $currentFileName
    
    # Skip if already in new format
    if (Test-NewFormat -Filename $currentFileName) {
        Write-Log "Skipping '$currentFileName' - Already in new format"
        return $false
    }
    
    # Check if file exists
    if (-not (Test-Path $currentFilePath)) {
        Write-Log "Skipping '$currentFileName' - File not found at: $currentFilePath" "WARNING"
        return $false
    }
    
    # Generate new filename
    $extension = [System.IO.Path]::GetExtension($currentFileName)
    $newFileName = New-CamelCaseFilename -Publisher $ImageRecord.publisher -Range $ImageRecord.range -Name $ImageRecord.name -Extension $extension
    $newFilePath = Join-Path $MediaPath $newFileName
    $newDatabasePath = "uploaded_images/$newFileName"
    
    Write-Log "Rename: $currentFileName -> $newFileName"
    
    if (-not $DryRun) {
        try {
            # Check if target file already exists
            if (Test-Path $newFilePath) {
                Write-Log "  ERROR: Target file already exists: $newFileName" "ERROR"
                return $false
            }
            
            # Rename the physical file
            Move-Item -Path $currentFilePath -Destination $newFilePath -ErrorAction Stop
            
            # Update database
            $updateSuccess = Update-DatabaseImagePath -DbPath $DatabasePath -ImageId $ImageRecord.id -NewImagePath $newDatabasePath
            
            if ($updateSuccess) {
                Write-Log "  SUCCESS: Renamed file and updated database" "SUCCESS"
                return $true
            }
            else {
                # Restore original file if database update failed
                Write-Log "  ERROR: Database update failed, restoring original file" "ERROR"
                try {
                    Move-Item -Path $newFilePath -Destination $currentFilePath -ErrorAction Stop
                    Write-Log "  Restored original file" "SUCCESS"
                }
                catch {
                    Write-Log "  CRITICAL: Could not restore original file! Manual intervention required." "ERROR"
                }
                return $false
            }
        }
        catch {
            Write-Log "  ERROR: File rename failed: $($_.Exception.Message)" "ERROR"
            return $false
        }
    }
    
    return $true  # Dry run success
}

function Main {
    Write-Log "STL Collection File Rename Script (PowerShell)"
    Write-Log "=" * 60
    
    # Validate paths
    if (-not (Test-Path $DatabasePath)) {
        Write-Log "Database not found: $DatabasePath" "ERROR"
        exit 1
    }
    
    if (-not (Test-Path $MediaPath)) {
        Write-Log "Media directory not found: $MediaPath" "ERROR"
        exit 1
    }
    
    Write-Log "Database: $DatabasePath"
    Write-Log "Media Path: $MediaPath"
    Write-Log ""
    
    # Get images from database
    $images = Get-DatabaseImages -DbPath $DatabasePath
    
    if ($images.Count -eq 0) {
        Write-Log "No images found in database" "WARNING"
        exit 0
    }
    
    Write-Log "Found $($images.Count) images in database"
    Write-Log ""
    
    # Dry run first
    Write-Log "DRY RUN - No changes will be made"
    Write-Log "-" * 40
    
    $filesToRename = @()
    foreach ($image in $images) {
        $success = Rename-ImageFile -ImageRecord $image -MediaPath $MediaPath -DatabasePath $DatabasePath -DryRun $true
        if ($success -and $image.image -and -not (Test-NewFormat -Filename (Split-Path $image.image -Leaf))) {
            $filesToRename += $image
        }
    }
    
    Write-Log ""
    Write-Log "Summary: $($filesToRename.Count) files need to be renamed"
    
    if ($filesToRename.Count -eq 0) {
        Write-Log "All files are already in the correct format!" "SUCCESS"
        exit 0
    }
    
    # Ask for confirmation unless Force is specified
    if (-not $Force -and -not $DryRun) {
        Write-Log ""
        $response = Read-Host "Do you want to proceed with the actual renaming? (y/N)"
        
        if ($response.ToLower() -ne 'y') {
            Write-Log "Operation cancelled."
            exit 0
        }
    }
    
    if ($DryRun) {
        Write-Log ""
        Write-Log "Dry run completed. Use -DryRun:`$false to perform actual renaming." "SUCCESS"
        exit 0
    }
    
    # Perform actual renaming
    Write-Log ""
    Write-Log "ACTUAL RENAMING - Making changes"
    Write-Log "-" * 40
    
    $successCount = 0
    $errorCount = 0
    
    foreach ($image in $filesToRename) {
        if (Rename-ImageFile -ImageRecord $image -MediaPath $MediaPath -DatabasePath $DatabasePath -DryRun $false) {
            $successCount++
        }
        else {
            $errorCount++
        }
    }
    
    Write-Log ""
    Write-Log "FINAL SUMMARY"
    Write-Log "=" * 20
    Write-Log "Successfully renamed: $successCount files" "SUCCESS"
    Write-Log "Errors encountered: $errorCount files" $(if ($errorCount -gt 0) { "ERROR" } else { "SUCCESS" })
    
    if ($errorCount -gt 0) {
        Write-Log ""
        Write-Log "Please review the errors above and fix any issues manually." "WARNING"
    }
    else {
        Write-Log ""
        Write-Log "All files have been successfully renamed to the new format!" "SUCCESS"
    }
}

# Run the main function
Main
