import unittest
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from api.index import create_app
from api.config import Config
from api.db import init_db

class TestApexTaskVercelAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_health_check(self):
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['auth_user'], Config.APP_USERNAME)
        print("[TEST 1] Health Check Passed")

    def test_02_auth_flow(self):
        # 1. Invalid login
        res = self.client.post('/api/auth/login', json={
            "username": Config.APP_USERNAME,
            "password": "wrongpassword"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data['success'])

        # 2. Valid login
        res = self.client.post('/api/auth/login', json={
            "username": Config.APP_USERNAME,
            "password": Config.APP_PASSWORD
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('token', data)
        token = data['token']

        # 3. Verify token
        res_verify = self.client.get('/api/auth/verify', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res_verify.status_code, 200)
        vdata = res_verify.get_json()
        self.assertTrue(vdata['valid'])
        self.assertEqual(vdata['username'], Config.APP_USERNAME)
        print("[TEST 2] Authentication Flow Passed (Login & Verify)")

    def test_03_protected_routes_without_token(self):
        res = self.client.get('/api/tasks/today')
        self.assertEqual(res.status_code, 401)

        res = self.client.get('/api/records/weekly')
        self.assertEqual(res.status_code, 401)

        res = self.client.get('/api/user/profile')
        self.assertEqual(res.status_code, 401)
        print("[TEST 3] Protected Routes Security Enforcement Passed")

    def test_04_task_crud_with_token(self):
        # Login to get token
        res_login = self.client.post('/api/auth/login', json={
            "username": Config.APP_USERNAME,
            "password": Config.APP_PASSWORD
        })
        token = res_login.get_json()['token']
        headers = {'Authorization': f'Bearer {token}'}

        # 1. Create Task
        res = self.client.post('/api/tasks', headers=headers, json={
            "title": "Deploy to Vercel Serverless",
            "notes": "Configure Environment Variables",
            "priority": "high"
        })
        self.assertEqual(res.status_code, 201)
        task = res.get_json()['task']
        task_id = task['id']

        # 2. Complete Task
        res_comp = self.client.put(f'/api/tasks/{task_id}/complete', headers=headers, json={})
        self.assertEqual(res_comp.status_code, 200)
        cdata = res_comp.get_json()
        self.assertEqual(cdata['result']['status'], 'complete')
        self.assertGreater(cdata['result']['xp_delta'], 0)

        # 3. Delete Task
        res_del = self.client.delete(f'/api/tasks/{task_id}', headers=headers)
        self.assertEqual(res_del.status_code, 200)
        print("[TEST 4] Task Lifecycle CRUD with JWT Passed")

    def test_05_dashboards_with_token(self):
        res_login = self.client.post('/api/auth/login', json={
            "username": Config.APP_USERNAME,
            "password": Config.APP_PASSWORD
        })
        token = res_login.get_json()['token']
        headers = {'Authorization': f'Bearer {token}'}

        # Weekly
        res_w = self.client.get('/api/records/weekly?date=today', headers=headers)
        self.assertEqual(res_w.status_code, 200)
        self.assertEqual(len(res_w.get_json()['records']['days']), 7)

        # Monthly
        res_m = self.client.get('/api/records/monthly', headers=headers)
        self.assertEqual(res_m.status_code, 200)
        self.assertIn('days', res_m.get_json()['records'])

        # Yearly
        res_y = self.client.get('/api/records/yearly', headers=headers)
        self.assertEqual(res_y.status_code, 200)
        self.assertIn('trend', res_y.get_json()['records'])
        print("[TEST 5] Analytics Dashboards with JWT Passed")

    def test_06_gamification_and_reset(self):
        res_login = self.client.post('/api/auth/login', json={
            "username": Config.APP_USERNAME,
            "password": Config.APP_PASSWORD
        })
        token = res_login.get_json()['token']
        headers = {'Authorization': f'Bearer {token}'}

        # Chest
        res_chest = self.client.post('/api/rewards/chest', headers=headers, json={})
        self.assertEqual(res_chest.status_code, 200)
        self.assertTrue(res_chest.get_json()['success'])

        # Reset
        res_reset = self.client.post('/api/user/reset', headers=headers, json={})
        self.assertEqual(res_reset.status_code, 200)
        p = res_reset.get_json()['profile']
        self.assertEqual(p['xp'], 0)
        self.assertEqual(p['level'], 1)
        self.assertEqual(p['streak'], 0)
        print("[TEST 6] Gamification & Reset with JWT Passed")

if __name__ == '__main__':
    unittest.main()
