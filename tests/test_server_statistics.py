"""Persistence, concurrent updates, and failure recovery for private counters."""
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from server_statistics import ServerStatistics


class ServerStatisticsTests(unittest.TestCase):
    def test_names_merge_and_counters_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'private'/'statistics.json'
            stats=ServerStatistics(path)
            stats.record(' Alice ')
            stats.record('ALICE',played=True)
            stats.record('Ｂob',played=True)
            restored=ServerStatistics(path)
            restored.record('bob',played=True)
            data=json.loads(path.read_text())
            self.assertEqual(data['unique_users'],2)
            self.assertEqual(data['games_played'],3)
            self.assertEqual(data['users']['alice'],dict(username='Alice',games_played=1))
            self.assertEqual(data['users']['bob']['games_played'],2)
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777,0o700)

    def test_concurrent_games_do_not_lose_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'statistics.json'
            stats=ServerStatistics(path)
            with ThreadPoolExecutor(max_workers=10) as pool:
                list(pool.map(lambda _:stats.record('Player',played=True),range(80)))
            self.assertEqual(ServerStatistics(path).snapshot()['games_played'],80)

    def test_failed_replace_preserves_file_and_retries_in_memory_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'statistics.json'
            stats=ServerStatistics(path);stats.record('Player')
            with patch('server_statistics.os.replace',side_effect=OSError('disk error')):
                with self.assertLogs(level='ERROR'):stats.record('Player',played=True)
            self.assertEqual(json.loads(path.read_text())['games_played'],0)
            stats.record('Player')
            self.assertEqual(ServerStatistics(path).snapshot()['games_played'],1)
            self.assertEqual(list(path.parent.glob('.statistics-*')),[])

    def test_corrupt_history_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'statistics.json';path.write_text('broken')
            with self.assertRaises(ValueError):ServerStatistics(path)
            self.assertEqual(path.read_text(),'broken')
