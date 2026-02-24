import requests
import json
from typing import Dict, Optional

def login_step1(email: str, b64_password: str) -> str:
    """
    First step of login - send email and password to get OTP JWT token
    Returns the OTP JWT token needed for step 2
    """
    url = 'https://api6.axiom.trade/login-password-v2'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Content-Type': 'application/json',
        'Origin': 'https://axiom.trade',
        'Connection': 'keep-alive',
        'Referer': 'https://axiom.trade/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'TE': 'trailers'
    }
    
    data = {
        "email": email,
        "b64Password": b64_password
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    
    result = response.json()
    return result.get('otpJwtToken')

def login_step2(otp_jwt_token: str, otp_code: str, email: str, b64_password: str) -> Dict:
    """
    Second step of login - send OTP code to complete authentication
    Returns client credentials (clientSecret, orgId, userId)
    """
    url = 'https://api10.axiom.trade/login-otp'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Content-Type': 'application/json',
        'Origin': 'https://axiom.trade',
        'Connection': 'keep-alive',
        'Referer': 'https://axiom.trade/',
        'Cookie': f'auth-otp-login-token={otp_jwt_token}',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'TE': 'trailers'
    }
    
    data = {
        "code": otp_code,
        "email": email,
        "b64Password": b64_password
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    
    return response.json()

def complete_login(email: str, b64_password: str, otp_code: str) -> Dict:
    """
    Complete the full login process
    Returns client credentials (clientSecret, orgId, userId)
    """
    print("Step 1: Sending email and password...")
    otp_jwt_token = login_step1(email, b64_password)
    print("OTP JWT token received")
    
    print("Step 2: Sending OTP code...")
    credentials = login_step2(otp_jwt_token, otp_code, email, b64_password)
    print("Login completed successfully")
    
    return credentials

def refresh_access_token(refresh_token):
    url = 'https://api9.axiom.trade/refresh-access-token'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Origin': 'https://axiom.trade',
        'Connection': 'keep-alive',
        'Referer': 'https://axiom.trade/',
        'Cookie': f'auth-refresh-token={refresh_token}',
        'Content-Length': '0',
        'TE': 'trailers'
    }

    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json().get('auth-access-token')

def get_trending_tokens(access_token, time_period='1h'):
    url = f'https://api6.axiom.trade/meme-trending?timePeriod={time_period}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Origin': 'https://axiom.trade',
        'Connection': 'keep-alive',
        'Referer': 'https://axiom.trade/',
        'Cookie': f'auth-access-token={access_token}',
        'TE': 'trailers'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

if __name__ == '__main__':
    print("Axiom Trade API - Login and Trending Tokens")
    print("=" * 50)
    
    # Option to either login fresh or use existing refresh token
    use_existing_token = input("Do you have a refresh token? (y/n): ").lower().strip() == 'y'
    
    if use_existing_token:
        refresh_token = input('Enter your refresh token: ')
        try:
            access_token = refresh_access_token(refresh_token)
            print('Access token refreshed successfully.')
        except requests.exceptions.RequestException as e:
            print('Error refreshing token:', e)
            exit(1)
    else:
        # Fresh login process
        email = input('Enter your email: ')
        b64_password = input('Enter your base64 encoded password: ')
        
        try:
            # Step 1: Get OTP token
            otp_jwt_token = login_step1(email, b64_password)
            print('OTP request sent. Check your email/phone for the code.')
            
            # Step 2: Complete login with OTP
            otp_code = input('Enter the OTP code: ')
            credentials = login_step2(otp_jwt_token, otp_code, email, b64_password)
            
            print('Login successful!')
            print(f"Client Secret: {credentials.get('clientSecret')}")
            print(f"Org ID: {credentials.get('orgId')}")
            print(f"User ID: {credentials.get('userId')}")
            
            # For now, we'll need to implement getting access token from credentials
            # This might require additional API calls that aren't shown in the examples
            print("\nNote: You'll need to use these credentials to get access tokens for API calls.")
            exit(0)
            
        except requests.exceptions.RequestException as e:
            print('Login error:', e)
            exit(1)
    
    # Get trending tokens
    try:
        time_period = input('Enter time period (1h, 24h, 7d) [default: 1h]: ').strip() or '1h'
        trending_tokens = get_trending_tokens(access_token, time_period)
        
        print(f'\nTrending tokens for {time_period}:')
        print('=' * 30)
        print(json.dumps(trending_tokens, indent=2))
        
    except requests.exceptions.RequestException as e:
        print('Error fetching trending tokens:', e)
