@echo off
echo 正在打包Flask应用为exe...
echo.

pyinstaller --noconfirm --onefile --windowed ^
    --name="URLTrigger" ^
    --icon="icon.ico" ^
    --add-data="icon.png;." ^
    --add-data="config.json;." ^
    --add-data="logs.json;." ^
    --hidden-import=pystray ^
    --hidden-import=PIL ^
    --hidden-import=flask ^
    --hidden-import=requests ^
    --hidden-import=pyperclip ^
    app_with_tray.py

echo.
echo 打包完成！
echo exe文件在 dist\URLTrigger.exe
echo.
pause
