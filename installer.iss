; Script de Inno Setup para KILLCleaner v1.0
[Setup]
AppId={{D9A83F12-72E4-4D61-A79B-98F1C37B49B1}
AppName=KILLCleaner
AppVersion=1.0
AppPublisher=KILLSecurity Suite
DefaultDirName={autopf}\KILLCleaner
DefaultGroupName=KILLCleaner
OutputDir=dist_installer
OutputBaseFilename=KILLCleaner_Setup
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Binario compilado
Source: "dist\KILLCleaner.exe"; DestDir: "{app}"; Flags: ignoreversion
; Recursos y soporte
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\KILLCleaner"; Filename: "{app}\KILLCleaner.exe"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Desinstalar KILLCleaner"; Filename: "{uninstallexe}"
Name: "{autodesktop}\KILLCleaner"; Filename: "{app}\KILLCleaner.exe"; Tasks: desktopicon; IconFilename: "{app}\assets\icon.ico"

[Run]
Filename: "{app}\KILLCleaner.exe"; Description: "{cm:LaunchProgram,KILLCleaner}"; Flags: nowait postinstall skipifsilent