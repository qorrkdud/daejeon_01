@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

rem 기본 디자인 방식: HTML / A / B / coverB  (HTML = 레시피 카드 + 제품 사진)
set DEFAULT_MODE=HTML

echo ==================================================
echo   카드뉴스 만들기를 시작할게요
echo ==================================================

where py < nul > nul 2> nul
if errorlevel 1 goto nopython

py -c "import PIL" < nul > nul 2> nul
if errorlevel 1 goto nopillow

py "%~dp0scripts\make_flow.py"
goto done

:nopython
echo [오류] 준비 단계: 파이썬 실행기 py 를 찾지 못했어요.
echo        파이썬이 설치되어 있는지 확인해 주세요.
goto done

:nopillow
echo [오류] 준비 단계: 이미지 도구 Pillow 가 없어요.
echo        검은 창에서  py -m pip install pillow  를 실행해 주세요.
goto done

:done
echo.
echo 아무 키나 누르면 창이 닫혀요.
pause > nul
