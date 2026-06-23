# 一键启动前后端（开发模式，默认仅监听 localhost）
$backendCmd = "cd backend; .\venv\Scripts\uvicorn main:app --host 127.0.0.1 --port 8001 --reload"
$frontendCmd = "npm run dev"

Write-Host "启动后端: http://localhost:8001" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Write-Host "启动前端: http://localhost:3000" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "按任意键退出..."
[void][System.Console]::ReadKey($true)
