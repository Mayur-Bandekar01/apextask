import unittest
import json
import datetime
from backend.app import create_app
from backend.models.task import TaskModel
from backend.models.user import UserModel
from backend.models.badge import BadgeModel
from backend.models.record import RecordModel

class TodoAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_health(self):
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['status'] == 'healthy')
        print(f"[TEST 1] Health OK, DB Engine: {data.get('database_engine')}")

    def test_02_user_profile(self):
        res = self.client.get('/api/user/profile?user_id=1')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('xp', data['profile'])
        self.assertIn('level', data['profile'])
        print(f"[TEST 2] User Profile: Level {data['profile']['level']}, XP {data['profile']['xp']}")

    def test_03_create_task(self):
        payload = {
            "title": "Master Full-Stack Suite",
            "notes": "Verify tables, logs and cross-day synchronization",
            "priority": "high",
            "deadline": (datetime.datetime.now() + datetime.timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")
        }
        res = self.client.post('/api/tasks', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['task']['title'], "Master Full-Stack Suite")
        self.assertEqual(data['task']['priority'], "high")
        task_id = data['task']['id']
        print(f"[TEST 3] Task Created with ID: {task_id}")

        # Check logs
        res_logs = self.client.get(f'/api/tasks/{task_id}/logs')
        self.assertEqual(res_logs.status_code, 200)
        log_data = res_logs.get_json()
        self.assertTrue(len(log_data['logs']) >= 1)
        print(f"[TEST 3] Log entry verified: {log_data['logs'][0]['change_description']}")

        # Complete task
        res_comp = self.client.put(f'/api/tasks/{task_id}/complete', data=json.dumps({}), content_type='application/json')
        self.assertEqual(res_comp.status_code, 200)
        comp_data = res_comp.get_json()
        self.assertEqual(comp_data['result']['status'], 'complete')
        self.assertEqual(comp_data['result']['xp_delta'], 50)
        print(f"[TEST 3] Task completed successfully. XP Delta: {comp_data['result']['xp_delta']}")

    def test_04_weekly_and_monthly_records(self):
        res_w = self.client.get('/api/records/weekly?date=today')
        self.assertEqual(res_w.status_code, 200)
        w_data = res_w.get_json()
        self.assertTrue(w_data['success'])
        self.assertEqual(len(w_data['records']['days']), 7)
        print(f"[TEST 4] Weekly days count: {len(w_data['records']['days'])}, Total completed: {w_data['records']['total_completed']}")

        res_m = self.client.get('/api/records/monthly')
        self.assertEqual(res_m.status_code, 200)
        m_data = res_m.get_json()
        self.assertTrue(m_data['success'])
        self.assertTrue(len(m_data['records']['days']) >= 28)
        print(f"[TEST 4] Monthly days count: {len(m_data['records']['days'])}, Month total completed: {m_data['records']['summary']['total_completed']}")

        res_y = self.client.get('/api/records/yearly')
        self.assertEqual(res_y.status_code, 200)
        y_data = res_y.get_json()
        self.assertTrue(y_data['success'])
        self.assertEqual(len(y_data['records']['trend']['labels']), 12)
        print(f"[TEST 4] Yearly trend months: {len(y_data['records']['trend']['labels'])}")

    def test_05_rollover_and_shame_board(self):
        old_date = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
        past_deadline = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        task = TaskModel.create_task(1, "Old Forgotten Goal", "Must carry over", "medium", past_deadline, old_date)
        
        # Test rollover
        res_roll = self.client.post('/api/tasks/rollover', data=json.dumps({}), content_type='application/json')
        self.assertEqual(res_roll.status_code, 200)
        roll_data = res_roll.get_json()
        self.assertTrue(roll_data['success'])
        print(f"[TEST 5] Rolled over tasks count: {roll_data['rollover']['rolled_count']}")

        # Test shame board
        res_shame = self.client.get('/api/tasks/missed')
        self.assertEqual(res_shame.status_code, 200)
        shame_data = res_shame.get_json()
        self.assertTrue(shame_data['success'])
        print(f"[TEST 5] Shame board missed tasks count: {shame_data['count']}")

    def test_06_chest_reward(self):
        res_chest = self.client.post('/api/rewards/chest', data=json.dumps({}), content_type='application/json')
        self.assertEqual(res_chest.status_code, 200)
        chest_data = res_chest.get_json()
        self.assertTrue(chest_data['success'])
        reward_type = chest_data['reward']['type']
        print(f"[TEST 6] Chest reward unlocked successfully (Type: {reward_type})")

if __name__ == '__main__':
    unittest.main()
