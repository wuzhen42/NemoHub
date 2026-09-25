"""Account-specific API transport. No automatic retries of billable requests."""
import requests


class ApiError(Exception):
    def __init__(self, status, detail):
        self.status = status
        super().__init__(str(detail))


class ApiSession:
    def __init__(self, username, base_url, proxies=None):
        self.username = username.strip()
        self.base_url = base_url.rstrip('/')
        self.proxies = proxies or {}
        self.is_subaccount = '/' in self.username
        self.is_studio_owner = False
        self.cookies = requests.cookies.RequestsCookieJar()
        self.token = None

    def request(self, method, path, **kwargs):
        headers = dict(kwargs.pop('headers', {}))
        if self.is_subaccount and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        response = requests.request(
            method, self.base_url + path, cookies=self.cookies,
            headers=headers, proxies=self.proxies, timeout=(10, 60), **kwargs,
        )
        if not response.ok:
            try:
                detail = response.json().get('detail', response.reason)
            except ValueError:
                detail = response.reason
            response.close()
            raise ApiError(response.status_code, detail)
        return response

    def login(self, password):
        path = '/client/login' if self.is_subaccount else '/login'
        response = self.request('POST', path, data={'username': self.username, 'password': password})
        if response.status_code == 202:
            return False
        if self.is_subaccount:
            self.token = response.json()['access_token']
        else:
            self.cookies.update(response.cookies)
            self.profile()
        return True

    def verify_mfa(self, code):
        response = self.request('POST', '/login/verify-mfa', params={'username': self.username, 'code': code})
        self.cookies.update(response.cookies)
        self.profile()
        return True

    def profile(self):
        data = self.request('GET', '/users/whoami').json()
        self.is_studio_owner = bool(data.get('is_studio'))
        return data

    def licenses(self):
        if self.is_subaccount:
            return self.request('GET', '/client/licenses').json()['seats']
        data = self.profile()
        if self.is_studio_owner:
            return []
        return [seat for seat in data['seats'] if not seat.get('subaccount_id')]

    def issue(self, action, payload):
        if self.is_subaccount:
            return self.request('POST', f'/client/license/{action}', json=payload).json()
        if self.is_studio_owner:
            raise ApiError(403, 'Sign in with a studio subaccount to activate a license.')
        return self.request('POST', f'/license/seat/{action}', params=payload).json()

    def download_license(self, seat_id):
        if not self.is_subaccount:
            raise ApiError(400, 'License recovery is available for studio subaccounts.')
        return self.request('GET', f'/client/licenses/{seat_id}').json()

    def deactivate(self, seat_id, expected_revision=None):
        if self.is_subaccount:
            return self.request('POST', '/client/license/deactivate', json={
                'seat': seat_id, 'expected_revision': expected_revision,
            })
        self.request('POST', '/license/seat/deactivate', params={'seat': seat_id})
