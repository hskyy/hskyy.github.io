; Inno Setup script — builds the installer wizard for HEIC to JPEG.
; Compile with:  ISCC.exe packaging\HeicToJpeg.iss   (after PyInstaller has produced dist\HeicToJpeg.exe)

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "HEIC to JPEG"
#define AppPublisher "Brian Hundley"
#define AppExeName "HeicToJpeg.exe"
#define AppURL "https://github.com/hskyy/hskyy.github.io/tree/master/projects/heic-to-jpeg"

[Setup]
AppId={{7A6B1E0C-4D2F-4B8B-9C21-3F5E8D2A6B14}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Per-user install by default so no admin prompt is needed; user may still choose all users.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=HeicToJpeg-Setup-{#AppVersion}
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "sendto"; Description: "Add ""{#AppName}"" to the right-click Send to menu"; GroupDescription: "Explorer integration:"

[Files]
; The PyInstaller one-file build already bundles Python, Pillow, pillow-heif and libheif.
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; DestName: "README.txt"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{usersendto}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: sendto

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
