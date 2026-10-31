; Build with ISCC /DSourceFolder=<absolute bundle path> /DOutputDir=<dist path>.
; This is an independent, unofficial distribution. It does not upgrade Thonny.
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef SourceFolder
  #error SourceFolder must point to the prepared application bundle
#endif
#ifndef OutputDir
  #define OutputDir "..\..\dist"
#endif

[Setup]
AppId=RicardoKers.ThonnyRFC2217
AppName=Thonny RFC2217
AppVersion={#AppVersion}
AppVerName=Thonny RFC2217 {#AppVersion}
AppPublisher=RicardoKers (unofficial distribution)
AppPublisherURL=https://github.com/RicardoKers/Thonny-RFC2217
AppSupportURL=https://github.com/RicardoKers/Thonny-RFC2217/issues
AppUpdatesURL=https://github.com/RicardoKers/Thonny-RFC2217/releases
AppComments=Unofficial Thonny distribution with native RFC 2217 support for MicroPython.
AppCopyright=Original Thonny and dependency copyrights are preserved in the included licenses.
DefaultDirName={localappdata}\Programs\ThonnyRFC2217
DefaultGroupName=Thonny RFC2217
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=Thonny-RFC2217-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
DisableReadyPage=no
AlwaysShowDirOnReadyPage=yes
UninstallDisplayName=Thonny RFC2217 {#AppVersion}
UninstallDisplayIcon={app}\ThonnyRFC2217.exe
CloseApplications=no
RestartApplications=no
ChangesAssociations=no
SetupLogging=yes
#if FileExists(SourceFolder + "\LICENSE")
LicenseFile={#SourceFolder}\LICENSE
#elif FileExists(SourceFolder + "\LICENSE.txt")
LicenseFile={#SourceFolder}\LICENSE.txt
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; User settings and portable-mode markers belong to the portable ZIP only.
Source: "{#SourceFolder}\*"; DestDir: "{app}"; Excludes: "user_data\*,.portable,portable.ini,portable_thonny.ini,runtime\portable_thonny.ini"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Thonny RFC2217"; Filename: "{app}\ThonnyRFC2217.exe"; WorkingDir: "{app}"; AppUserModelID: "RicardoKers.ThonnyRFC2217"
Name: "{autodesktop}\Thonny RFC2217"; Filename: "{app}\ThonnyRFC2217.exe"; WorkingDir: "{app}"; AppUserModelID: "RicardoKers.ThonnyRFC2217"; Tasks: desktopicon

[Run]
Filename: "{app}\ThonnyRFC2217.exe"; Description: "{cm:LaunchProgram,Thonny RFC2217}"; Flags: nowait postinstall skipifsilent unchecked

; No file associations, original-Thonny registry keys, bulk upgrade deletions,
; or wildcard UninstallDelete entries. Inno removes only installed files.
