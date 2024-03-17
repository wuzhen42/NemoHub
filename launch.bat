pyside6-uic .\resource\ui\LoginWindow.ui -o ui_loginwindow.py
pyside6-rcc .\resource\resource.qrc -o resource_rc.py

SET PYTHONPATH=%~dp0;%~dp0/app;%PYTHONPATH%

python client.py