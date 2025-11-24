# VyRaTrader Authentication Test Script for PowerShell
# Run this from the vyra_trader directory

$baseUrl = "http://localhost:8000/api/v1"

Write-Host "`n=== Testing VyRaTrader Authentication ===`n" -ForegroundColor Cyan

# Test 1: Signup
Write-Host "Test 1: Signup" -ForegroundColor Yellow
$signupBody = @{
    email = "test@example.com"
    password = "SecurePass123!"
    full_name = "Test User"
    currency = "GHS"
} | ConvertTo-Json

try {
    $signupResponse = Invoke-RestMethod -Uri "$baseUrl/auth/signup" `
        -Method Post `
        -ContentType "application/json" `
        -Body $signupBody
    
    Write-Host "✅ Signup successful!" -ForegroundColor Green
    Write-Host "User ID: $($signupResponse.id)"
    Write-Host "Email: $($signupResponse.email)"
    Write-Host "Access Token: $($signupResponse.access_token.Substring(0, 20))..."
    Write-Host "Refresh Token: $($signupResponse.refresh_token.Substring(0, 20))..."
    
    $global:accessToken = $signupResponse.access_token
    $global:refreshToken = $signupResponse.refresh_token
    
} catch {
    Write-Host "❌ Signup failed" -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit
}

Start-Sleep -Seconds 1

# Test 2: Login
Write-Host "`nTest 2: Login" -ForegroundColor Yellow
$loginBody = @{
    email = "test@example.com"
    password = "SecurePass123!"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/auth/login" `
        -Method Post `
        -ContentType "application/json" `
        -Body $loginBody
    
    Write-Host "✅ Login successful!" -ForegroundColor Green
    Write-Host "User: $($loginResponse.user.full_name)"
    Write-Host "Email: $($loginResponse.user.email)"
    Write-Host "Active: $($loginResponse.user.is_active)"
    
} catch {
    Write-Host "❌ Login failed" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Start-Sleep -Seconds 1

# Test 3: Get Current User (Protected Endpoint)
if ($global:accessToken) {
    Write-Host "`nTest 3: Get Current User (Protected)" -ForegroundColor Yellow
    $headers = @{
        "Authorization" = "Bearer $global:accessToken"
    }
    
    try {
        $userResponse = Invoke-RestMethod -Uri "$baseUrl/users/me" `
            -Method Get `
            -Headers $headers
        
        Write-Host "✅ Protected endpoint successful!" -ForegroundColor Green
        Write-Host "User ID: $($userResponse.id)"
        Write-Host "Email: $($userResponse.email)"
        
    } catch {
        Write-Host "❌ Protected endpoint failed" -ForegroundColor Red
        Write-Host $_.Exception.Message
    }
}

Start-Sleep -Seconds 1

# Test 4: Test Invalid Token
Write-Host "`nTest 4: Test Invalid Token (should fail)" -ForegroundColor Yellow
$invalidHeaders = @{
    "Authorization" = "Bearer invalid-token-12345"
}

try {
    $invalidResponse = Invoke-RestMethod -Uri "$baseUrl/users/me" `
        -Method Get `
        -Headers $invalidHeaders
    
    Write-Host "⚠️ Unexpected success with invalid token!" -ForegroundColor Yellow
    
} catch {
    Write-Host "✅ Correctly rejected invalid token" -ForegroundColor Green
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`n=== Testing Complete ===`n" -ForegroundColor Cyan

