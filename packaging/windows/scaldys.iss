; Scaldys project installer script for Inno Setup.
; This file is used by deployment modes that produce a Windows installer.
; The active mode is set via deployment_mode in builder.toml and controls
; which preprocessor defines scaldys-builder passes to ISCC at build time.
;
;   Mode 1 -- pyinstaller (default, no extra define passed):
;     The installer deploys the PyInstaller-frozen executable tree bundled in
;     dist/portable/.  No Python runtime is installed alongside it.
;     Launcher scripts detect <app>.exe in bin/ and call it directly.
;     Set in builder.toml:  deployment_mode = "pyinstaller"
;
;   Mode 2 -- pyruntime (/DPyruntimeMode=1):
;     PyInstaller is not used.  The installer deploys a managed Python virtual
;     environment (PythonRuntime) into the installation directory.  The launcher
;     scripts activate that environment rather than calling a frozen executable.
;     Use this mode when the application must coexist with tools such as Quarto
;     that require a real Python interpreter.
;     Set in builder.toml:  deployment_mode = "pyruntime"
;     Within Mode 2, two sub-modes are available:
;       Online  (default): uv downloads Python and installs the wheel at install time.
;       Offline (/DPythonRuntimeDir=<path>): a pre-built venv is bundled in setup.exe.
;         Set in builder.toml:  bundle_pyruntime = true
;
;   Mode 3 -- wheel_only:
;     This file is NOT used.  scaldys-builder skips Inno Setup entirely and
;     only produces a binary wheel in dist/wheels/.  No installer is built.
;     Set in builder.toml:  deployment_mode = "wheel_only"

#define MyAppName "scaldys"
#define MyAppVersion ""
#define MyAppPublisher "Scaldys"
#define MyAppURL "http://www.scaldys.net/"
#define MyAppExeName "scaldys.exe"
#define MyAppBatName "scaldys_commandline.bat"
#define MyAppPs1Name "scaldys_powershell.ps1"
#define MyAppHelpName "manual"

#ifndef SourceDir
  #define SourceDir "..\..\dist\portable"
#endif

; Determine PythonRuntime install mode (only relevant when PyruntimeMode is set).
#ifdef PyruntimeMode
  #ifdef PythonRuntimeDir
    #define PythonRuntimeDesc "Python runtime environment (included -- no internet required)"
  #else
    #define PythonRuntimeDesc "Python runtime environment (downloaded at install time)"
  #endif
#endif

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{51A09FD6-57C7-4CFD-9B7A-3E5FBBB92AFE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\Scaldys
DefaultGroupName=Scaldys
UsePreviousGroup=no
OutputDir=..\..\dist\installer
OutputBaseFilename=setup
Compression=lzma
SolidCompression=yes
; "ArchitecturesAllowed=x64" specifies that Setup cannot run on
; anything but x64.
ArchitecturesAllowed=x64
; "ArchitecturesInstallIn64BitMode=x64" requests that the install be
; done in "64-bit mode" on x64, meaning it should use the native
; 64-bit Program Files directory and the 64-bit view of the registry.
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
; The pyruntime task controls PythonRuntime installation (Mode 2 only).
; It runs during the installation phase (while still elevated), so it can write
; to C:\Program Files\<App>\PythonRuntime without a separate UAC prompt.
#ifdef PyruntimeMode
Name: "pyruntime"; Description: "{#PythonRuntimeDesc}"; GroupDescription: "Optional components:"
#endif

[Files]
; NOTE: Don't use "Flags: ignoreversion" on any shared system files
; The SourceDir tree contains bin/ (Mode 1: PyInstaller exe; Mode 2: scripts only),
; documentation/, examples/, logs/, and in Mode 2 also wheels/.
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: createallsubdirs recursesubdirs ignoreversion

; Offline mode (Mode 2 only): include the pre-built PythonRuntime environment.
; This section is only compiled when the builder passes /DPythonRuntimeDir=<path>.
#ifdef PyruntimeMode
  #ifdef PythonRuntimeDir
Source: "{#PythonRuntimeDir}\*"; DestDir: "{app}\PythonRuntime"; Flags: createallsubdirs recursesubdirs ignoreversion; Tasks: pyruntime
  #endif
#endif

[Icons]
; CMD launcher (bat file -- works for both modes; content differs per mode)
Name: "{group}\{#MyAppName} CMD"; Filename: "{app}\bin\{#MyAppBatName}"
; PS launcher (ps1 file -- works for both modes; content differs per mode)
Name: "{group}\{#MyAppName} PS"; Filename: "{code:GetLauncher}"; Parameters: "{code:GetLauncherParameters}"
Name: "{group}\{#MyAppName} Help"; Filename: "{app}\documentation\{#MyAppHelpName}\index.html"; Check: FileExists(ExpandConstant('{app}\documentation\{#MyAppHelpName}\index.html'))
Name: "{commondesktop}\{#MyAppName}"; Filename: "{code:GetLauncher}"; Parameters: "{code:GetLauncherParameters}"; Tasks: desktopicon

; Online mode (Mode 2 only): run the PythonRuntime setup script during installation
; while the installer is still elevated, so it can create PythonRuntime without a
; separate UAC prompt.  Only compiled when PyruntimeMode is set and PythonRuntimeDir
; is NOT defined (i.e. online mode).
#ifdef PyruntimeMode
  #ifndef PythonRuntimeDir
[Run]
Filename: "powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\bin\setup_pyruntime.ps1"" ""{app}"""; \
    StatusMsg: "Installing Python runtime environment..."; \
    Tasks: pyruntime
  #endif
#endif

[UninstallRun]
; Mode 2: remove PythonRuntime and the bundled wheels on uninstall.
; Both directories may not exist (user deselected the task, or setup failed),
; so each command is guarded with Test-Path.
#ifdef PyruntimeMode
Filename: "powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""if (Test-Path '{app}\PythonRuntime') {{ Remove-Item -Recurse -Force '{app}\PythonRuntime' -ErrorAction SilentlyContinue }}"""; \
    Flags: runhidden; \
    RunOnceId: "RemovePythonRuntime"
Filename: "powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""if (Test-Path '{app}\wheels') {{ Remove-Item -Recurse -Force '{app}\wheels' -ErrorAction SilentlyContinue }}"""; \
    Flags: runhidden; \
    RunOnceId: "RemoveWheels"
#endif

[Code]
function GetLauncher(Param: string): string;
begin
  if FileExists(ExpandConstant('{localappdata}\Microsoft\WindowsApps\wt.exe')) then
    Result := ExpandConstant('{localappdata}\Microsoft\WindowsApps\wt.exe')
  else
    Result := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
end;

function GetLauncherParameters(Param: string): string;
var
  Ps1Path: string;
begin
  Ps1Path := ExpandConstant('{app}\bin\{#MyAppPs1Name}');

  if FileExists(ExpandConstant('{localappdata}\Microsoft\WindowsApps\wt.exe')) then
    Result := 'powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File "' + Ps1Path + '"'
  else
    Result := '-NoProfile -ExecutionPolicy Bypass -NoExit -File "' + Ps1Path + '"';
end;
