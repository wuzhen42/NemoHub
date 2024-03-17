cd "%2"
del /q *.*
for /d %%i in (*) do rmdir /s /q "%%i" 

xcopy /e /q %1 %2

.\NemoHub
exit 0