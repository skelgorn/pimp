; Script para Inno Setup gerado pela Cascade

#define MyAppName "LetrasPIP"
#define MyAppVersion "0.1-beta"
#define MyAppPublisher "Skelgorn"
#define MyAppURL "https://github.com/skelgorn/pimp"
#define MyAppExeName "LetrasPIP.exe"

[Setup]
AppId={{F4C6E5A3-7B8D-4E9C-8A1B-2C3D4E5F6A7B}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
CloseApplications=force
DisableProgramGroupPage=yes
OutputDir=.\installer
OutputBaseFilename=LetrasPIP_setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icon.ico

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\LetrasPIP.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // Force kill the app before the installer even shows up, to prevent the "app is running" message.
  Exec('taskkill.exe', '/f /im "{#MyAppExeName}"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;
