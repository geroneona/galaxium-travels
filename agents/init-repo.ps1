$ErrorActionPreference = 'Stop'
$GIT_BASH = "${env:ProgramFiles}\Git\bin\bash.exe"
if (-not (Test-Path $GIT_BASH)) { $GIT_BASH = "${env:ProgramFiles(x86)}\Git\bin\bash.exe" }
if (-not (Test-Path $GIT_BASH)) { throw "Git Bash not found" }

$TARGET_DIR_WIN  = $PWD.Path
$TARGET_DIR_BASH = "/" + $TARGET_DIR_WIN.Substring(0,1).ToLower() + $TARGET_DIR_WIN.Substring(2).Replace('\','/')
$TEMP_REPO = Join-Path $env:TEMP '.temp-repo'
$GIT_ORIGIN = 'git@github.ibm.com:Consulting-DTT-AI-Integration-Services/agentstudio-external-agent-boilerplate.git'

try {
    if (Test-Path $TEMP_REPO) { Remove-Item $TEMP_REPO -Recurse -Force }
    git -c core.autocrlf=false clone --filter=blob:none --no-checkout $GIT_ORIGIN $TEMP_REPO
    Set-Location $TEMP_REPO
    git sparse-checkout init --cone
    git sparse-checkout set scripts
    git checkout

    & $GIT_BASH -lc "find scripts -type f -name '*.sh' -print0 | xargs -0 sed -i 's/\r$//'"
    & $GIT_BASH -x scripts/bin/init-repo.sh "$TARGET_DIR_BASH"
}
finally {
    Set-Location $env:TEMP
    if (Test-Path $TEMP_REPO) { Remove-Item $TEMP_REPO -Recurse -Force -ErrorAction SilentlyContinue }
    Set-Location $TARGET_DIR_WIN
}