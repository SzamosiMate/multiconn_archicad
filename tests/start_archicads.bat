pushd %~dp0

set ARCHICAD_PATH="C:\Program Files\GRAPHISOFT\Archicad 27\Archicad.exe"

start "" %ARCHICAD_PATH% "%~dp0TestProject01.pla" -demo
start "" %ARCHICAD_PATH% "%~dp0TestProject02.pla" -demo
start "" %ARCHICAD_PATH% "%~dp0TestProject03.pla" -demo
start "" %ARCHICAD_PATH% "%~dp0TestProject04.pla" -demo
start "" %ARCHICAD_PATH% "%~dp0TestProject05.pla" -demo

popd
