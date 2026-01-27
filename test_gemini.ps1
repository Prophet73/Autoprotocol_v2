$apiKey = "AIzaSyAbW11chSyV0rL0yaPeAcL09oLr0uMg98Y"

# JSON в файл чтобы PowerShell не портил кавычки
$json = '{"contents":[{"parts":[{"text":"Say hello world"}]}]}'
$json | Out-File -Encoding utf8 -FilePath "request.json"

curl.exe "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key=$apiKey" `
  -H "Content-Type: application/json" `
  -X POST `
  -d "@request.json"
