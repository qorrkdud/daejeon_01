@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ==================================================
echo   좋은 아침이에요! 오늘의 카드뉴스 후보를 모을게요
echo ==================================================
echo.

where py > nul 2> nul
if errorlevel 1 goto nopython

py "%~dp0scripts\morning.py"
if errorlevel 1 goto failed
goto done

:nopython
echo [오류] 파이썬 실행기 py 를 찾지 못했어요.
echo        파이썬이 설치되어 있는지 확인해 주세요.
echo        설치할 때 Add python.exe to PATH 칸에 체크해야 해요.
goto done

:failed
echo.
echo [오류] 작업 중에 문제가 생겼어요. 바로 위에 나온 안내 문장을 확인해 주세요.
echo        이해가 어려우면 이 화면을 Claude에게 보여 주세요.

:done
echo.
echo 아무 키나 누르면 창이 닫혀요.
pause > nul
