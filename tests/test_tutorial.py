"""Guided lessons use real AP/ammunition while remaining safe and replayable."""
import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
import server
from game import Game
from tutorial import TutorialGame, LESSONS


def order(lesson):
    """Return the real gameplay order described by a lesson."""
    return dict(unit='s0',**{k:v for k,v in lesson.items() if k in ('action','x','y','z','weapon')})


class TutorialTests(unittest.TestCase):
    def test_complete_lesson_sequence(self):
        """Every step succeeds using the advertised action and normal AP costs."""
        g=TutorialGame();expected_ap=[1,0,2,1,1,0,2,2,0]
        initial={u['id']:g.position(u) for u in g.alive('alien')}
        for index,lesson in enumerate(LESSONS):
            with self.subTest(step=index):
                if lesson['action'] in ('move','attack'):
                    before=g.state();preview=g.preview(order(lesson))
                    self.assertEqual(g.state(),before)
                    self.assertGreater(preview['cost'],0)
                    if lesson['action']=='attack':self.assertEqual(preview['chance'],100)
                g.action(order(lesson))
                self.assertEqual(g.units[0]['ap'],expected_ap[index])
                self.assertEqual(g.tutorial_step,index+1)
                self.assertEqual(g.units[0]['hp'],g.units[0]['max_hp'])
                self.assertTrue(all(g.position(u)==initial[u['id']] for u in g.units if u['team']=='alien'))
        self.assertEqual(g.status,'victory')
        self.assertTrue(g.state()['tutorial']['complete'])
        self.assertEqual(g.mission_statistics()['shots_fired'],2)
        self.assertEqual(g.mission_statistics()['enemies_killed'],4)
        self.assertEqual(g.round,3)
        with self.assertRaises(ValueError):g.action(order(LESSONS[-1]))

    def test_wrong_actions_never_spend_resources_or_skip_steps(self):
        """Off-lesson commands cannot strand the player or move the targets."""
        g=TutorialGame();before=g.state()
        for data in [dict(action='end_turn',unit='s0'),dict(action='deploy'),dict(action='shoot',unit='s0',target='e0'),dict(action='move',unit='s0',x=8,y=15,z=0),dict(action='move',unit='e0',x=6,y=15,z=0)]:
            with self.assertRaisesRegex(ValueError,'Training step'):g.action(data)
            self.assertEqual(g.state(),before)
        with self.assertRaises(ValueError):g.preview(dict(action='move',unit='s0',x=7,y=15,z=0))
        self.assertEqual(g.state(),before)

    def test_restart_and_normal_missions_remain_independent(self):
        """Training is fixed and normal combat retains its actual hit chance."""
        g=TutorialGame();g.action(order(LESSONS[0]));fresh=TutorialGame()
        self.assertEqual(fresh.tutorial_step,0)
        self.assertEqual(fresh.position(fresh.units[0]),(6,18,0))
        self.assertEqual(fresh.state(),TutorialGame().state())
        self.assertNotIn('tutorial',Game(41,'urban').state())
        self.assertLessEqual(Game.chance(fresh,fresh.units[0],fresh.units[1]),95)

    def test_http_consent_resume_restart_and_normal_game(self):
        """The API preserves consent, per-player isolation and resume semantics."""
        original=server.registry,server.game
        server.registry=server.SessionRegistry()
        class QuietHandler(server.Handler):
            def log_message(self,*args):pass
        httpd=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        def post(path,data,cookie=''):
            conn=http.client.HTTPConnection('127.0.0.1',httpd.server_port)
            conn.request('POST',path,json.dumps(data),{'Content-Type':'application/json','Cookie':cookie})
            res=conn.getresponse();result=res.status,json.loads(res.read());conn.close();return result
        try:
            self.assertEqual(post('/api/tutorial',{})[0],401)
            first=server.registry.create('Trainee');second=server.registry.create('Other player');other=second.game
            cookie=f'{server.USER_COOKIE}={first.user_id}'
            status,state=post('/api/tutorial',{},cookie);self.assertEqual(status,200);self.assertEqual(state['tutorial']['step'],0)
            post('/api/action',order(LESSONS[0]),cookie)
            self.assertEqual(post('/api/tutorial',{'resume':True},cookie)[1]['tutorial']['step'],1)
            self.assertEqual(post('/api/tutorial',{},cookie)[1]['tutorial']['step'],0)
            self.assertIs(second.game,other)
            status,state=post('/api/new',{'theme':'urban','size':24},cookie)
            self.assertEqual(status,200);self.assertEqual(state['status'],'loadout');self.assertNotIn('tutorial',state)
        finally:
            httpd.shutdown();httpd.server_close();server.registry,server.game=original
