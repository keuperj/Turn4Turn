"""Private, persistent server usage counters; never included in player state."""
import json
import logging
import os
import tempfile
import threading
import unicodedata
from pathlib import Path


class ServerStatistics:
    """Serialize updates from HTTP threads and atomically replace the local file."""

    def __init__(self, path=None):
        self.path=Path(path) if path is not None else None
        self.lock=threading.RLock()
        self.users={}
        if self.path and self.path.exists():
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if data.get('version')!=1 or not isinstance(data.get('users'),dict):
                raise ValueError('Invalid server statistics file; restore it from backup.')
            for key,entry in data['users'].items():
                if (not isinstance(entry,dict) or not isinstance(entry.get('username'),str)
                        or type(entry.get('games_played')) is not int or entry['games_played']<0):
                    raise ValueError('Invalid server statistics user record.')
            self.users=data['users']
            self.path.chmod(0o600)

    def record(self, username, *, played=False):
        """Register a name, optionally counting a successfully deployed mission."""
        name=unicodedata.normalize('NFKC',username.strip())
        key=name.casefold()
        with self.lock:
            if key not in self.users:
                self.users[key]={'username':name,'games_played':0}
            if played:self.users[key]['games_played']+=1
            self._save()

    def snapshot(self):
        """Return an independent snapshot for local administration and tests."""
        with self.lock:
            users={key:dict(entry) for key,entry in self.users.items()}
            return dict(version=1,unique_users=len(users),
                        games_played=sum(entry['games_played'] for entry in users.values()),users=users)

    def _save(self):
        if self.path is None:return
        temporary=None
        try:
            self.path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            # mkstemp creates a private (0600) file in the same filesystem.
            fd,temporary=tempfile.mkstemp(prefix='.statistics-',dir=self.path.parent)
            with os.fdopen(fd,'w',encoding='utf-8') as stream:
                json.dump(self.snapshot(),stream,ensure_ascii=False,indent=2)
                stream.write('\n');stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.path)
        except OSError:
            # A statistics disk error must not lose an already accepted gameplay action.
            # Keep counters in memory and retry persistence on the next update.
            logging.exception('Could not save private server statistics to %s',self.path)
        finally:
            if temporary and os.path.exists(temporary):os.unlink(temporary)
