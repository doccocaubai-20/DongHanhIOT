"""API một hộ gia đình, SQLite, ảnh JPEG riêng tư, lệnh có lease và thời hạn."""
import asyncio
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from io import BytesIO
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
import uuid

import hashlib
import urllib.request
from fastapi import FastAPI, Depends, Header, HTTPException, Request, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, field_validator
from server.ai_adapter import analyze, provider as ai_provider

ROOT = Path(__file__).resolve().parents[1]
for raw in (ROOT / '.env').read_text(encoding='utf-8').splitlines() if (ROOT / '.env').exists() else []:
    if raw.strip() and not raw.lstrip().startswith('#') and '=' in raw:
        k, v = raw.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
TOKENS = {r: os.getenv(r.upper() + '_TOKEN', '') for r in ('caregiver', 'phone', 'test', 'chest', 'cane')}
if any(len(t) < 24 or t == 'CHANGE_ME' for t in TOKENS.values()) or len(set(TOKENS.values())) != 5:
    raise RuntimeError('Chạy python scripts/setup.py trước; cần 5 token khác nhau, ít nhất 24 ký tự.')
# Nút tìm gậy cầm tay (ESP32-C3, từ smart_cane) là tùy chọn: để trống thì role remote bị tắt.
REMOTE_TOKEN = os.getenv('REMOTE_TOKEN', '').strip()
if REMOTE_TOKEN and REMOTE_TOKEN != 'CHANGE_ME':
    if len(REMOTE_TOKEN) < 24 or REMOTE_TOKEN in TOKENS.values():
        raise RuntimeError('REMOTE_TOKEN cần ít nhất 24 ký tự và khác 5 token còn lại.')
    TOKENS['remote'] = REMOTE_TOKEN
# test : 1 ESP32 (cảm biến, nút, còi) + camera điện thoại
# duo  : 1 ESP32 (cảm biến, nút, còi) + 1 ESP32-CAM chỉ chụp ảnh (sketch firmware/camera)
# final: ESP32-CAM ở ngực (cảm biến + camera) + ESP32 ở gậy
MODE = os.getenv('PROJECT_MODE', 'test')
if MODE not in ('test', 'duo', 'final'):
    raise RuntimeError('PROJECT_MODE phải là test, duo hoặc final')
DATA = Path(os.getenv('DATA_DIR', str(ROOT / 'data'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
IMAGES = DATA / 'images'
IMAGES.mkdir(exist_ok=True)
DB = DATA / 'donghanh.sqlite3'
RETENTION = max(1, int(os.getenv('RETENTION_DAYS', '7'))) * 86400
CAMERA = 'phone' if MODE == 'test' else 'chest'
CONTROLLER = 'chest' if MODE == 'final' else 'test'
FIND_TARGET = 'cane' if MODE == 'final' else 'test'
# Role được gửi sự kiện (SOS/rơi/riêng tư) trong từng chế độ; phone luôn được gửi SOS.
EVENT_SOURCES = {'test': ('test',), 'duo': ('test',), 'final': ('chest', 'cane')}[MODE]
# Phản hồi AI cho người đeo (luồng road_ms của smart_cane). Mặc định tắt: AI chỉ hiển thị cho người nhà.
WEARER_AI_ALERT = os.getenv('WEARER_AI_ALERT', '0') == '1'
WEARER_ALERT_S = 20
WEARER_ALERT_RISKS = ('possible_road', 'possible_water')
lock = threading.RLock()
Image.MAX_IMAGE_PIXELS = 8_000_000
from server import notify  # noqa: E402
PUSH = notify.Push(DATA, os.getenv('VAPID_SUBJECT', 'mailto:admin@example.com').strip())
PUSH_MAX_ATTEMPTS = 8

@contextmanager
def db():
    con = sqlite3.connect(DB, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with con:
            yield con
    finally:
        con.close()

def init_db():
    with db() as c:
        c.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY, last_seen REAL, state TEXT);
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, source TEXT, kind TEXT, received_at REAL,
          occurred_at REAL, clock_synced INTEGER, details TEXT, image_path TEXT, captured_at REAL,
          image_received_at REAL, image_status TEXT, ai TEXT, acknowledged_at REAL);
        CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY, target TEXT, kind TEXT, event_id TEXT,
          created_at REAL, expires_at REAL, lease_until REAL DEFAULT 0, status TEXT DEFAULT 'pending', result TEXT);
        CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1), periodic INTEGER, interval_s INTEGER, last_periodic REAL);
        INSERT OR IGNORE INTO settings VALUES(1, 1, 60, 0);
        CREATE TABLE IF NOT EXISTS location(id INTEGER PRIMARY KEY CHECK(id=1), latitude REAL, longitude REAL,
          accuracy REAL, captured_at REAL, received_at REAL);
        CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, event_id TEXT NOT NULL, stage TEXT NOT NULL,
          level TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, created_at REAL NOT NULL, read_at REAL,
          push_state TEXT NOT NULL, push_attempts INTEGER NOT NULL DEFAULT 0, next_try REAL NOT NULL DEFAULT 0, push_error TEXT);
        CREATE TABLE IF NOT EXISTS push_subscriptions(endpoint TEXT PRIMARY KEY, p256dh TEXT NOT NULL, auth TEXT NOT NULL,
          created_at REAL NOT NULL, last_ok REAL);
        DROP TABLE IF EXISTS outbox;
        ''')
        # Nâng cấp CSDL cũ của dong-hanh-iot: thêm cột ngữ cảnh SOS nếu chưa có.
        if 'context' not in {r['name'] for r in c.execute('PRAGMA table_info(events)')}:
            c.execute('ALTER TABLE events ADD COLUMN context TEXT')

init_db()

def authenticate(authorization: str = Header(default='')):
    if not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Cần Bearer token')
    token = authorization[7:]
    for role, expected in TOKENS.items():
        if secrets.compare_digest(token, expected):
            return role
    raise HTTPException(401, 'Khóa không hợp lệ')

def only(*roles):
    def dependency(role=Depends(authenticate)):
        if role not in roles:
            raise HTTPException(403, 'Không có quyền')
        return role
    return dependency

def clock_value(value):
    if value is not None and (not math.isfinite(value) or value < 0 or value > time.time() + 300):
        raise ValueError('Thời gian không hợp lệ hoặc ở tương lai')
    return value

class State(BaseModel):
    model_config = ConfigDict(extra='forbid')
    distance_cm: float | None = Field(default=None, ge=2, le=400)
    sensor_valid: bool = False
    periodic_enabled: bool = True
    drop_alarm: bool = False
    sos_alarm: bool = False
    simulated: bool = False
    camera_ready: bool = False
    imu_ready: bool = False
    queue_dropped: int = Field(default=0, ge=0)
    uptime_s: int = Field(default=0, ge=0)
    @field_validator('distance_cm')
    @classmethod
    def finite(cls, v):
        if v is not None and not math.isfinite(v):
            raise ValueError('Khoảng cách không hữu hạn')
        return v

class Event(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event_id: str = Field(min_length=8, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    kind: str = Field(pattern=r'^(sos|drop|privacy|test)$')
    occurred_at: float | None = None
    clock_synced: bool = False
    message: str = Field(default='', max_length=240)
    @field_validator('occurred_at')
    @classmethod
    def valid_time(cls, v): return clock_value(v)

class Settings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    periodic_enabled: bool
    interval_s: int = Field(ge=15, le=3600)

class Position(BaseModel):
    model_config = ConfigDict(extra='forbid')
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float = Field(ge=0, le=100000)
    captured_at: float
    @field_validator('latitude', 'longitude', 'accuracy', 'captured_at')
    @classmethod
    def finite(cls, v):
        if not math.isfinite(v): raise ValueError('Giá trị phải hữu hạn')
        return v
    @field_validator('captured_at')
    @classmethod
    def time(cls, v): return clock_value(v)

class Ack(BaseModel):
    result: str = Field(default='done', pattern=r'^(done|failed|privacy_off|camera_unavailable)$')

def add_command(c, target, kind, event_id=None, ttl=90):
    cid = str(uuid.uuid4())
    now = time.time()
    c.execute('INSERT INTO commands(id,target,kind,event_id,created_at,expires_at) VALUES(?,?,?,?,?,?)', (cid,target,kind,event_id,now,now+ttl))
    return cid

def sos_context(c, now, occurred, synced):
    """Ảnh chụp nhanh vị trí + khoảng cách lúc nhận SOS (từ smart_cane).
    Chỉ gắn vị trí khi biết giờ sự kiện và bản tin GPS gần thời điểm đó, để SOS gửi muộn
    không bị gắn nhầm vị trí hiện tại."""
    context = {'location': None, 'distance_cm': None}
    pos = c.execute('SELECT * FROM location WHERE id=1').fetchone()
    if pos and synced and occurred is not None and now - occurred <= 120 and pos['accuracy'] <= 100 \
            and occurred - 60 <= pos['captured_at'] <= occurred + 5:
        context['location'] = {k: pos[k] for k in ('latitude', 'longitude', 'accuracy', 'captured_at')}
    device = c.execute('SELECT * FROM devices WHERE id=?', (CONTROLLER,)).fetchone()
    if device and now - device['last_seen'] < 10:
        state = json.loads(device['state'])
        if state.get('sensor_valid'): context['distance_cm'] = state.get('distance_cm')
    return context

def add_message(c, eid, stage):
    """Tạo tin nhắn cho người nhà (hộp tin web) và xếp hàng thông báo đẩy. Mỗi (sự kiện, stage) một tin."""
    event = c.execute('SELECT * FROM events WHERE id=?', (eid,)).fetchone()
    if not event: return
    event = dict(event)
    level, title, body = notify.compose(event, stage, json.loads(event['ai']) if event['ai'] else None)
    c.execute('INSERT OR IGNORE INTO messages(id,event_id,stage,level,title,body,created_at,push_state) VALUES(?,?,?,?,?,?,?,?)',
              (eid+':'+stage, eid, stage, level, title, body, time.time(), 'pending' if PUSH.enabled else 'unavailable'))

def add_event(c, eid, source, kind, occurred=None, synced=False, details='', capture=False):
    now = time.time()
    context = json.dumps(sos_context(c, now, occurred, synced)) if kind == 'sos' else None
    c.execute('INSERT INTO events(id,source,kind,received_at,occurred_at,clock_synced,details,image_status,ai,context) VALUES(?,?,?,?,?,?,?,?,?,?)',
              (eid,source,kind,now,occurred,int(synced),details,'pending' if capture else 'not_requested',json.dumps({'status':'waiting' if capture else 'not_requested','risk':'unknown'}),context))
    if capture: add_command(c,CAMERA,'capture',eid,90 if kind=='sos' else 30)
    if kind in ('sos', 'drop'): add_message(c, eid, kind)

def capture_permitted(c, now):
    """Ảnh không phải SOS chỉ được chụp khi người đeo bật quyền cục bộ và người nhà bật cài đặt."""
    controller=c.execute('SELECT * FROM devices WHERE id=?',(CONTROLLER,)).fetchone()
    settings=c.execute('SELECT periodic FROM settings WHERE id=1').fetchone()
    return bool(controller and now-controller['last_seen']<20 and json.loads(controller['state']).get('periodic_enabled',False) and settings['periodic'])

def wearer_alert_ms(c, now):
    if not WEARER_AI_ALERT: return 0
    row=c.execute("SELECT ai,captured_at,image_received_at FROM events WHERE image_status='ready' ORDER BY image_received_at DESC LIMIT 1").fetchone()
    # Kết quả cũ không được kéo dài cảnh báo; chỉ ảnh mới nhất, trong WEARER_ALERT_S giây kể từ lúc chụp.
    if not row or json.loads(row['ai']).get('risk') not in WEARER_ALERT_RISKS: return 0
    taken=row['captured_at'] or row['image_received_at']
    return max(0, min(WEARER_ALERT_S*1000, int((taken + WEARER_ALERT_S - now) * 1000)))

def clean_expired(c):
    now = time.time()
    expired = c.execute("SELECT event_id FROM commands WHERE status IN ('pending','leased') AND expires_at < ?", (now,)).fetchall()
    for row in expired:
        if c.execute("UPDATE events SET image_status='missing' WHERE id=? AND image_path IS NULL", (row['event_id'],)).rowcount:
            kind = c.execute('SELECT kind FROM events WHERE id=?', (row['event_id'],)).fetchone()
            if kind and kind['kind'] == 'sos': add_message(c, row['event_id'], 'image')
    c.execute("UPDATE commands SET status='expired' WHERE status IN ('pending','leased') AND expires_at < ?", (now,))

def worker(stop):
    last_cleanup = 0
    while not stop.wait(1):
        try:
            with lock, db() as c:
                clean_expired(c)
                row = c.execute("SELECT id,image_path FROM events WHERE image_status='uploaded' ORDER BY received_at LIMIT 1").fetchone()
                if row: c.execute("UPDATE events SET image_status='analyzing' WHERE id=?", (row['id'],))
            if row:
                try: result = analyze(IMAGES / row['image_path'])
                except Exception as exc:
                    result = {'status':'error','risk':'unknown','summary':'Phân tích thất bại; xem log máy chủ.','error_type':type(exc).__name__}
                    print('AI error:', type(exc).__name__, flush=True)
                with lock, db() as c:
                    c.execute("UPDATE events SET ai=?, image_status='ready' WHERE id=?", (json.dumps(result,ensure_ascii=False),row['id']))
                    kind=c.execute('SELECT kind FROM events WHERE id=?',(row['id'],)).fetchone()
                    if kind and kind['kind']=='sos': add_message(c,row['id'],'image')
            if time.time() - last_cleanup > 3600:
                with lock, db() as c:
                    rows = c.execute('SELECT image_path FROM events WHERE received_at < ?', (time.time()-RETENTION,)).fetchall()
                    for r in rows:
                        if r['image_path']: (IMAGES / r['image_path']).unlink(missing_ok=True)
                    c.execute('DELETE FROM messages WHERE event_id IN (SELECT id FROM events WHERE received_at < ?)', (time.time()-RETENTION,))
                    c.execute('DELETE FROM events WHERE received_at < ?', (time.time()-RETENTION,))
                    c.execute('DELETE FROM commands WHERE expires_at < ?', (time.time()-86400,))
                    c.execute('DELETE FROM location WHERE received_at < ?', (time.time()-RETENTION,))
                last_cleanup = time.time()
        except Exception as exc:
            print('Worker error:', type(exc).__name__, flush=True)

def push_one(sender=None):
    """Đẩy một tin nhắn đến hạn tới mọi thiết bị đã đăng ký. Trả True nếu đã xử lý một tin."""
    sender = sender or PUSH.send
    now = time.time()
    with lock, db() as c:
        # SOS trước; tin ảnh của một SOS chỉ đẩy sau khi tin SOS đầu tiên đã xong.
        row = c.execute("SELECT * FROM messages m WHERE push_state='pending' AND next_try<=? AND (stage!='image' OR NOT EXISTS("
                        "SELECT 1 FROM messages i WHERE i.event_id=m.event_id AND i.stage='sos' AND i.push_state='pending')) "
                        "ORDER BY CASE level WHEN 'sos' THEN 0 ELSE 1 END, created_at LIMIT 1", (now,)).fetchone()
        if not row: return False
        subs = [dict(r) for r in c.execute('SELECT * FROM push_subscriptions')]
        if not subs:
            c.execute("UPDATE messages SET push_state='no_device' WHERE id=?", (row['id'],))
            return True
    payload = {'title': row['title'], 'body': row['body'][:400], 'tag': row['id'], 'level': row['level'], 'url': '/#messages'}
    delivered, gone, transient = [], [], 0
    # Gọi mạng ngoài khóa CSDL để API không bị chặn khi máy chủ push chậm.
    for sub in subs:
        code = sender({'endpoint': sub['endpoint'], 'keys': {'p256dh': sub['p256dh'], 'auth': sub['auth']}}, payload, row['level'] == 'sos')
        if 200 <= code < 300: delivered.append(sub['endpoint'])
        elif code in (404, 410): gone.append(sub['endpoint'])  # trình duyệt đã hủy đăng ký
        else: transient += 1
    with lock, db() as c:
        for endpoint in gone: c.execute('DELETE FROM push_subscriptions WHERE endpoint=?', (endpoint,))
        if delivered:
            for endpoint in delivered: c.execute('UPDATE push_subscriptions SET last_ok=? WHERE endpoint=?', (time.time(), endpoint))
            c.execute("UPDATE messages SET push_state='sent',push_error=NULL WHERE id=?", (row['id'],))
        elif not transient:
            c.execute("UPDATE messages SET push_state='no_device' WHERE id=?", (row['id'],))
        else:
            count = row['push_attempts'] + 1
            # Lỗi mạng phải còn thử lại được và không bao giờ trông như đã gửi.
            state = 'failed' if count >= PUSH_MAX_ATTEMPTS else 'pending'
            c.execute('UPDATE messages SET push_state=?,push_attempts=?,next_try=?,push_error=? WHERE id=?',
                      (state, count, time.time() + min(300, 2 ** count), 'push_unreachable', row['id']))
    return True

def push_worker(stop):
    while not stop.is_set():
        try: worked = push_one()
        except Exception as exc:
            print('Push error:', type(exc).__name__, flush=True); worked = False
        if not worked: stop.wait(1)

@asynccontextmanager
async def lifespan(app):
    with lock, db() as c:
        c.execute("UPDATE events SET image_status='uploaded' WHERE image_status='analyzing'")
    stop = threading.Event()
    # Thông báo đẩy chạy luồng riêng: mạng chậm không chặn AI hay việc dọn lệnh hết hạn.
    threads = [threading.Thread(target=fn,args=(stop,),daemon=True) for fn in (worker, push_worker)]
    for thread in threads: thread.start()
    yield
    stop.set()
    for thread in threads: thread.join(timeout=2)

app = FastAPI(title='Đồng Hành IoT', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
origins = [v.strip() for v in os.getenv('ALLOWED_ORIGINS','').split(',') if v.strip()]
if origins:
    app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST','PUT'],allow_headers=['Authorization','Content-Type','X-Captured-At'])

@app.middleware('http')
async def headers(request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    return response

@app.get('/health')
def health(): return {'ok':True}

@app.get('/api/v1/session')
def session(role=Depends(authenticate)):
    return {'role':role,'mode':MODE,'camera_source':CAMERA,'server_time':time.time()}

@app.post('/api/v1/state')
def state(body:State, role=Depends(only('test','chest','cane','phone'))):
    with lock, db() as c:
        c.execute('INSERT INTO devices VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,state=excluded.state', (role,time.time(),body.model_dump_json()))
    return {'ok':True}

@app.post('/api/v1/events')
def event(body:Event, role=Depends(only('test','chest','cane','phone'))):
    if (role=='phone' and body.kind!='sos') or (role!='phone' and role not in EVENT_SOURCES):
        raise HTTPException(403,'Nguồn không phù hợp chế độ hiện tại')
    with lock, db() as c:
        old = c.execute('SELECT source,kind FROM events WHERE id=?',(body.event_id,)).fetchone()
        if old:
            if old['source']!=role or old['kind']!=body.kind: raise HTTPException(409,'event_id đã được sử dụng')
            return {'id':body.event_id,'duplicate':True}
        add_event(c,body.event_id,role,body.kind,body.occurred_at,body.clock_synced,body.message,capture=body.kind=='sos')
    return {'id':body.event_id,'duplicate':False}

@app.get('/api/v1/commands')
def commands(role=Depends(only('phone','chest','test','cane'))):
    now=time.time()
    with lock, db() as c:
        clean_expired(c)
        settings=c.execute('SELECT * FROM settings WHERE id=1').fetchone()
        pending = c.execute("SELECT 1 FROM commands WHERE target=? AND kind='capture' AND status IN ('pending','leased') AND expires_at>?",(CAMERA,now)).fetchone()
        if role==CAMERA and not pending and now-settings['last_periodic']>=settings['interval_s'] and capture_permitted(c,now):
            eid=str(uuid.uuid4())
            add_event(c,eid,CAMERA,'periodic',capture=True)
            c.execute('UPDATE settings SET last_periodic=? WHERE id=1',(now,))
        rows=c.execute("SELECT * FROM commands WHERE target=? AND status IN ('pending','leased') AND expires_at>? AND lease_until<? ORDER BY CASE kind WHEN 'capture' THEN 1 ELSE 0 END,created_at LIMIT 4",(role,now,now)).fetchall()
        result=[]
        for r in rows:
            c.execute("UPDATE commands SET lease_until=?,status='leased' WHERE id=?",(now+12,r['id']))
            item=dict(r)
            if r['event_id']:
                e=c.execute('SELECT kind FROM events WHERE id=?',(r['event_id'],)).fetchone()
                item['reason']=e['kind'] if e else 'unknown'
            result.append({k:item[k] for k in ('id','kind','event_id','expires_at','reason') if k in item})
        alert = wearer_alert_ms(c,now) if role in ('test','chest') else 0
    return {'commands':result,'settings':{'periodic_enabled':bool(settings['periodic']),'interval_s':settings['interval_s']},'road_alert_ms':alert}

@app.post('/api/v1/commands/{cid}/ack')
def ack_command(cid:str, body:Ack, role=Depends(only('phone','chest','cane','test'))):
    with lock, db() as c:
        row=c.execute('SELECT * FROM commands WHERE id=? AND target=?',(cid,role)).fetchone()
        if not row: raise HTTPException(404,'Không có lệnh')
        if row['status']=='expired': raise HTTPException(410,'Lệnh hết hạn')
        if row['kind']=='capture' and body.result=='done':
            e=c.execute('SELECT image_path FROM events WHERE id=?',(row['event_id'],)).fetchone()
            if not e or not e['image_path']: raise HTTPException(409,'Chưa có ảnh; không xác nhận thành công')
        c.execute("UPDATE commands SET status='done',result=? WHERE id=?",(body.result,cid))
        if body.result!='done' and row['event_id']:
            c.execute("UPDATE events SET image_status=? WHERE id=? AND image_path IS NULL",(body.result,row['event_id']))
    return {'ok':True}

@app.post('/api/v1/events/{eid}/image')
async def upload(eid:str, request:Request, role=Depends(only('phone','chest'))):
    if role!=CAMERA: raise HTTPException(403,'Không phải nguồn camera hiện tại')
    if request.headers.get('content-type','').split(';')[0]!='image/jpeg': raise HTTPException(415,'Cần image/jpeg')
    data=bytearray()
    async for part in request.stream():
        data.extend(part)
        if len(data)>2_000_000: raise HTTPException(413,'Ảnh tối đa 2 MB')
    stamp=request.headers.get('x-captured-at')
    try: captured=clock_value(float(stamp)) if stamp else None
    except ValueError: raise HTTPException(422,'Thời gian chụp không hợp lệ')
    try:
        with Image.open(BytesIO(data)) as im:
            if im.format!='JPEG' or im.width*im.height>8_000_000: raise ValueError()
            im.load()
            rgb=im.convert('RGB')
            rgb.thumbnail((1280,1280))
            out=BytesIO()
            rgb.save(out,format='JPEG',quality=85)
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError):
        raise HTTPException(400,'Ảnh JPEG không hợp lệ')
    with lock, db() as c:
        row=c.execute('SELECT * FROM events WHERE id=?',(eid,)).fetchone()
        cmd=c.execute("SELECT * FROM commands WHERE event_id=? AND target=? AND kind='capture' ORDER BY created_at DESC LIMIT 1",(eid,role)).fetchone()
        if not row or not cmd: raise HTTPException(404,'Không có yêu cầu chụp')
        if row['image_path']: return {'ok':True,'duplicate':True}
        if cmd['expires_at']<time.time(): raise HTTPException(410,'Yêu cầu chụp đã hết hạn')
        if row['kind'] in ('periodic','manual') and not capture_permitted(c,time.time()):
            raise HTTPException(409,'Đã tắt ảnh định kỳ')
        name=str(uuid.uuid4())+'.jpg'
        (IMAGES/name).write_bytes(out.getvalue())
        c.execute("UPDATE events SET image_path=?,captured_at=?,image_received_at=?,image_status='uploaded',ai=? WHERE id=?",(name,captured,time.time(),json.dumps({'status':'pending','risk':'unknown'}),eid))
        # Đã có ảnh thì lệnh coi như xong, kể cả khi ACK của thiết bị bị mất: không giao lại,
        # không chặn lịch chụp/yêu cầu chụp mới đến hết TTL.
        c.execute("UPDATE commands SET status='done',result='done' WHERE id=?",(cmd['id'],))
    return {'ok':True,'duplicate':False}

@app.get('/api/v1/events/{eid}/image')
def image_file(eid:str, role=Depends(only('caregiver'))):
    with db() as c: row=c.execute('SELECT image_path FROM events WHERE id=?',(eid,)).fetchone()
    if not row or not row['image_path'] or not (IMAGES/row['image_path']).is_file(): raise HTTPException(404,'Chưa có ảnh')
    return FileResponse(IMAGES/row['image_path'],media_type='image/jpeg')

@app.get('/api/v1/dashboard')
def dashboard(role=Depends(only('caregiver'))):
    with lock, db() as c:
        clean_expired(c)
        events=[]
        for r in c.execute('SELECT * FROM events ORDER BY received_at DESC LIMIT 100'):
            item=dict(r)
            item['has_image']=bool(item.pop('image_path'))
            item['ai']=json.loads(item['ai'])
            item['context']=json.loads(item['context']) if item['context'] else None
            item['notifications']=[dict(n) for n in c.execute('SELECT stage,push_state AS state,push_attempts AS attempts,read_at FROM messages WHERE event_id=? ORDER BY created_at',(item['id'],))]
            events.append(item)
        devices=[{'id':r['id'],'last_seen':r['last_seen'],'state':json.loads(r['state'])} for r in c.execute('SELECT * FROM devices')]
        position=c.execute('SELECT * FROM location WHERE id=1').fetchone()
        settings=c.execute('SELECT * FROM settings WHERE id=1').fetchone()
        unread=c.execute('SELECT COUNT(*) FROM messages WHERE read_at IS NULL').fetchone()[0]
    return {'mode':MODE,'camera_source':CAMERA,'server_time':time.time(),'ai_provider':ai_provider(),'push_enabled':PUSH.enabled,'unread_messages':unread,'wearer_ai_alert':WEARER_AI_ALERT,'events':events,'devices':devices,'location':dict(position) if position else None,'settings':{'periodic_enabled':bool(settings['periodic']),'interval_s':settings['interval_s']}}

@app.put('/api/v1/settings')
def settings(body:Settings, role=Depends(only('caregiver'))):
    with lock, db() as c:
        c.execute('UPDATE settings SET periodic=?,interval_s=? WHERE id=1',(int(body.periodic_enabled),body.interval_s))
    return {'ok':True}

@app.post('/api/v1/events/{eid}/ack')
def seen(eid:str, role=Depends(only('caregiver'))):
    with lock, db() as c:
        changed=c.execute("UPDATE events SET acknowledged_at=COALESCE(acknowledged_at,?) WHERE id=? AND kind='sos'",(time.time(),eid)).rowcount
        if not changed: raise HTTPException(404,'Không có SOS')
    return {'ok':True}

@app.post('/api/v1/capture')
def capture_now(role=Depends(only('caregiver'))):
    """Người nhà yêu cầu chụp ngay (từ /api/capture của smart_cane); vẫn tôn trọng nút riêng tư."""
    now=time.time()
    with lock, db() as c:
        clean_expired(c)
        if not capture_permitted(c,now): raise HTTPException(409,'Người đeo đang tắt ảnh hoặc thiết bị điều khiển mất kết nối')
        row=c.execute("SELECT event_id FROM commands WHERE target=? AND kind='capture' AND status IN ('pending','leased') AND expires_at>?",(CAMERA,now)).fetchone()
        if row: return {'id':row['event_id'],'duplicate':True}
        eid='manual-'+uuid.uuid4().hex
        add_event(c,eid,'caregiver','manual',capture=True)
    return {'id':eid,'duplicate':False}

@app.post('/api/v1/find-cane')
def find_cane(role=Depends(only('caregiver','phone','chest','remote','test'))):
    with lock, db() as c:
        targets = set([FIND_TARGET, 'cane', 'test'])
        cid = None
        for target in targets:
            row=c.execute("SELECT id FROM commands WHERE target=? AND kind='find' AND expires_at>? AND status IN ('pending','leased')",(target,time.time())).fetchone()
            if not row:
                c_id = add_command(c,target,'find',ttl=20)
                if not cid: cid = c_id
            elif not cid:
                cid = row['id']
    return {'id':cid,'expires_in_s':20}

@app.post('/api/v1/stop-alarm')
def stop_alarm(role=Depends(only('caregiver','phone','chest','remote','test','cane'))):
    with lock, db() as c:
        now = time.time()
        c.execute("UPDATE commands SET status='done', result='cancelled' WHERE kind IN ('find','sos') AND status IN ('pending','leased')")
        for target in ('cane', 'test'):
            add_command(c, target, 'stop', ttl=15)
    return {'ok': True}

@app.post('/api/v1/location')
def location(body:Position, role=Depends(only('phone'))):
    with lock, db() as c:
        old=c.execute('SELECT captured_at FROM location WHERE id=1').fetchone()
        if old and body.captured_at<old['captured_at']: return {'ok':True,'ignored_older':True}
        c.execute('INSERT OR REPLACE INTO location VALUES(1,?,?,?,?,?)',(body.latitude,body.longitude,body.accuracy,body.captured_at,time.time()))
    return {'ok':True}

class Subscription(BaseModel):
    model_config = ConfigDict(extra='ignore')  # trình duyệt gửi kèm expirationTime
    endpoint: str = Field(min_length=20, max_length=1000)
    keys: dict[str, str]
    @field_validator('endpoint')
    @classmethod
    def push_service(cls, v):
        if not notify.push_host_allowed(v): raise ValueError('Endpoint không thuộc dịch vụ push của trình duyệt')
        return v
    @field_validator('keys')
    @classmethod
    def push_keys(cls, v):
        if not (20 <= len(v.get('p256dh','')) <= 200 and 8 <= len(v.get('auth','')) <= 100): raise ValueError('Khóa push không hợp lệ')
        return v

class ReadMessages(BaseModel):
    ids: list[str] | None = Field(default=None, max_length=200)

class Unsubscribe(BaseModel):
    endpoint: str = Field(min_length=20, max_length=1000)

@app.get('/api/v1/messages')
def messages(role=Depends(only('caregiver'))):
    with lock, db() as c:
        rows=[dict(r) for r in c.execute('SELECT id,event_id,stage,level,title,body,created_at,read_at,push_state FROM messages ORDER BY created_at DESC LIMIT 100')]
        unread=c.execute('SELECT COUNT(*) FROM messages WHERE read_at IS NULL').fetchone()[0]
    return {'messages':rows,'unread':unread}

@app.post('/api/v1/messages/read')
def read_messages(body:ReadMessages, role=Depends(only('caregiver'))):
    """Đánh dấu đã đọc. Không gửi ids = đọc tất cả. Đọc tin không có nghĩa đã xác nhận SOS."""
    with lock, db() as c:
        if body.ids is None: c.execute('UPDATE messages SET read_at=? WHERE read_at IS NULL',(time.time(),))
        else:
            for mid in body.ids: c.execute('UPDATE messages SET read_at=COALESCE(read_at,?) WHERE id=?',(time.time(),mid))
    return {'ok':True}

@app.get('/api/v1/push/config')
def push_config(role=Depends(only('caregiver'))):
    return {'enabled':PUSH.enabled,'public_key':PUSH.public_key}

@app.post('/api/v1/push/subscriptions')
def subscribe(body:Subscription, role=Depends(only('caregiver'))):
    if not PUSH.enabled: raise HTTPException(503,'Máy chủ chưa cài pywebpush')
    with lock, db() as c:
        if c.execute('SELECT COUNT(*) FROM push_subscriptions').fetchone()[0] >= 20 and not c.execute('SELECT 1 FROM push_subscriptions WHERE endpoint=?',(body.endpoint,)).fetchone():
            raise HTTPException(409,'Đã đủ 20 thiết bị nhận thông báo; hủy bớt trước')
        c.execute('INSERT INTO push_subscriptions(endpoint,p256dh,auth,created_at) VALUES(?,?,?,?) ON CONFLICT(endpoint) DO UPDATE SET p256dh=excluded.p256dh,auth=excluded.auth',
                  (body.endpoint,body.keys['p256dh'],body.keys['auth'],time.time()))
    return {'ok':True}

@app.post('/api/v1/push/unsubscribe')
def unsubscribe(body:Unsubscribe, role=Depends(only('caregiver'))):
    with lock, db() as c: c.execute('DELETE FROM push_subscriptions WHERE endpoint=?',(body.endpoint,))
    return {'ok':True}


# ==========================================
# DỊCH VỤ GIỌNG NÓI TIẾNG VIỆT VIFAST-TTS
# ==========================================
VIFAST_TTS_URL = os.getenv('VIFAST_TTS_URL', 'https://vifasttts.hoctuthien.com/api/tts')

@app.get('/api/v1/tts')
async def vifast_tts(text: str = Query(..., min_length=1, max_length=500), speed: float = 1.0):
    """
    Chuyển đổi văn bản thành giọng nói tiếng Việt bằng ViFastTts Services (Ngọc Huyền N0 24kHz).
    Bộ đệm lưu trữ (cache) âm thanh tại DATA/tts_cache để phản hồi tức thì.
    """
    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(400, 'Nội dung văn bản rỗng')

    cache_dir = DATA / 'tts_cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(f"{clean_text}_{speed:.2f}".encode('utf-8')).hexdigest()
    cache_file = cache_dir / f"{cache_key}.wav"

    if cache_file.exists():
        return FileResponse(cache_file, media_type='audio/wav')

    try:
        payload = json.dumps({
            'text': clean_text,
            'speed': speed,
            'alpha': 1.5,
            'dialect': 'north'
        }).encode('utf-8')

        req = urllib.request.Request(
            VIFAST_TTS_URL,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'DongHanhIoT/1.0'
            }
        )

        def fetch_audio():
            with urllib.request.urlopen(req, timeout=10) as res:
                if res.status == 200:
                    return res.read()
                return None

        audio_data = await asyncio.to_thread(fetch_audio)
        if not audio_data:
            raise HTTPException(502, 'Lỗi kết nối ViFastTts Service')

        with open(cache_file, 'wb') as f:
            f.write(audio_data)

        return Response(content=audio_data, media_type='audio/wav')
    except Exception as e:
        print(f"[ViFastTTS] Lỗi tổng hợp giọng nói: {e}", flush=True)
        raise HTTPException(502, f'Dịch vụ ViFastTts không khả dụng: {e}')

app.mount('/',StaticFiles(directory=ROOT/'web',html=True),name='web')
