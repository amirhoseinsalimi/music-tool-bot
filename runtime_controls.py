"""Optional core-owned controls. Standalone bots keep all core tools enabled."""
import json
import os
import re
import sqlite3
import time
from contextlib import closing
from functools import wraps
from pathlib import Path

TOOLS = {
    'tag_editor': ('Tag editor', 'Edit artist, title, album and cover.'),
    'bitrate_changer': ('Bitrate changer', 'Convert audio bitrate.'),
    'cutter': ('Audio cutter', 'Trim the portion you need.'),
    'voice_converter': ('Voice converter', 'Convert audio to Telegram voice.'),
    'recognition': ('Music recognition', 'Identify audio and suggest metadata.'),
    'separation': ('Vocal separation', 'Separate vocals and instrumental audio.'),
    'artwork': ('Cover artwork', 'Generate artwork from a description.'),
}

class ControlError(Exception):
    def __init__(self, code, status=400):
        super().__init__(code)
        self.code, self.status = code, status

class ControlsStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS configuration (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, settings TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS control_audit (operation TEXT PRIMARY KEY, actor TEXT NOT NULL, feature TEXT NOT NULL, enabled INTEGER NOT NULL, previous INTEGER NOT NULL, reason TEXT NOT NULL, revision INTEGER NOT NULL, expected_revision INTEGER NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS bot_observation (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, checked REAL NOT NULL);
                CREATE TRIGGER IF NOT EXISTS controls_no_update BEFORE UPDATE ON control_audit BEGIN SELECT RAISE(ABORT,'Audit is append-only'); END;
                CREATE TRIGGER IF NOT EXISTS controls_no_delete BEFORE DELETE ON control_audit BEGIN SELECT RAISE(ABORT,'Audit is append-only'); END;
            ''')
            db.execute('INSERT OR IGNORE INTO configuration VALUES (1,0,?)', (json.dumps({key:True for key in TOOLS}),))
            db.execute('BEGIN IMMEDIATE')
            raw=db.execute('SELECT settings FROM configuration WHERE id=1').fetchone()[0]
            settings=json.loads(raw)
            for key in TOOLS:
                settings.setdefault(key,True)
            db.execute('UPDATE configuration SET settings=? WHERE id=1',(json.dumps(settings),))
            db.commit()

    def connect(self):
        db=sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory=sqlite3.Row
        return db

    def read(self):
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            row=db.execute('SELECT * FROM configuration WHERE id=1').fetchone()
            settings=json.loads(row['settings'])
            seen=db.execute('SELECT * FROM bot_observation WHERE id=1').fetchone()
            audit=[dict(r) for r in db.execute('SELECT * FROM control_audit ORDER BY revision DESC LIMIT 20')]
            return dict(revision=row['revision'],features=[dict(id=k,name=TOOLS[k][0],description=TOOLS[k][1],enabled=settings[k]) for k in TOOLS if k not in {'recognition','separation','artwork'} or os.getenv('BOT_PREMIUM_CONTROLS')=='true'],
                        botRevision=seen['revision'] if seen else None,botCheckedAt=seen['checked'] if seen else None,audit=audit)

    def audit(self, page='1'):
        if not isinstance(page, str) or not re.fullmatch(r'[0-9]{1,6}', page) or not 1 <= int(page) <= 100000:
            raise ControlError('invalid_request')
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            total=db.execute('SELECT COUNT(*) FROM control_audit').fetchone()[0]
            page=min(int(page),max(1,(total+9)//10))
            items=[dict(r) for r in db.execute('SELECT * FROM control_audit ORDER BY revision DESC LIMIT 10 OFFSET ?',((page-1)*10,))]
        return dict(items=items,total=total,page=page,pageSize=10)

    def change(self, actor, data):
        if not isinstance(data,dict) or set(data)!={'feature','enabled','reason','operationId','expectedRevision'}:
            raise ControlError('invalid_control')
        feature,enabled,reason,operation,revision=(data[k] for k in ('feature','enabled','reason','operationId','expectedRevision'))
        if (not isinstance(feature,str) or feature not in TOOLS or type(enabled) is not bool
                or not isinstance(reason,str) or not 1<=len(reason.strip())<=500
                or not isinstance(operation,str) or not re.fullmatch('[a-zA-Z0-9_-]{16,128}',operation)
                or type(revision) is not int or not 0<=revision<=2**53-1):
            raise ControlError('invalid_control')
        reason=reason.strip()
        with closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT * FROM control_audit WHERE operation=?',(operation,)).fetchone()
            if prior:
                if (prior['actor'],prior['feature'],bool(prior['enabled']),prior['reason'],prior['expected_revision'])!=(actor,feature,enabled,reason,revision):
                    raise ControlError('operation_conflict',409)
                db.rollback()
                return dict(prior),False
            current=db.execute('SELECT * FROM configuration WHERE id=1').fetchone()
            if current['revision']!=revision:
                raise ControlError('configuration_conflict',409)
            settings=json.loads(current['settings'])
            previous=settings[feature]
            if previous==enabled:
                raise ControlError('no_change',409)
            settings[feature]=enabled
            db.execute('UPDATE configuration SET revision=?,settings=? WHERE id=1',(revision+1,json.dumps(settings)))
            db.execute('INSERT INTO control_audit VALUES (?,?,?,?,?,?,?,?,?)',(operation,actor,feature,int(enabled),int(previous),reason,revision+1,revision,time.time()))
            row=dict(db.execute('SELECT * FROM control_audit WHERE operation=?',(operation,)).fetchone())
            db.commit()
            return row,True

def bot_settings():
    path=os.getenv('BOT_CONTROL_DB','')
    if not path:
        return {key:True for key in TOOLS}
    # A configured but unavailable control store fails closed for these tools.
    with closing(sqlite3.connect(path,timeout=2,isolation_level=None)) as db:
        db.execute('BEGIN IMMEDIATE')
        revision,raw=db.execute('SELECT revision,settings FROM configuration WHERE id=1').fetchone()
        settings=json.loads(raw)
        if not set(settings)<=set(TOOLS) or not {'tag_editor','bitrate_changer','cutter','voice_converter'}<=set(settings) or any(type(v) is not bool for v in settings.values()):
            raise ValueError('Invalid runtime controls')
        db.execute('INSERT INTO bot_observation VALUES (1,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,checked=excluded.checked',(revision,time.time()))
        db.commit()
        return settings

def disabled_message(language="en"):
    from config.pyi18n import i18n
    if language not in {"en", "fa", "ru", "es", "fr", "ar", "hi", "id"}:
        language = "en"
    return i18n.gettext(language, "featureDisabledMessage")


def feature_gate(feature):
    if feature not in TOOLS:
        raise ValueError('Unknown core tool')
    def decorate(function):
        @wraps(function)
        async def handler(update,context,*args,**kwargs):
            import asyncio
            try:
                enabled=(await asyncio.to_thread(bot_settings))[feature]
            except (OSError,sqlite3.Error,ValueError,TypeError):
                enabled=False
            if not enabled:
                if update.effective_message:
                    data = getattr(context, 'user_data', None) or {}
                    await update.effective_message.reply_text(disabled_message(data.get('language', 'en')), parse_mode=None)
                return None
            return await function(update,context,*args,**kwargs)
        handler.runtime_control_feature = feature
        return handler
    return decorate
