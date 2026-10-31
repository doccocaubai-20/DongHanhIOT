import os
from pathlib import Path
import tempfile
import time
import unittest
from io import BytesIO

temporary = tempfile.TemporaryDirectory(dir=os.getenv('TEST_TEMP_DIR'))
os.environ['DATA_DIR'] = temporary.name
os.environ['PROJECT_MODE'] = 'test'
os.environ['AI_MODEL_DIR'] = ''
for name in ('CAREGIVER','PHONE','TEST','CHEST','CANE'):
    os.environ[name+'_TOKEN'] = name.lower()+'-test-token-'+'x'*32
os.environ['REMOTE_TOKEN'] = 'remote-test-token-'+'x'*32
os.environ['WEARER_AI_ALERT'] = '0'
os.environ.pop('AI_PROVIDER', None)

from fastapi.testclient import TestClient
from PIL import Image
from server import app as module

def auth(role): return {'Authorization':'Bearer '+os.environ[role.upper()+'_TOKEN']}
def jpeg():
    out=BytesIO();Image.new('RGB',(40,30),'green').save(out,'JPEG');return out.getvalue()

class FakePush:
    def __init__(self,enabled):self.enabled=enabled;self.public_key='fake-public-key' if enabled else ''
    def send(self,*a):return 201

class APITest(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(module.app)
        with module.db() as c:
            for table in ('events','commands','devices','location','messages','push_subscriptions'): c.execute('DELETE FROM '+table)
            c.execute('UPDATE settings SET periodic=1,interval_s=60,last_periodic=0')
        module.MODE='test';module.CAMERA='phone';module.CONTROLLER='test';module.FIND_TARGET='test';module.EVENT_SOURCES=('test',)
        module.PUSH=FakePush(True);module.WEARER_AI_ALERT=False

    def event(self,eid='sos-test-001',role='test',kind='sos'):
        return self.client.post('/api/v1/events',headers=auth(role),json={'event_id':eid,'kind':kind})
    def state(self,on=True,role='test'):
        return self.client.post('/api/v1/state',headers=auth(role),json={'periodic_enabled':on,'sensor_valid':False})
    def commands(self,role='phone'):
        return self.client.get('/api/v1/commands',headers=auth(role)).json()['commands']
    def upload(self,eid='sos-test-001',payload=None,role='phone'):
        return self.client.post('/api/v1/events/'+eid+'/image',headers={**auth(role),'Content-Type':'image/jpeg','X-Captured-At':str(time.time())},content=payload if payload is not None else jpeg())

    def test_auth_required(self):
        self.assertEqual(self.client.get('/api/v1/dashboard').status_code,401)
        self.assertEqual(self.client.get('/api/v1/dashboard',headers=auth('test')).status_code,403)
    def test_event_is_idempotent(self):
        self.assertEqual(self.event().status_code,200)
        self.assertTrue(self.event().json()['duplicate'])
        self.assertEqual(len(self.commands()),1)
    def test_duplicate_other_owner_rejected(self):
        self.event();self.assertEqual(self.event(role='phone').status_code,409)
    def test_sos_capture_even_privacy_off(self):
        self.state(False);self.event();commands=self.commands();self.assertEqual(commands[0]['reason'],'sos')
        self.assertEqual(self.upload().status_code,200)
    def test_periodic_requires_local_consent(self):
        self.state(False);self.assertEqual(self.commands(),[])
        self.state(True);self.assertEqual(self.commands()[0]['reason'],'periodic')
    def test_stale_controller_does_not_enable_periodic(self):
        self.state()
        with module.db() as c:c.execute('UPDATE devices SET last_seen=?',(time.time()-60,))
        self.assertEqual(self.commands(),[])
    def test_remote_setting_cannot_override_local_off(self):
        self.state(False)
        r=self.client.put('/api/v1/settings',headers=auth('caregiver'),json={'periodic_enabled':True,'interval_s':15})
        self.assertEqual(r.status_code,200);self.assertEqual(self.commands(),[])
    def test_privacy_change_blocks_inflight_periodic(self):
        self.state();cmd=self.commands()[0];self.state(False)
        self.assertEqual(self.upload(cmd['event_id']).status_code,409)
    def test_command_lease_and_redelivery(self):
        self.event();first=self.commands();self.assertEqual(self.commands(),[])
        with module.db() as c:c.execute('UPDATE commands SET lease_until=0')
        self.assertEqual(self.commands()[0]['id'],first[0]['id'])
    def test_cannot_ack_photo_before_upload(self):
        self.event();cmd=self.commands()[0]
        r=self.client.post('/api/v1/commands/'+cmd['id']+'/ack',headers=auth('phone'),json={'result':'done'})
        self.assertEqual(r.status_code,409)
    def test_upload_private_idempotent_and_ack(self):
        self.event();cmd=self.commands()[0]
        self.assertEqual(self.upload().status_code,200)
        self.assertTrue(self.upload().json()['duplicate'])
        r=self.client.get('/api/v1/events/sos-test-001/image',headers=auth('caregiver'))
        self.assertEqual(r.status_code,200);self.assertEqual(r.headers['content-type'],'image/jpeg')
        self.assertEqual(self.client.get('/api/v1/events/sos-test-001/image').status_code,401)
        self.assertEqual(self.client.post('/api/v1/commands/'+cmd['id']+'/ack',headers=auth('phone'),json={'result':'done'}).status_code,200)
    def test_invalid_and_oversized_images(self):
        self.event();self.assertEqual(self.upload(payload=b'not a JPEG').status_code,400)
        self.assertEqual(self.upload(payload=b'X'*2_000_001).status_code,413)
    def test_wrong_camera_source_forbidden(self):
        self.event();self.assertEqual(self.upload(role='chest').status_code,403)
    def test_expired_capture_not_replaced_with_old_image(self):
        self.event()
        with module.db() as c:c.execute('UPDATE commands SET expires_at=?',(time.time()-1,))
        self.assertEqual(self.upload().status_code,410)
        board=self.client.get('/api/v1/dashboard',headers=auth('caregiver')).json()
        self.assertEqual(board['events'][0]['image_status'],'missing')
        self.assertFalse(board['events'][0]['has_image'])
    def test_location_role_and_monotonic_timestamp(self):
        pos={'latitude':10,'longitude':106,'accuracy':20,'captured_at':time.time()-1}
        self.assertEqual(self.client.post('/api/v1/location',headers=auth('test'),json=pos).status_code,403)
        self.assertEqual(self.client.post('/api/v1/location',headers=auth('phone'),json=pos).status_code,200)
        pos['captured_at']-=20
        self.assertTrue(self.client.post('/api/v1/location',headers=auth('phone'),json=pos).json()['ignored_older'])
        pos['latitude']=100
        self.assertEqual(self.client.post('/api/v1/location',headers=auth('phone'),json=pos).status_code,422)
    def test_find_expires_and_deduplicates(self):
        first=self.client.post('/api/v1/find-cane',headers=auth('caregiver')).json()
        second=self.client.post('/api/v1/find-cane',headers=auth('caregiver')).json()
        self.assertEqual(first['id'],second['id'])
        with module.db() as c:c.execute('UPDATE commands SET expires_at=?',(time.time()-1,))
        self.assertEqual(self.commands('test'),[])
    def test_chest_find_button_routes_to_cane_only_in_final(self):
        self.assertEqual(self.client.post('/api/v1/find-cane',headers=auth('chest')).status_code,403)
        module.MODE='final';module.FIND_TARGET='cane';module.EVENT_SOURCES=('chest','cane')
        response=self.client.post('/api/v1/find-cane',headers=auth('chest'))
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.commands('cane')[0]['kind'],'find')
    def test_ack_only_sos_and_only_caregiver(self):
        self.event()
        self.assertEqual(self.client.post('/api/v1/events/sos-test-001/ack',headers=auth('phone')).status_code,403)
        self.assertEqual(self.client.post('/api/v1/events/sos-test-001/ack',headers=auth('caregiver')).status_code,200)
    def test_final_cane_sos_routes_to_chest(self):
        module.MODE='final';module.CAMERA='chest';module.CONTROLLER='chest';module.FIND_TARGET='cane';module.EVENT_SOURCES=('chest','cane')
        self.assertEqual(self.event(role='cane').status_code,200)
        self.assertEqual(self.commands('phone'),[])
        self.assertEqual(self.commands('chest')[0]['reason'],'sos')
        self.assertEqual(self.upload(role='chest').status_code,200)
    def test_unconfigured_ai_returns_unknown(self):
        result=module.analyze(Path('not-needed.jpg'))
        self.assertEqual(result['status'],'not_configured');self.assertEqual(result['risk'],'unknown')
    def test_worker_processes_uploaded_image(self):
        with TestClient(module.app) as client:
            self.event();self.upload()
            deadline=time.monotonic()+4
            while time.monotonic()<deadline:
                board=client.get('/api/v1/dashboard',headers=auth('caregiver')).json()
                if board['events'][0]['image_status']=='ready':break
                time.sleep(.2)
            self.assertEqual(board['events'][0]['ai']['status'],'not_configured')

    # ---- Các điểm tích hợp từ smart_cane ----
    # ---- Tin nhắn web/app (thay Telegram) ----
    FCM='https://fcm.googleapis.com/fcm/send/abcdefghijklmnopqrstuvwxyz0123456789'
    def msgs(self):
        with module.db() as c: return [dict(r) for r in c.execute('SELECT * FROM messages ORDER BY created_at,rowid')]
    def add_sub(self,endpoint=None):
        with module.db() as c:c.execute('INSERT INTO push_subscriptions(endpoint,p256dh,auth,created_at) VALUES(?,?,?,?)',(endpoint or self.FCM,'p'*40,'a'*16,time.time()))
    def test_sos_and_drop_create_messages(self):
        self.event();self.event(eid='drop-test-001',kind='drop');self.event(eid='privacy-test-1',kind='privacy')
        rows=self.msgs()
        self.assertEqual([(r['stage'],r['level'],r['push_state']) for r in rows],[('sos','sos','pending'),('drop','warn','pending')])
        self.assertIn('SOS',rows[0]['title'])
        module.PUSH=FakePush(False);self.event(eid='sos-test-002')
        self.assertEqual(self.msgs()[-1]['push_state'],'unavailable')  # hộp tin vẫn có tin dù không đẩy được
    def test_push_no_device_retry_success_and_gone(self):
        self.event()
        self.assertTrue(module.push_one(lambda *a:201));self.assertEqual(self.msgs()[0]['push_state'],'no_device')
        self.event(eid='sos-test-002');self.add_sub();codes=[0]
        self.assertTrue(module.push_one(lambda *a:codes[-1]))
        row=[m for m in self.msgs() if m['event_id']=='sos-test-002'][0]
        self.assertEqual((row['push_state'],row['push_attempts']),('pending',1));self.assertGreater(row['next_try'],time.time())
        self.assertFalse(module.push_one(lambda *a:201))  # chưa đến hạn thử lại
        with module.db() as c:c.execute('UPDATE messages SET next_try=0')
        sent=[]
        self.assertTrue(module.push_one(lambda sub,payload,urgent:sent.append((payload['title'],urgent)) or 201))
        self.assertEqual(sent[0][1],True);self.assertEqual([m['push_state'] for m in self.msgs()],['no_device','sent'])
        self.event(eid='drop-test-001',kind='drop')
        self.assertTrue(module.push_one(lambda *a:410))
        with module.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM push_subscriptions').fetchone()[0],0)
        self.assertEqual(self.msgs()[-1]['push_state'],'no_device')
    def test_push_gives_up_after_max_attempts(self):
        self.event();self.add_sub()
        for _ in range(module.PUSH_MAX_ATTEMPTS):
            with module.db() as c:c.execute('UPDATE messages SET next_try=0')
            module.push_one(lambda *a:503)
        self.assertEqual(self.msgs()[0]['push_state'],'failed')
    def test_image_message_waits_for_sos_message(self):
        self.event();self.add_sub()
        with module.db() as c:module.add_message(c,'sos-test-001','image');c.execute("UPDATE messages SET next_try=? WHERE stage='sos'",(time.time()+99,))
        self.assertFalse(module.push_one(lambda *a:201))
    def test_missing_image_creates_image_message(self):
        self.event()
        with module.db() as c:c.execute('UPDATE commands SET expires_at=?',(time.time()-1,))
        self.client.get('/api/v1/dashboard',headers=auth('caregiver'))
        self.assertEqual([r['stage'] for r in self.msgs()],['sos','image'])
        self.assertIn('không nhận được ảnh',self.msgs()[1]['title'])
    def test_messages_api_and_read_state(self):
        self.event();self.event(eid='drop-test-001',kind='drop')
        self.assertEqual(self.client.get('/api/v1/messages',headers=auth('phone')).status_code,403)
        box=self.client.get('/api/v1/messages',headers=auth('caregiver')).json()
        self.assertEqual(box['unread'],2);self.assertEqual(box['messages'][0]['stage'],'drop')
        self.client.post('/api/v1/messages/read',headers=auth('caregiver'),json={'ids':['sos-test-001:sos']})
        self.assertEqual(self.client.get('/api/v1/dashboard',headers=auth('caregiver')).json()['unread_messages'],1)
        self.client.post('/api/v1/messages/read',headers=auth('caregiver'),json={})
        self.assertEqual(self.client.get('/api/v1/messages',headers=auth('caregiver')).json()['unread'],0)
        board=self.client.get('/api/v1/dashboard',headers=auth('caregiver')).json()
        self.assertIsNone(board['events'][-1]['acknowledged_at'])  # đọc tin không phải xác nhận SOS
    def test_push_subscription_validation(self):
        good={'endpoint':self.FCM,'keys':{'p256dh':'p'*40,'auth':'a'*16},'expirationTime':None}
        self.assertEqual(self.client.post('/api/v1/push/subscriptions',headers=auth('phone'),json=good).status_code,403)
        self.assertEqual(self.client.post('/api/v1/push/subscriptions',headers=auth('caregiver'),json=good).status_code,200)
        for bad in ('https://fcm.googleapis.com.evil.example/x'+'y'*20,'http://fcm.googleapis.com/fcm/send/'+'x'*20,'https://192.168.1.10/'+'x'*20,'https://user@fcm.googleapis.com/'+'x'*20):
            r=self.client.post('/api/v1/push/subscriptions',headers=auth('caregiver'),json={**good,'endpoint':bad})
            self.assertEqual(r.status_code,422,bad)
        self.assertEqual(self.client.post('/api/v1/push/subscriptions',headers=auth('caregiver'),json={**good,'keys':{'p256dh':'x'}}).status_code,422)
        self.assertEqual(self.client.get('/api/v1/push/config',headers=auth('caregiver')).json()['public_key'],'fake-public-key')
        self.client.post('/api/v1/push/unsubscribe',headers=auth('caregiver'),json={'endpoint':self.FCM})
        with module.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM push_subscriptions').fetchone()[0],0)
        module.PUSH=FakePush(False)
        self.assertEqual(self.client.post('/api/v1/push/subscriptions',headers=auth('caregiver'),json=good).status_code,503)
    def test_push_host_allowlist(self):
        ok=module.notify.push_host_allowed
        self.assertTrue(ok('https://updates.push.services.mozilla.com/wpush/v2/abc'))
        self.assertTrue(ok('https://web.push.apple.com/QAbc'))
        self.assertTrue(ok('https://wns2-par02p.notify.windows.com/w/?token=abc'))
        self.assertFalse(ok('https://evilpush.apple.com.example/x'));self.assertFalse(ok('https://localhost/x'))
    @unittest.skipUnless(module.notify.PUSH_AVAILABLE,'chưa cài pywebpush')
    def test_vapid_key_generated_once(self):
        folder=Path(temporary.name)/'vapid';folder.mkdir()
        first=module.notify.Push(folder,'mailto:a@example.com');second=module.notify.Push(folder,'mailto:a@example.com')
        self.assertTrue(first.enabled);self.assertEqual(first.public_key,second.public_key);self.assertEqual(len(first.public_key),87)
    def test_duo_mode_routes(self):
        module.MODE='duo';module.CAMERA='chest';module.CONTROLLER='test';module.FIND_TARGET='test';module.EVENT_SOURCES=('test',)
        self.assertEqual(self.event().status_code,200)
        self.assertEqual(self.commands('chest')[0]['reason'],'sos');self.assertEqual(self.commands('phone'),[])
        self.assertEqual(self.upload(role='chest').status_code,200)
        self.assertEqual(self.event(eid='chest-sos-0001',role='chest').status_code,403)
        self.assertEqual(self.event(eid='cane-sos-00001',role='cane').status_code,403)
        self.client.post('/api/v1/find-cane',headers=auth('caregiver'));self.assertEqual(self.commands('test')[0]['kind'],'find')
        self.assertEqual(self.client.post('/api/v1/find-cane',headers=auth('chest')).status_code,403)
        self.state(True)  # ESP32 (test) giữ nút riêng tư; ESP32-CAM chỉ chụp
        with module.db() as c:c.execute('UPDATE settings SET last_periodic=0')
        self.assertEqual(self.commands('chest')[0]['reason'],'periodic')
    def test_sos_context_location_and_distance(self):
        now=time.time()
        self.client.post('/api/v1/state',headers=auth('test'),json={'periodic_enabled':True,'sensor_valid':True,'distance_cm':85})
        self.client.post('/api/v1/location',headers=auth('phone'),json={'latitude':10.5,'longitude':106.7,'accuracy':15,'captured_at':now-5})
        self.client.post('/api/v1/events',headers=auth('test'),json={'event_id':'sos-synced-01','kind':'sos','occurred_at':now-1,'clock_synced':True})
        self.event(eid='sos-unsynced-1')
        events={e['id']:e for e in self.client.get('/api/v1/dashboard',headers=auth('caregiver')).json()['events']}
        self.assertEqual(events['sos-synced-01']['context']['location']['latitude'],10.5)
        self.assertEqual(events['sos-synced-01']['context']['distance_cm'],85)
        self.assertIsNone(events['sos-unsynced-1']['context']['location'])  # không biết giờ nhấn nút -> không gắn vị trí
        self.assertEqual(events['sos-synced-01']['notifications'][0]['stage'],'sos')
    def test_old_sos_not_tagged_with_current_location(self):
        now=time.time()
        self.client.post('/api/v1/location',headers=auth('phone'),json={'latitude':10,'longitude':106,'accuracy':15,'captured_at':now-1})
        self.client.post('/api/v1/events',headers=auth('test'),json={'event_id':'sos-late-0001','kind':'sos','occurred_at':now-600,'clock_synced':True})
        event=self.client.get('/api/v1/dashboard',headers=auth('caregiver')).json()['events'][0]
        self.assertIsNone(event['context']['location'])
    def test_message_text_includes_context(self):
        event={'id':'sos-x','source':'test','clock_synced':0,'occurred_at':None,'received_at':time.time(),
               'context':'{"location":{"latitude":10.1,"longitude":106.2,"accuracy":12,"captured_at":1},"distance_cm":42.4}'}
        text=module.notify.event_text(event)
        self.assertIn('google.com/maps?q=10.1,106.2',text);self.assertIn('42 cm',text);self.assertIn('chưa đồng bộ giờ',text)
    def test_manual_capture_respects_privacy(self):
        self.assertEqual(self.client.post('/api/v1/capture',headers=auth('caregiver')).status_code,409)  # chưa có thiết bị
        self.state(False);self.assertEqual(self.client.post('/api/v1/capture',headers=auth('caregiver')).status_code,409)
        self.state(True)
        with module.db() as c:c.execute('UPDATE settings SET last_periodic=?',(time.time(),))
        first=self.client.post('/api/v1/capture',headers=auth('caregiver')).json()
        second=self.client.post('/api/v1/capture',headers=auth('caregiver')).json()
        self.assertFalse(first['duplicate']);self.assertTrue(second['duplicate']);self.assertEqual(first['id'],second['id'])
        cmd=self.commands()[0];self.assertEqual(cmd['reason'],'manual')
        self.assertEqual(self.client.post('/api/v1/capture',headers=auth('phone')).status_code,403)
        self.state(False);self.assertEqual(self.upload(cmd['event_id']).status_code,409)
        self.state(True);self.assertEqual(self.upload(cmd['event_id']).status_code,200)
    def test_remote_role_only_finds_cane(self):
        r=self.client.post('/api/v1/find-cane',headers=auth('remote'));self.assertEqual(r.status_code,200)
        self.assertEqual(self.commands('test')[0]['kind'],'find')
        self.assertEqual(self.client.get('/api/v1/dashboard',headers=auth('remote')).status_code,403)
        self.assertEqual(self.event(eid='remote-sos-01',role='remote').status_code,403)
    def test_wearer_road_alert_opt_in_and_freshness(self):
        self.event()
        with module.db() as c:c.execute("UPDATE events SET image_status='ready',image_received_at=?,captured_at=?,ai=?",(time.time(),time.time()-2,'{"status":"ready","risk":"possible_road"}'))
        get=lambda role:self.client.get('/api/v1/commands',headers=auth(role)).json()['road_alert_ms']
        self.assertEqual(get('test'),0)  # mặc định tắt
        module.WEARER_AI_ALERT=True
        self.assertTrue(15000<get('test')<=20000);self.assertEqual(get('phone'),0)
        with module.db() as c:c.execute('UPDATE events SET captured_at=?',(time.time()-30,))
        self.assertEqual(get('test'),0)
        with module.db() as c:c.execute("UPDATE events SET captured_at=?,ai=?",(time.time(),'{"status":"ready","risk":"unknown"}'))
        self.assertEqual(get('test'),0)
    def test_upload_completes_command_without_ack(self):
        self.event();self.commands();self.assertEqual(self.upload().status_code,200)
        with module.db() as c:c.execute('UPDATE commands SET lease_until=0')
        self.assertEqual(self.commands(),[])  # không giao lại lệnh đã có ảnh
        self.state(True)
        with module.db() as c:c.execute('UPDATE settings SET last_periodic=?',(time.time(),))
        self.assertFalse(self.client.post('/api/v1/capture',headers=auth('caregiver')).json()['duplicate'])
    def test_missing_image_file_returns_404(self):
        self.event();self.commands();self.upload()
        with module.db() as c:name=c.execute('SELECT image_path FROM events').fetchone()[0]
        (module.IMAGES/name).unlink()
        self.assertEqual(self.client.get('/api/v1/events/sos-test-001/image',headers=auth('caregiver')).status_code,404)
    def test_migration_adds_context_column(self):
        import sqlite3
        old=Path(temporary.name)/'old.sqlite3'
        con=sqlite3.connect(old);con.execute('CREATE TABLE events(id TEXT PRIMARY KEY, source TEXT, kind TEXT, received_at REAL, occurred_at REAL, clock_synced INTEGER, details TEXT, image_path TEXT, captured_at REAL, image_received_at REAL, image_status TEXT, ai TEXT, acknowledged_at REAL)');con.commit();con.close()
        saved=module.DB;module.DB=old
        try:
            module.init_db()
            with module.db() as c:cols={r['name'] for r in c.execute('PRAGMA table_info(events)')}
        finally:module.DB=saved
        self.assertIn('context',cols)

class AITest(unittest.TestCase):
    def setUp(self):
        self.saved={k:os.environ.get(k) for k in ('AI_PROVIDER','AI_MODEL_DIR')}
        self.path=Path(temporary.name)/'ai.jpg';Image.new('RGB',(64,48),(120,140,130)).save(self.path,'JPEG')
    def tearDown(self):
        for k,v in self.saved.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v
    def gemini(self,status=200,payload=None,exc=None):
        from server.gemini import GeminiAnalyzer
        class Response:
            def __init__(s):s.status_code=status
            def json(s):return payload
        def post(*a,**k):
            if exc:raise exc
            return Response()
        return GeminiAnalyzer('k'*30,'gemini-test-model',post=post)
    def reply(self,result):
        import json
        return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(result)}]}}]}
    def test_provider_selection(self):
        from server import ai_adapter
        os.environ.pop('AI_PROVIDER',None);os.environ['AI_MODEL_DIR']='';self.assertEqual(ai_adapter.provider(),'none')
        os.environ['AI_MODEL_DIR']='somewhere';self.assertEqual(ai_adapter.provider(),'segformer')
        os.environ['AI_PROVIDER']='bogus'
        with self.assertRaises(RuntimeError):ai_adapter.provider()
    def test_segformer_without_folder_is_not_configured(self):
        from server import ai_adapter
        os.environ['AI_PROVIDER']='segformer';os.environ['AI_MODEL_DIR']=''
        self.assertEqual(ai_adapter.analyze(self.path)['status'],'not_configured')
    @unittest.skipUnless(__import__('importlib').util.find_spec('torch'),'chưa cài torch')
    def test_real_segformer_model(self):
        from server import ai_adapter
        os.environ['AI_PROVIDER']='segformer';os.environ['AI_MODEL_DIR']='ai/model-baseline'
        cwd=os.getcwd();os.chdir(temporary.name)  # đường dẫn tương đối phải tính từ gốc dự án
        try:result=ai_adapter.analyze(self.path)
        finally:os.chdir(cwd)
        self.assertEqual((result['status'],result['provider']),('ready','segformer'))
        self.assertIn(result['risk'],('unknown','possible_road','possible_water'));self.assertIsInstance(result['regions'],list)
        os.environ['AI_MODEL_DIR']='khong-co-thu-muc'
        self.assertEqual(ai_adapter.analyze(self.path)['status'],'not_configured')
    def test_gemini_valid_road(self):
        result=self.gemini(payload=self.reply({'road_status':'possible_road','water_status':'unknown','image_quality':'clear','scene_description':'Một con đường.','observed_objects':['xe máy']})).analyze(self.path)
        self.assertEqual((result['status'],result['risk']),('ready','possible_road'));self.assertEqual(result['observed_objects'],['xe máy'])
    def test_gemini_blurry_never_warns(self):
        result=self.gemini(payload=self.reply({'road_status':'possible_road','water_status':'possible_water','image_quality':'blurry','scene_description':'Nhòe.','observed_objects':[]})).analyze(self.path)
        self.assertEqual(result['risk'],'unknown')
    def test_gemini_rejects_bad_schema_and_text(self):
        self.assertEqual(self.gemini(payload=self.reply({'road_status':'yes'})).analyze(self.path)['status'],'error')
        bad={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'not json'}]}}]}
        self.assertEqual(self.gemini(payload=bad).analyze(self.path)['status'],'error')
        self.assertEqual(self.gemini(payload={'candidates':[]}).analyze(self.path)['status'],'error')
    def test_gemini_quota_backoff_and_network_errors(self):
        import httpx
        analyzer=self.gemini(status=429,payload={})
        self.assertEqual(analyzer.analyze(self.path)['status'],'error');self.assertGreater(analyzer.retry_after,0)
        self.assertIn('tạm dừng',analyzer.analyze(self.path)['summary'])
        self.assertEqual(self.gemini(exc=httpx.ConnectError('x')).analyze(self.path)['status'],'error')
        self.assertEqual(self.gemini(exc=httpx.ReadTimeout('x')).analyze(self.path)['status'],'error')
    def test_gemini_without_key_and_dark_image(self):
        from server.gemini import GeminiAnalyzer
        self.assertEqual(GeminiAnalyzer('','').analyze(self.path)['status'],'not_configured')
        dark=Path(temporary.name)/'dark.jpg';Image.new('RGB',(32,32),(2,2,2)).save(dark,'JPEG')
        called=[]
        result=GeminiAnalyzer('k'*30,'',post=lambda *a,**k:called.append(1)).analyze(dark)
        self.assertEqual((result['status'],result['risk'],called),('ready','unknown',[]))

if __name__=='__main__': unittest.main(verbosity=2)
