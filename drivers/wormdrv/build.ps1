# drivers/wormdrv/build.ps1 — WormDrv build chain (WDK + MSBuild).
# المطلوب مثبت: Visual Studio + Windows Driver Kit (WDK) 10/11.
# الاستخدام: ./build.ps1  (من مجلد WormGPT_Ultra_Singularity\drivers\wormdrv)
# الناتج: wormdrv.sys + wormdrv.inf (في مجلد .\bin)

$wdkRoot  = "C:\Program Files (x86)\Windows Kits\10"
$msbuild  = "msbuild.exe"
$proj     = "wormdrv.vcxproj"

# حدّث حسب نسختك: VS/WDK install path
$candidates = @(
    "${env:ProgramFiles}\Microsoft Visual Studio\Community\MSBuild\Current\Bin\MSBuild.exe",
    "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Community\MSBuild\Current\Bin\MSBuild.exe",
    "${env:ProgramFiles}\Microsoft Visual Studio\Professional\MSBuild\Current\Bin\MSBuild.exe",
    "${env:ProgramFiles}\Microsoft Visual Studio\Enterprise\MSBuild\Current\Bin\MSBuild.exe"
)
$msbuildPath = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $msbuildPath) {
    Write-Error "MSBuild غير موجود — ثبّت Visual Studio أولا."
    exit 1
}
if (-not (Test-Path $wdkRoot)) {
    Write-Error "WDK غير موجود في $wdkRoot — ثبّت WDK أولا."
    exit 1
}

Write-Host ">> msbuild $proj (x64 WDM driver)"
& $msbuildPath $proj /p:Configuration=Release /p:Platform=x64 /p:DriverType=WDM /m
if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed."
    exit $LASTEXITCODE
}

# انسخ الناتج إلى مجلد bin
New-Item -ItemType Directory -Force -Path ".\bin" | Out-Null
Copy-Item ".\Release\wormdrv\wormdrv.sys" ".\bin" -Force -ErrorAction SilentlyContinue
Copy-Item ".\Release\wormdrv\wormdrv.inf" ".\bin" -Force -ErrorAction SilentlyContinue

Write-Host ">> Build OK -> bin\wormdrv.sys"
Write-Host ">> توقيع الاختبار (SHELL AS ADMIN): bcdedit /set testsigning on"
Write-Host ">> تثبيت الخدمة: sc create WormDrv type= kernel binPath=<abs path to.sys>"
Write-Host ">> تشغيل:        sc start WormDrv"
Write-Host ">> إيقاف:        sc stop WormDrv   |   إزالة: sc delete WormDrv"
