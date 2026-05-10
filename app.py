"""
ErgoWork — Backend Flask Completo
Fixes: upload de vídeo corrigido, todas as rotas, Google OAuth, mobile
"""
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, send_from_directory)
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import base64, os, json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ergowork_2025_secret')

_basedir = os.path.abspath(os.path.dirname(__file__))
os.makedirs(os.path.join(_basedir, 'instance'), exist_ok=True)
_db_url = os.environ.get('DATABASE_URL',
    'sqlite:///' + os.path.join(_basedir, 'instance', 'ergowork.db'))
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(_basedir, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

ALLOWED_IMG = {'png','jpg','jpeg','gif','webp','bmp'}
ALLOWED_VID = {'mp4','mov','avi','webm','mkv','ogg','m4v','3gp','flv'}

db = SQLAlchemy(app)

# ─────────────── MODELOS ────────────────────────────────────────

ADMIN_EMAILS = {'gabrielroliveira98@gmail.com'}

class User(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    nome        = db.Column(db.String(100), nullable=False)
    email       = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash  = db.Column(db.String(200), default='')
    cargo       = db.Column(db.String(100), default='')
    foto_perfil = db.Column(db.Text, default='')
    google_id   = db.Column(db.String(200), default='')
    is_admin    = db.Column(db.Boolean, default=False)
    criado_em   = db.Column(db.DateTime, default=datetime.utcnow)
    pontos     = db.relationship('RegistroPonto', backref='usuario', lazy=True, cascade='all,delete')
    checklists = db.relationship('ChecklistErgo', backref='usuario', lazy=True, cascade='all,delete')
    midias     = db.relationship('Midia',         backref='usuario', lazy=True, cascade='all,delete')

class RegistroPonto(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data         = db.Column(db.Date, default=date.today)
    entrada      = db.Column(db.DateTime)
    almoco       = db.Column(db.DateTime)
    retorno      = db.Column(db.DateTime)
    saida        = db.Column(db.DateTime)
    foto_entrada = db.Column(db.Text, default='')
    foto_saida   = db.Column(db.Text, default='')

    @property
    def total_min(self):
        if not (self.entrada and self.saida): return 0
        t = (self.saida - self.entrada).total_seconds() / 60
        if self.almoco and self.retorno:
            t -= (self.retorno - self.almoco).total_seconds() / 60
        return max(0, int(t))

    @property
    def total_fmt(self):
        m = self.total_min
        return f"{m//60}h {m%60:02d}m"

    def to_dict(self):
        fmt = lambda dt: dt.strftime('%H:%M') if dt else None
        return dict(entrada=fmt(self.entrada), almoco=fmt(self.almoco),
                    retorno=fmt(self.retorno), saida=fmt(self.saida),
                    total=self.total_fmt)

class ChecklistErgo(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    data          = db.Column(db.DateTime, default=datetime.utcnow)
    respostas     = db.Column(db.Text, default='{}')
    pontuacao     = db.Column(db.Integer, default=0)
    classificacao = db.Column(db.String(30), default='')

class Midia(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    nome        = db.Column(db.String(200), nullable=False)
    tipo        = db.Column(db.String(10))
    filename    = db.Column(db.String(300))
    descricao   = db.Column(db.Text, default='')
    tamanho     = db.Column(db.Integer, default=0)
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)

# ─────────────── HELPERS ────────────────────────────────────────

def current_user():
    if 'user_id' not in session:
        return None
    u = User.query.get(session['user_id'])
    if not u:
        session.clear()
    return u

def login_required(f):
    from functools import wraps
    @wraps(f)
    def deco(*a, **kw):
        if not current_user():
            return redirect(url_for('login'))
        return f(*a, **kw)
    return deco

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def deco(*a, **kw):
        u = current_user()
        if not u:
            return redirect(url_for('login'))
        if not u.is_admin:
            return redirect(url_for('dashboard'))
        return f(*a, **kw)
    return deco

def ponto_hoje(uid):
    return RegistroPonto.query.filter_by(user_id=uid, data=date.today()).first()

def get_ext(filename):
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

def fmt_size(b):
    if b < 1024: return f"{b} B"
    if b < 1024**2: return f"{b/1024:.1f} KB"
    return f"{b/1024**2:.1f} MB"

# ─────────────── AUTH ────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    msg = request.args.get('msg','')
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        senha = request.form.get('senha','')
        u = User.query.filter_by(email=email).first()
        if u and u.senha_hash and check_password_hash(u.senha_hash, senha):
            session.permanent = True
            session['user_id'] = u.id
            return redirect(url_for('dashboard'))
        return render_template('login.html', erro='E-mail ou senha incorretos.', msg=msg)
    return render_template('login.html', erro='', msg=msg)

@app.route('/cadastro', methods=['GET','POST'])
def cadastro():
    if request.method == 'POST':
        nome  = request.form.get('nome','').strip()
        email = request.form.get('email','').strip().lower()
        senha = request.form.get('senha','')
        cargo = request.form.get('cargo','').strip()
        if User.query.filter_by(email=email).first():
            return render_template('cadastro.html', erro='E-mail já cadastrado.')
        if len(senha) < 4:
            return render_template('cadastro.html', erro='Senha mínima de 4 caracteres.')
        u = User(nome=nome, email=email, senha_hash=generate_password_hash(senha), cargo=cargo)
        fp = request.files.get('foto_perfil')
        if fp and fp.filename:
            u.foto_perfil = 'data:' + fp.mimetype + ';base64,' + base64.b64encode(fp.read()).decode()
        db.session.add(u); db.session.commit()
        session.permanent = True
        session['user_id'] = u.id
        return redirect(url_for('dashboard'))
    return render_template('cadastro.html', erro='')

@app.route('/login/google')
def login_google():
    client_id = os.environ.get('GOOGLE_CLIENT_ID','')
    if not client_id:
        return redirect(url_for('login') + '?msg=Configure GOOGLE_CLIENT_ID no .env — veja README')
    from urllib.parse import urlencode
    params = urlencode({'client_id':client_id,
                        'redirect_uri':url_for('google_callback',_external=True),
                        'response_type':'code','scope':'openid email profile'})
    return redirect(f'https://accounts.google.com/o/oauth2/v2/auth?{params}')

@app.route('/login/google/callback')
def google_callback():
    import urllib.request, urllib.parse
    code = request.args.get('code','')
    client_id     = os.environ.get('GOOGLE_CLIENT_ID','')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET','')
    redirect_uri  = url_for('google_callback', _external=True)
    if not code or not client_id:
        return redirect(url_for('login'))
    try:
        data = urllib.parse.urlencode({'code':code,'client_id':client_id,
            'client_secret':client_secret,'redirect_uri':redirect_uri,
            'grant_type':'authorization_code'}).encode()
        with urllib.request.urlopen(
                urllib.request.Request('https://oauth2.googleapis.com/token', data=data, method='POST')
        ) as r: tokens = json.loads(r.read())
        with urllib.request.urlopen(
                urllib.request.Request('https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization':f"Bearer {tokens['access_token']}"})
        ) as r: info = json.loads(r.read())
        email = info.get('email','').lower()
        u = User.query.filter_by(email=email).first()
        if not u:
            u = User(nome=info.get('name','Usuário'), email=email,
                     google_id=info.get('id',''), foto_perfil=info.get('picture',''),
                     is_admin=email in ADMIN_EMAILS)
            db.session.add(u)
        else:
            u.google_id = info.get('id', u.google_id)
            u.foto_perfil = info.get('picture', u.foto_perfil)
            if email in ADMIN_EMAILS:
                u.is_admin = True
        db.session.commit()
        session.permanent = True
        session['user_id'] = u.id
        return redirect(url_for('dashboard'))
    except Exception as e:
        return redirect(url_for('login') + f'?msg=Erro: {str(e)[:60]}')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─────────────── PÁGINAS ────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    u  = current_user()
    p  = ponto_hoje(u.id)
    checks = ChecklistErgo.query.filter_by(user_id=u.id).order_by(ChecklistErgo.data.desc()).limit(8).all()
    tc  = ChecklistErgo.query.filter_by(user_id=u.id).count()
    tm  = Midia.query.filter_by(user_id=u.id).count()
    avg = db.session.query(db.func.avg(ChecklistErgo.pontuacao)).filter_by(user_id=u.id).scalar() or 0
    return render_template('dashboard.html', user=u, ponto=p, checks=checks,
                           total_checks=tc, total_midias=tm, media_score=int(avg))

@app.route('/ponto')
@login_required
def ponto():
    u   = current_user()
    h   = ponto_hoje(u.id)
    his = RegistroPonto.query.filter_by(user_id=u.id).order_by(RegistroPonto.data.desc()).limit(30).all()
    return render_template('ponto.html', user=u, hoje=h, historico=his)

@app.route('/ponto/registrar', methods=['POST'])
@login_required
def registrar_ponto():
    u = current_user()
    tipo = request.form.get('tipo','')
    foto = request.form.get('foto','')
    ts_str = request.form.get('ts','')
    try:
        agora = datetime.fromisoformat(ts_str) if ts_str else datetime.now()
    except Exception:
        agora = datetime.now()
    hoje_data = date.today()
    h = RegistroPonto.query.filter_by(user_id=u.id, data=hoje_data).first()
    if not h:
        h = RegistroPonto(user_id=u.id, data=hoje_data)
        db.session.add(h)
    if   tipo=='entrada' and not h.entrada: h.entrada=agora; h.foto_entrada=foto
    elif tipo=='almoco'  and h.entrada and not h.almoco:  h.almoco=agora
    elif tipo=='retorno' and h.almoco  and not h.retorno: h.retorno=agora
    elif tipo=='saida'   and h.entrada and not h.saida:   h.saida=agora; h.foto_saida=foto
    else: return jsonify({'ok':False,'erro':'Registro não permitido agora.'})
    db.session.commit()
    return jsonify({'ok':True,'hora':agora.strftime('%H:%M:%S'),'total':h.total_fmt})

@app.route('/checklist')
@login_required
def checklist():
    u   = current_user()
    his = ChecklistErgo.query.filter_by(user_id=u.id).order_by(ChecklistErgo.data.desc()).limit(10).all()
    return render_template('checklist.html', user=u, historico=his)

@app.route('/checklist/salvar', methods=['POST'])
@login_required
def salvar_checklist():
    u   = current_user()
    d   = request.get_json()
    pts = d.get('pontuacao', 0)
    cls = 'Excelente' if pts>=80 else ('Bom' if pts>=60 else ('Regular' if pts>=40 else 'Precisa melhorar'))
    c = ChecklistErgo(user_id=u.id, respostas=json.dumps(d.get('respostas',{})),
                      pontuacao=pts, classificacao=cls)
    db.session.add(c); db.session.commit()
    return jsonify({'ok':True,'classificacao':cls,'pontuacao':pts})

@app.route('/exercicios')
@login_required
def exercicios():
    return render_template('exercicios.html', user=current_user())

@app.route('/estudos')
@login_required
def estudos():
    return render_template('estudos.html', user=current_user())

@app.route('/midias')
@login_required
def midias():
    u  = current_user()
    fs = Midia.query.filter_by(user_id=u.id, tipo='foto').order_by(Midia.data_upload.desc()).all()
    vs = Midia.query.filter_by(user_id=u.id, tipo='video').order_by(Midia.data_upload.desc()).all()
    return render_template('midias.html', user=u, fotos=fs, videos=vs)

@app.route('/midias/upload', methods=['POST'])
@login_required
def upload_midia():
    u = current_user()
    f = request.files.get('arquivo')
    if not f or not f.filename:
        return jsonify({'ok':False,'erro':'Nenhum arquivo recebido.'})
    e  = get_ext(f.filename)
    tp = 'foto' if e in ALLOWED_IMG else ('video' if e in ALLOWED_VID else None)
    if not tp:
        return jsonify({'ok':False,'erro':f'Formato .{e} não suportado. Aceitos: mp4 mov webm avi mkv (vídeo) | jpg png gif webp (foto)'})
    sub   = 'fotos' if tp == 'foto' else 'videos'
    pasta = os.path.join(app.config['UPLOAD_FOLDER'], sub)
    os.makedirs(pasta, exist_ok=True)
    ts    = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    fname = f"u{u.id}_{ts}_{secure_filename(f.filename)}"
    path  = os.path.join(pasta, fname)
    f.save(path)
    tamanho = os.path.getsize(path)
    nome  = request.form.get('nome','').strip() or f.filename
    descr = request.form.get('descricao','').strip()
    m = Midia(user_id=u.id, nome=nome, tipo=tp,
              filename=f"{sub}/{fname}", descricao=descr, tamanho=tamanho)
    db.session.add(m); db.session.commit()
    return jsonify({'ok':True,'id':m.id,'nome':m.nome,'tipo':tp,
                    'url':f'/uploads/{m.filename}','tamanho':fmt_size(tamanho)})

@app.route('/midias/excluir/<int:mid>', methods=['POST'])
@login_required
def excluir_midia(mid):
    u = current_user()
    m = Midia.query.filter_by(id=mid, user_id=u.id).first_or_404()
    try: os.remove(os.path.join(app.config['UPLOAD_FOLDER'], m.filename))
    except: pass
    db.session.delete(m); db.session.commit()
    return jsonify({'ok':True})

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve com Range support para streaming de vídeo em mobile."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, conditional=True)

@app.route('/perfil', methods=['GET','POST'])
@login_required
def perfil():
    u = current_user()
    msg = ''
    if request.method == 'POST':
        u.nome  = request.form.get('nome', u.nome).strip()
        u.cargo = request.form.get('cargo', u.cargo).strip()
        nova    = request.form.get('nova_senha','').strip()
        if nova:
            if len(nova) < 4: msg = 'erro:Senha mínima de 4 caracteres.'
            else: u.senha_hash = generate_password_hash(nova)
        if not msg:
            fp = request.files.get('foto_perfil')
            if fp and fp.filename:
                u.foto_perfil = 'data:'+fp.mimetype+';base64,'+base64.b64encode(fp.read()).decode()
            db.session.commit()
            msg = 'ok:Perfil atualizado!'
    return render_template('perfil.html', user=u, msg=msg)

@app.route('/admin')
@admin_required
def admin_panel():
    u     = current_user()
    users = User.query.order_by(User.criado_em.desc()).all()
    stats = {
        'usuarios':   User.query.count(),
        'pontos':     RegistroPonto.query.count(),
        'checklists': ChecklistErgo.query.count(),
        'midias':     Midia.query.count(),
    }
    dados = []
    for usr in users:
        pontos  = RegistroPonto.query.filter_by(user_id=usr.id).order_by(RegistroPonto.data.desc()).limit(30).all()
        checks  = ChecklistErgo.query.filter_by(user_id=usr.id).order_by(ChecklistErgo.data.desc()).limit(10).all()
        midias  = Midia.query.filter_by(user_id=usr.id).order_by(Midia.data_upload.desc()).all()
        dados.append({'user': usr, 'pontos': pontos, 'checks': checks, 'midias': midias})
    return render_template('admin.html', user=u, stats=stats, dados=dados, hoje=date.today().isoformat())

@app.route('/admin/pontos_dia')
@admin_required
def admin_pontos_dia():
    data_str = request.args.get('data', date.today().isoformat())
    try:
        d = date.fromisoformat(data_str)
    except ValueError:
        d = date.today()
    registros = RegistroPonto.query.filter_by(data=d).order_by(RegistroPonto.entrada).all()
    user_ids = [r.user_id for r in registros]
    users_map = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}
    resultado = []
    for r in registros:
        u = users_map.get(r.user_id)
        if not u:
            continue
        entry = r.to_dict()
        entry['nome']  = u.nome
        entry['cargo'] = u.cargo or '—'
        if not r.saida:
            entry['total'] = 'Em curso' if r.entrada else '—'
        entry['status'] = 'completo' if r.saida else ('andamento' if r.entrada else 'ausente')
        resultado.append(entry)
    return jsonify({'ok': True, 'data_fmt': d.strftime('%d/%m/%Y'), 'registros': resultado})

@app.route('/admin/promover/<int:uid>', methods=['POST'])
@admin_required
def admin_promover(uid):
    alvo = User.query.get_or_404(uid)
    alvo.is_admin = not alvo.is_admin
    db.session.commit()
    return jsonify({'ok': True, 'is_admin': alvo.is_admin})

@app.route('/admin/excluir_usuario/<int:uid>', methods=['POST'])
@admin_required
def admin_excluir_usuario(uid):
    u = current_user()
    if uid == u.id:
        return jsonify({'ok': False, 'erro': 'Não pode excluir a si mesmo.'})
    alvo = User.query.get_or_404(uid)
    db.session.delete(alvo)
    db.session.commit()
    return jsonify({'ok': True})

# ─────────────── INIT ────────────────────────────────────────────

def _init_db():
    try:
        db.create_all()
        try:
            db.session.execute(db.text('ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN DEFAULT 0'))
            db.session.commit()
        except Exception:
            db.session.rollback()
        changed = False
        for email in ADMIN_EMAILS:
            adm = User.query.filter_by(email=email).first()
            if adm and not adm.is_admin:
                adm.is_admin = True
                changed = True
        if changed:
            db.session.commit()
        if not User.query.first():
            demo = User(nome='Demo ErgoWork', email='demo@ergo.com',
                        senha_hash=generate_password_hash('1234'), cargo='Analista')
            db.session.add(demo); db.session.commit()
            print('Usuario demo: demo@ergo.com / 1234')
    except Exception as e:
        print(f'[WARN] init_db falhou (DB pode estar indisponivel): {e}')

with app.app_context():
    _init_db()

if __name__ == '__main__':
    port  = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV','development') == 'development'
    print(f'http://localhost:{port}  |  demo@ergo.com / 1234')
    app.run(debug=debug, host='0.0.0.0', port=port)
