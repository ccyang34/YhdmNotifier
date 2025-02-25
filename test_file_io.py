import unittest
import os
import json
import datetime

# 假设原代码文件名为 动漫更新自动微信推送-YHDM.py
from 动漫更新自动微信推送-YHDM import (
    load_history,
    save_history
)

class TestFileIO(unittest.TestCase):
    def setUp(self):
        # 在每个测试用例执行前，若历史记录文件存在则删除
        if os.path.exists('update_history.json'):
            os.remove('update_history.json')

    def tearDown(self):
        # 在每个测试用例执行后，若历史记录文件存在则删除
        if os.path.exists('update_history.json'):
            os.remove('update_history.json')

    def test_load_and_save_history(self):
        # 测试加载和保存历史记录的功能
        # 加载初始历史记录
        initial_history = load_history()
        self.assertEqual(isinstance(initial_history, dict), True)
        self.assertEqual('date' in initial_history, True)
        self.assertEqual('data' in initial_history, True)

        # 修改历史记录
        test_date = str(datetime.date.today())
        test_data = ['test_content_1', 'test_content_2']
        updated_history = {
            'date': test_date,
            'data': test_data
        }

        # 保存修改后的历史记录
        save_history(updated_history)

        # 再次加载历史记录
        reloaded_history = load_history()
        self.assertEqual(reloaded_history, updated_history)

if __name__ == '__main__':
    unittest.main()
