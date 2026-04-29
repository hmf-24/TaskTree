# 测试头像上传接口
# 需要先登录获取token

# 1. 登录获取token
$loginBody = @{
    email = "admin@example.com"
    password = "admin123"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/tasktree/auth/login" -Method POST -Body $loginBody -ContentType "application/json"

if ($loginResponse.code -eq 200) {
    $token = $loginResponse.data.access_token
    Write-Host "登录成功，Token: $($token.Substring(0, 20))..." -ForegroundColor Green
    
    # 2. 创建一个测试图片文件（1x1像素的PNG）
    $testImagePath = "test_avatar.png"
    # Base64编码的1x1透明PNG图片
    $base64Image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    $imageBytes = [Convert]::FromBase64String($base64Image)
    [IO.File]::WriteAllBytes($testImagePath, $imageBytes)
    Write-Host "测试图片已创建: $testImagePath" -ForegroundColor Green
    
    # 3. 上传文件
    $boundary = [System.Guid]::NewGuid().ToString()
    $headers = @{
        "Authorization" = "Bearer $token"
    }
    
    $fileContent = [IO.File]::ReadAllBytes($testImagePath)
    $fileName = [IO.Path]::GetFileName($testImagePath)
    
    $bodyLines = @(
        "--$boundary",
        "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
        "Content-Type: image/png",
        "",
        [System.Text.Encoding]::GetEncoding("iso-8859-1").GetString($fileContent),
        "--$boundary--"
    )
    
    $body = $bodyLines -join "`r`n"
    
    try {
        $uploadResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/tasktree/attachments/upload" -Method POST -Headers $headers -Body $body -ContentType "multipart/form-data; boundary=$boundary"
        
        if ($uploadResponse.code -eq 200) {
            Write-Host "上传成功！" -ForegroundColor Green
            Write-Host "文件URL: $($uploadResponse.data.url)" -ForegroundColor Cyan
            Write-Host "文件大小: $($uploadResponse.data.size) bytes" -ForegroundColor Cyan
        } else {
            Write-Host "上传失败: $($uploadResponse.message)" -ForegroundColor Red
        }
    } catch {
        Write-Host "上传出错: $_" -ForegroundColor Red
    }
    
    # 清理测试文件
    Remove-Item $testImagePath -ErrorAction SilentlyContinue
    
} else {
    Write-Host "登录失败: $($loginResponse.message)" -ForegroundColor Red
}
