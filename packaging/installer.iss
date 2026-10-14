#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef AppPublisher
  #define AppPublisher "EmailChronicle"
#endif
#ifndef SourceCompanion
  #error SourceCompanion must point to the verified source companion ZIP
#endif

[Setup]
AppId={{AA579A1A-4BBD-41A2-B704-5B8F5DEBE19B}
#ifdef SignRelease
AppName=EmailChronicle
#else
AppName=EmailChronicle (Unsigned Preview)
#endif
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/MaximDascalasu/emailchronicle
DefaultDirName={localappdata}\Programs\EmailChronicle
DefaultGroupName=EmailChronicle
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
DisableProgramGroupPage=yes
DisableDirPage=yes
DisableReadyPage=yes
OutputDir=..\installer-output
OutputBaseFilename=EmailChronicle-Setup-{#AppVersion}-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\EmailChronicle.exe
CloseApplications=yes
SetupLogging=yes
InfoBeforeFile=PREVIEW-NOTICE.txt
#ifdef SignRelease
SignTool=chronicle
SignedUninstaller=yes
#endif

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\EmailChronicle\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceCompanion}"; DestDir: "{app}\_internal\third-party-notices"; DestName: "ThirdPartySources.zip"; Flags: ignoreversion
Source: "QUICK-START.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\EmailChronicle"; Filename: "{app}\EmailChronicle.exe"
Name: "{autoprograms}\EmailChronicle third-party notices"; Filename: "{app}\_internal\THIRD_PARTY_NOTICES.md"
Name: "{autodesktop}\EmailChronicle"; Filename: "{app}\EmailChronicle.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EmailChronicle.exe"; Description: "Launch EmailChronicle"; Flags: nowait postinstall skipifsilent

; Evidence in LOCALAPPDATA\EmailChronicle is deliberately never removed on uninstall.
