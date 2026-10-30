param(
    [ValidateSet('setup', 'patch', 'rebuild', 'clean')]
    [string] $Command = 'rebuild',

    [ValidateSet('17', '21', '25')]
    [string] $JdkVersion = '17'
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$searchRoot = $repositoryRoot
$toolsRoot = $null
while ($searchRoot) {
    $candidateToolsRoot = Join-Path $searchRoot '.tools'
    if (Test-Path -LiteralPath (Join-Path $candidateToolsRoot "jdk-$JdkVersion\bin\javac.exe")) {
        $toolsRoot = $candidateToolsRoot
        break
    }

    $parent = Split-Path -Parent $searchRoot
    if ($parent -eq $searchRoot) {
        break
    }
    $searchRoot = $parent
}

if (-not $toolsRoot) {
    throw "Could not find a workspace-local .tools\jdk-$JdkVersion installation above $repositoryRoot."
}

$jdkRoot = Join-Path $toolsRoot "jdk-$JdkVersion"
$javac = Join-Path $jdkRoot 'bin\javac.exe'
$bash = Join-Path $env:ProgramFiles 'Git\bin\bash.exe'

if (-not (Test-Path -LiteralPath $javac)) {
    throw "JDK $JdkVersion is not installed at $jdkRoot."
}
if (-not (Test-Path -LiteralPath $bash)) {
    throw "Git Bash was not found at $bash."
}

$needsShortTempPath = $Command -eq 'setup'
$drive = $null
$shortTempExports = ''
if ($needsShortTempPath) {
    $availableDrive = @('Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z') |
        Where-Object { -not (Get-PSDrive -Name $_ -ErrorAction SilentlyContinue) } |
        Select-Object -First 1
    if (-not $availableDrive) {
        throw 'No free drive letter is available for the short Java temporary path.'
    }

    $drive = $availableDrive + ':'
    $tempPath = Join-Path $toolsRoot 'gradle-tmp'
    New-Item -ItemType Directory -Force -Path $tempPath | Out-Null
    & subst.exe $drive $toolsRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Could not map $drive to $toolsRoot."
    }

    $shortTempExports = "export TEMP='$drive\gradle-tmp'`nexport TMP='$drive\gradle-tmp'"
}

function ConvertTo-BashPath([string] $Path) {
    $fullPath = [IO.Path]::GetFullPath($Path)
    if ($fullPath -notmatch '^([A-Za-z]):\\(.*)$') {
        throw "Expected a drive-qualified Windows path: $fullPath"
    }
    return '/' + $Matches[1].ToLowerInvariant() + '/' + ($Matches[2] -replace '\\', '/')
}

$jdkBashPath = ConvertTo-BashPath $jdkRoot
$repositoryBashPath = ConvertTo-BashPath $repositoryRoot
$bashScript = @"
export JAVA_HOME='$jdkBashPath'
export PATH="`$JAVA_HOME/bin:`$PATH"
$shortTempExports
cd '$repositoryBashPath' && ./beefmc '$Command'
"@

try {
    & $bash -lc $bashScript
    $buildExitCode = $LASTEXITCODE
}
finally {
    if ($needsShortTempPath) {
        & subst.exe $drive /D
    }
}

if ($buildExitCode -ne 0) {
    exit $buildExitCode
}
