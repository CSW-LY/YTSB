# Test LLM fallback functionality
$uri = "http://localhost:8000/api/v1/intent/recognize"
$headers = @{"Content-Type"="application/json"}
$body = '{"app_key": "ui_test", "text": "Hello world"}'

try {
    $response = Invoke-WebRequest -Uri $uri -Method POST -Headers $headers -Body $body
    Write-Host "Response Status Code: " $response.StatusCode
    Write-Host "Response Content: " $response.Content
} catch {
    Write-Host "Error: " $_.Exception.Message
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response Body: " $responseBody
    }
}
