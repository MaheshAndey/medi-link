# 🚀 FastAPI App

This guide works on **Windows (CMD & PowerShell), macOS, and Linux**.

---

## 📦 Requirements

- Python 3.7 or higher
- pip (comes with Python)

---

## 🧪 Step 1: Create a `.env` File

Create a `.env` file in the root of your project (same level as `main.py`) and add:

```env
DATABASE_PASSWORD="your db password"
DATABASE_NAME="your db name"
```

> Replace `your db password` and `your db name` with your actual database credentials.
> Create the database in mysql if it doesn't exist. (with the same name given above)

---

## ⚙️ Step 2: Set Up the Virtual Environment

### ✅ On Linux / macOS / WSL

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### ✅ On Windows CMD

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### ✅ On Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

---

## 📦 Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> Make sure `python-dotenv` is listed in your `requirements.txt`.

---

## 🚀 Step 5: Run the FastAPI App

After setting up the `.env` and installing dependencies:

```bash
uvicorn main:app --reload
```

> Replace `main:app` if your app entry point is different.

---

## 🌐 API Access

- [http://127.0.0.1:8000](http://127.0.0.1:8000) – Base URL  
- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) – Swagger UI  
- [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) – ReDoc
