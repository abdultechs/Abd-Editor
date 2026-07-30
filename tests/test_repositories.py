import unittest
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tempfile
from app.database.connection import set_db_path, close_connection
from app.database.migrations import run_migrations
from app.database.repositories.log_repository import LogRepository
from app.database.repositories.history_repository import HistoryRepository


class TestRepositories(unittest.TestCase):
    def setUp(self):
        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp_db.close()
        set_db_path(self.tmp_db.name)
        run_migrations()
        self.log_repo = LogRepository()
        self.history_repo = HistoryRepository()

    def tearDown(self):
        close_connection()
        set_db_path(None)
        if os.path.exists(self.tmp_db.name):
            try:
                os.remove(self.tmp_db.name)
            except OSError:
                pass

    def test_log_repository_create(self):
        self.log_repo.create("info", "test", "Test log message")
        logs = self.log_repo.list_recent(5)
        self.assertTrue(any(l["message"] == "Test log message" for l in logs))

    def test_history_repository_create(self):
        self.history_repo.create(
            file_name="test.mp4",
            input_path="/path/test.mp4",
            output_path="/path/out.mp4",
            status="completed",
        )
        hist = self.history_repo.list_all()
        self.assertTrue(len(hist) > 0)

    def test_job_repository_recovery(self):
        from app.database.repositories.job_repository import JobRepository
        job_repo = JobRepository()
        job = job_repo.create("test_stuck.mp4", "/in/test.mp4", "/out/test.mp4")
        job_repo.mark_started(job["id"])
        stuck_job = job_repo.find_by_id(job["id"])
        self.assertEqual(stuck_job["status"], "processing")

        count = job_repo.recover_stuck_jobs()
        self.assertGreaterEqual(count, 1)
        recovered_job = job_repo.find_by_id(job["id"])
        self.assertEqual(recovered_job["status"], "waiting")
        self.assertEqual(recovered_job["progress"], 0)

    def test_job_repository_deletion(self):
        from app.database.repositories.job_repository import JobRepository
        job_repo = JobRepository()
        j1 = job_repo.create("del1.mp4", "/in/del1.mp4", "/out/del1.mp4")
        j2 = job_repo.create("del2.mp4", "/in/del2.mp4", "/out/del2.mp4")
        job_repo.mark_completed(j2["id"], 1000, "10s", "10s", "1920x1080", "1920x1080", "ffmpeg")

        job_repo.delete_waiting()
        self.assertIsNone(job_repo.find_by_id(j1["id"]))
        self.assertIsNotNone(job_repo.find_by_id(j2["id"]))

        job_repo.delete_many([j2["id"]])
        self.assertIsNone(job_repo.find_by_id(j2["id"]))


if __name__ == "__main__":
    unittest.main()
