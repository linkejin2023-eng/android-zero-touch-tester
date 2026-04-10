import os
import fcntl
import logging

class LockManager:
    def __init__(self, lock_file="test.lock"):
        self.lock_file = lock_file
        self.fd = None

    def acquire(self, blocking=True):
        """Acquire the lock. Returns True if successful, False otherwise."""
        try:
            self.fd = open(self.lock_file, 'w')
            # LOCK_EX: Exclusive lock
            # If not blocking, add LOCK_NB
            lock_flags = fcntl.LOCK_EX
            if not blocking:
                lock_flags |= fcntl.LOCK_NB
            
            if blocking:
                logging.info(f"Waiting for lock on {self.lock_file}...")
                
            fcntl.flock(self.fd, lock_flags)
            logging.info(f"Lock acquired: {self.lock_file}")
            return True
        except (IOError, BlockingIOError):
            if not blocking:
                logging.warning(f"Lock already held by another process: {self.lock_file}")
            return False
        except Exception as e:
            logging.error(f"Error acquiring lock: {e}")
            return False

    def release(self):
        """Release the lock."""
        if self.fd:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                self.fd.close()
                logging.info(f"Lock released: {self.lock_file}")
            except Exception as e:
                logging.error(f"Error releasing lock: {e}")
            finally:
                self.fd = None
                if os.path.exists(self.lock_file):
                    try:
                        os.remove(self.lock_file)
                    except:
                        pass

    def __enter__(self):
        if self.acquire():
            return self
        raise BlockingIOError(f"Could not acquire lock on {self.lock_file}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
