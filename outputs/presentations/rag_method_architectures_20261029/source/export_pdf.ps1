param(
    [string]$ProjectRoot = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'
$artifactRoot = Join-Path $ProjectRoot 'outputs/presentations/rag_method_architectures_20261029'
$presentationPath = Join-Path $artifactRoot 'output/rag_methods_architecture_and_logic.pptx'
$pdfPath = Join-Path $artifactRoot 'output/rag_methods_architecture_and_logic.pdf'
if (-not (Test-Path -LiteralPath $presentationPath)) { throw 'Validated presentation is missing.' }

# Use the installed Office document API as a local format converter. The deck
# opens read-only without a document window; no macros or external links run.
# Do not quit an application that already has user documents open.
$powerPoint = $null
$document = $null
$existingCount = 0
try {
    $powerPoint = New-Object -ComObject PowerPoint.Application
    $existingCount = $powerPoint.Presentations.Count
    $previousSecurity = $powerPoint.AutomationSecurity
    $powerPoint.AutomationSecurity = 3
    $document = $powerPoint.Presentations.Open($presentationPath, -1, 0, 0)
    if ($document.Slides.Count -ne 12) { throw 'Slide count differs.' }
    # ppSaveAsPDF = 32. SaveAs avoids PowerShell COM binding ambiguity in the
    # optional-parameter-heavy ExportAsFixedFormat method.
    $document.SaveAs($pdfPath, 32)
    Write-Output "Exported a 12-page PDF from the validated native presentation."
}
finally {
    if ($null -ne $document) {
        $document.Close()
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($document)
    }
    if ($null -ne $powerPoint) {
        $powerPoint.AutomationSecurity = $previousSecurity
        if ($existingCount -eq 0 -and $powerPoint.Presentations.Count -eq 0) { $powerPoint.Quit() }
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint)
    }
}
