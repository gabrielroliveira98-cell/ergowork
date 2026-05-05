# 🪑 ErgoWork — Guia Completo

## 🚀 Como Rodar (3 passos)

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Rodar o servidor
python app.py

# 3. Abrir no navegador
# http://localhost:5000
# Login demo: demo@ergo.com / 1234
```

---

## 📱 Acessar pelo Celular / Android / Emulador

### Celular na mesma rede Wi-Fi:
```bash
# Descubra o IP do seu computador:
# Windows: ipconfig
# Mac/Linux: ifconfig ou ip addr

# Rode com:
python app.py
# Acesse no celular: http://SEU_IP:5000
# Exemplo: http://192.168.1.10:5000
```

### Emulador Android (Android Studio):
```
# O emulador usa o IP especial 10.0.2.2 para acessar o localhost
# Acesse no emulador: http://10.0.2.2:5000
```

### Instalar como app no Android (PWA):
1. Abra o site no Chrome para Android
2. Toque no menu ⋮ → "Adicionar à tela inicial"
3. O app aparecerá como ícone na tela inicial

---

## 🔑 Ativar Login com Google

### Passo 1 — Criar credenciais no Google Cloud:
1. Acesse: https://console.cloud.google.com
2. Crie um projeto novo (ou use um existente)
3. Menu → "APIs e Serviços" → "Credenciais"
4. Clique em "+ Criar credenciais" → "ID do cliente OAuth 2.0"
5. Tipo: **Aplicativo da Web**
6. URIs de redirecionamento autorizados:
   - `http://localhost:5000/login/google/callback`
   - `http://SEU_IP:5000/login/google/callback` (para acesso na rede)
   - `https://SEU_DOMINIO/login/google/callback` (em produção)
7. Copie o **Client ID** e o **Client Secret**

### Passo 2 — Criar arquivo `.env`:
```bash
# Crie um arquivo .env na raiz do projeto:
GOOGLE_CLIENT_ID=seu_client_id_aqui.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu_client_secret_aqui
SECRET_KEY=uma_chave_secreta_qualquer_aqui
```

### Passo 3 — Carregar o .env ao rodar:
```bash
# Instale python-dotenv:
pip install python-dotenv

# Adicione no INÍCIO do app.py (antes de tudo):
from dotenv import load_dotenv
load_dotenv()
```

### Resultado:
O botão "Entrar com Google" na tela de login funcionará. Qualquer pessoa com conta Google poderá entrar.

---

## 🌐 Publicar Online (qualquer pessoa acessar)

### Opção 1 — Railway.app (gratuito, recomendado):
1. Crie conta em railway.app
2. Clique em "New Project" → "Deploy from GitHub"
3. Faça upload do código ou conecte o repositório
4. Configure as variáveis de ambiente (GOOGLE_CLIENT_ID, etc.)
5. URL pública será gerada automaticamente

### Opção 2 — Render.com (gratuito):
1. Crie conta em render.com
2. "New Web Service" → conecte o repositório
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`

### Opção 3 — Heroku:
```bash
pip install gunicorn
echo "web: gunicorn app:app" > Procfile
heroku create meu-ergowork
heroku config:set GOOGLE_CLIENT_ID=xxx GOOGLE_CLIENT_SECRET=xxx
git push heroku main
```

---

## 📁 Estrutura de Arquivos

```
ergowork/
├── app.py                    ← Backend Flask completo
├── requirements.txt          ← Flask, SQLAlchemy, Werkzeug
├── .env                      ← (crie você) Google OAuth keys
├── README.md                 ← Este arquivo
├── templates/
│   ├── base.html             ← HTML base com meta tags mobile
│   ├── layout.html           ← Sidebar + bottom nav mobile
│   ├── login.html            ← Login com Google + email/senha
│   ├── cadastro.html
│   ├── dashboard.html
│   ├── ponto.html            ← Ponto com câmera
│   ├── checklist.html        ← Sim/Não com feedback detalhado
│   ├── exercicios.html       ← Vídeos YouTube + timer
│   ├── midias.html           ← Upload fotos e VÍDEOS (corrigido)
│   └── perfil.html
├── static/
│   ├── css/style.css         ← Design responsivo mobile-first
│   ├── js/app.js
│   └── uploads/
│       ├── fotos/
│       └── videos/
└── instance/
    └── ergowork.db           ← SQLite (criado automaticamente)
```

---

## 🐛 Correções desta versão

| Problema | Correção |
|---|---|
| Vídeos não enviavam | XHR com progresso, aceita mp4/mov/webm/avi/mkv/ogg/m4v/3gp |
| Checklist sem feedback | 10 perguntas Sim/Não com feedback positivo e plano de melhoria |
| Exercícios sem vídeo | YouTube embed para cada exercício + passo a passo |
| Mobile sem responsivo | Bottom nav, meta tags, touch-action, font-size 16px |
| Câmera não funcionava | Fallback para gravação de vídeo com MediaRecorder |

---

## ❓ Problemas Comuns

| Erro | Solução |
|---|---|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| Porta 5000 ocupada | Edite `port=5001` no final do app.py |
| Upload falha com arquivo grande | Verifique `MAX_CONTENT_LENGTH` no app.py (padrão: 500MB) |
| Google OAuth não funciona | Verifique URI de redirecionamento no Google Cloud Console |
| Vídeo não reproduz no mobile | Use formato MP4 H.264, que tem suporte universal |
| Câmera bloqueada | Use HTTPS ou localhost (navegadores bloqueiam câmera em HTTP externo) |
