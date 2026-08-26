import requests
import json

# 测试登录接口
url = 'http://localhost:5000/login'
data = {
    'username': 'admin',
    'password': '123456'
}

headers = {
    'Content-Type': 'application/json'
}

response = requests.post(url, json=data, headers=headers)
print('Status code:', response.status_code)
print('Response:', response.text)

# 如果登录成功，测试 match_jobs 接口
if response.status_code == 200:
    try:
        result = response.json()
        if result.get('ok'):
            token = result.get('token')
            print('Login successful, token:', token)
            
            # 测试 match_jobs 接口
            match_url = 'http://localhost:5000/match_jobs'
            match_data = {
                'goal': '测试'
            }
            match_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            match_response = requests.post(match_url, json=match_data, headers=match_headers)
            print('Match jobs status code:', match_response.status_code)
            print('Match jobs response:', match_response.text)
    except Exception as e:
        print('Error parsing response:', e)