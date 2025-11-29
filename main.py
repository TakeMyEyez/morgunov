from fastapi import FastAPI, Form, UploadFile, File, Request, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os, uvicorn, uuid, time

SESSIONS = {}
SESSION_LIFETIME = 10

USERS = {
    "admin": "admin",
    "user": "pass"}

SECRET_KEY = "super_secret_jwt_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 5

app = FastAPI()
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

movies = [
    {"name": "Начало", "id": 1, "cost": 160, "director": "Кристофер Нолан", "image_path": "/static/"},
    {"name": "Интерстеллар", "id": 2, "cost": 165, "director": "Кристофер Нолан", "image_path": "/static/"},
    {"name": "Паразиты", "id": 3, "cost": 11, "director": "Пон Джун-хо", "image_path": "/static/"},
    {"name": "Джокер", "id": 4, "cost": 55, "director": "Тодд Филлипс", "image_path": "/static/"},
    {"name": "Матрица", "id": 5, "cost": 63, "director": "Лана и Лилли Вачовски", "image_path": "/static/"},
    {"name": "Форрест Гамп", "id": 6, "cost": 55, "director": "Роберт Земекис", "image_path": "/static/"},
    {"name": "Гладиатор", "id": 7, "cost": 103, "director": "Ридли Скотт", "image_path": "/static/"},
    {"name": "Зеленая миля", "id": 8, "cost": 60, "director": "Фрэнк Дарабонт", "image_path": "/static/"},
    {"name": "Темный рыцарь", "id": 9, "cost": 185, "director": "Кристофер Нолан", "image_path": "/static/"},
    {"name": "Побег из Шоушенка", "id": 10, "cost": 25, "director": "Фрэнк Дарабонт", "image_path": "/static/"}
]


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/study", response_class=HTMLResponse)
async def study_info():
    return """  
    <!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><title>Информация о БГИТУ</title></head>    <body style="font-family:Arial;text-align:center;background-color:#f5f5f5;padding:40px">        <h1>БГИТУ</h1><p>Брянский государственный инженерно-технологический университет</p>        <img src="/static/bgitu.jpg" alt="БГИТУ" style="width:400px;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,0.3)">    </body></html>    """


@app.get("/movietop/{movie_name}")
async def get_movie_info(movie_name: str):
    movie = next((m for m in movies if m["name"].lower() == movie_name.lower()), None)
    return movie or {"error": "Movie not found"}


@app.get("/movietop/")
async def get_all_movies():
    return {"movies": movies}


@app.get("/add-movie", response_class=HTMLResponse)
async def add_movie_form():
    movies_html = "".join([
        f"""  
        <div class="movie-card">            <img src="{m['image_path']}" alt="{m['name']}" class="movie-image">  
            <div class="movie-info"><h3 class="movie-title">{m['name']}</h3>  
                <p><strong>Режиссер:</strong> {m['director']}</p>  
                <p><strong>Бюджет:</strong> {m['cost']} млн $</p>            </div>        </div>""" for m in movies
    ])
    return HTMLResponse(f"""  
    <!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">    <meta name="viewport" content="width=device-width,initial-scale=1.0">    <title>Добавить фильм</title><link rel="stylesheet" href="/static/index.css"></head>    <body><div class="container"><h1>Добавить новый фильм</h1>    <form method="post" action="/add-movie" enctype="multipart/form-data" class="movie-form">        <input type="text" name="name" placeholder="Название фильма" required>        <input type="text" name="director" placeholder="Режиссер" required>        <input type="number" name="cost" placeholder="Бюджет (в млн $)" step="0.1" required>        <textarea name="description" placeholder="Описание фильма" required></textarea>        <label><input type="checkbox" name="is_published" checked> Опубликован</label>        <input type="file" name="image" accept="image/*" required>        <button type="submit" class="submit-btn">Добавить фильм</button>    </form><h2>Все фильмы</h2><div class="movies-grid">{movies_html}</div></div></body></html>  
    """)


@app.post("/add-movie")
async def add_movie(name: str = Form(...), director: str = Form(...), cost: float = Form(...),
                    description: str = Form(...), is_published: bool = Form(True),
                    image: UploadFile = File(...)):
    new_id = max(m["id"] for m in movies) + 1
    path = f"static/uploads/movie_{new_id}_{image.filename}"
    with open(path, "wb") as f: f.write(await image.read())
    movies.append({"name": name, "id": new_id, "cost": cost, "director": director,
                   "description": description, "is_published": is_published, "image_path": f"/{path}"})
    return RedirectResponse(url="/add-movie", status_code=303)


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if USERS.get(username) == password:
        token = str(uuid.uuid4())
        now = time.time()
        SESSIONS[token] = {"username": username, "login_time": now, "expires": now + SESSION_LIFETIME}
        response = JSONResponse({"message": "Login successful"})
        response.set_cookie("session_token", token, httponly=True, max_age=SESSION_LIFETIME)
        return response
    return JSONResponse({"message": "Invalid credentials"}, status_code=401)


@app.get("/user")
async def user_info(request: Request):
    token = request.cookies.get("session_token")
    if not token or token not in SESSIONS:
        return JSONResponse({"message": "Unauthorized"}, status_code=401)
    session = SESSIONS[token]
    now = time.time()
    if now > session["expires"]:
        del SESSIONS[token]
        return JSONResponse({"message": "Unauthorized"}, status_code=401)
    session["expires"] = now + SESSION_LIFETIME
    data = {
        "username": session["username"],
        "login_time": time.strftime("%H:%M:%S", time.localtime(session["login_time"])),
        "session_expires": time.strftime("%H:%M:%S", time.localtime(session["expires"])),
        "movies": movies
    }
    response = JSONResponse(data)
    response.set_cookie("session_token", token, httponly=True, max_age=SESSION_LIFETIME)
    return response


@app.get("/login", response_class=HTMLResponse)
async def login_form():
    return """  
    <form method="post" action="/login">        <input name="username" placeholder="Имя пользователя">        <input type="password" name="password" placeholder="Пароль">        <button type="submit">Войти</button>    </form>    """


def create_jwt_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_jwt_token(credentials: str):
    try:
        payload = jwt.decode(credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        return username
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


@app.post("/jwt-login")
async def jwt_login(data: dict):
    username = data.get("username")
    password = data.get("password")

    if USERS.get(username) != password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_jwt_token(
        data={"sub": username},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


if __name__ == "__main__":
    uvicorn.run("main:app", port=8165, reload=True)
