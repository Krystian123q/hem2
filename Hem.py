import os
import sys
import subprocess
import shutil
import re

LOG_FILE = "hem_log.txt"

def log(msg):
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def pause(msg="Naciśnij dowolny klawisz, aby zakończyć..."):
    """Pause execution waiting for user input."""
    try:
        input(msg)
    except EOFError:
        pass

def clear_log():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

def get_repo_name(url):
    name = url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name

def check_program(cmd):
    try:
        subprocess.run([cmd, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False

def clone_repo(url, target_dir):
    if os.path.exists(target_dir):
        log(f"Folder '{target_dir}' już istnieje. Usuwam go...")
        shutil.rmtree(target_dir)
    log(f"Klonuję repozytorium z {url} do {target_dir}...")
    result = subprocess.run(["git", "clone", url, target_dir], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    log(result.stdout)
    if result.returncode != 0:
        log("Błąd podczas klonowania repozytorium!")
        log(result.stderr)
        return False
    return True

def detect_project_type(path):
    if os.path.exists(os.path.join(path, "requirements.txt")):
        return "python"
    if os.path.exists(os.path.join(path, "package.json")):
        return "node"
    if os.path.exists(os.path.join(path, "Cargo.toml")):
        return "rust"
    return None

def install_deps_and_run(path, proj_type):
    os.chdir(path)
    if proj_type == "python":
        python = shutil.which("python") or shutil.which("python3")
        if not python:
            log("Python nie jest zainstalowany!")
            return False
        if os.path.exists("requirements.txt"):
            log("Instaluję zależności Pythona...")
            res = subprocess.run([python, "-m", "pip", "install", "-r", "requirements.txt"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            log(res.stdout + res.stderr)
            if res.returncode != 0:
                log("Błąd podczas instalacji zależności Pythona!")
                return False
        main_py = "main.py" if os.path.exists("main.py") else None
        if not main_py:
            # Szukaj jakiegokolwiek pliku .py
            for f in os.listdir("."):
                if f.endswith(".py"):
                    main_py = f
                    break
        if main_py:
            log(f"Uruchamiam {main_py} ...")
            res = subprocess.run([python, main_py], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            log(res.stdout + res.stderr)
        else:
            log("Nie znaleziono pliku main.py")
    elif proj_type == "node":
        if not check_program("npm"):
            log("Node.js/npm nie jest zainstalowany!")
            return False
        log("Instaluję zależności Node.js (npm install)...")
        res = subprocess.run(["npm", "install"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        log(res.stdout + res.stderr)
        if res.returncode != 0:
            log("Błąd podczas npm install!")
            return False
        log("Uruchamiam npm start ...")
        res = subprocess.run(["npm", "start"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        log(res.stdout + res.stderr)
    elif proj_type == "rust":
        if not check_program("cargo"):
            log("Rust/cargo nie jest zainstalowany!")
            return False
        log("Instaluję zależności Rust (cargo build)...")
        res = subprocess.run(["cargo", "build"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        log(res.stdout + res.stderr)
        if res.returncode != 0:
            log("Błąd podczas cargo build!")
            return False
        log("Uruchamiam cargo run ...")
        res = subprocess.run(["cargo", "run"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        log(res.stdout + res.stderr)
    else:
        log("Nie rozpoznano typu projektu.")
        return False
    return True

def main():
    clear_log()
    log("==== Hem - GitHub Project Runner ====")
    url = ""
    if len(sys.argv) > 1:
        url = sys.argv[1]
    while not re.match(r"^https?://github\.com/.+?/.+?\.git$", url):
        url = input("Wklej link do repozytorium (np. https://github.com/realpython/materials.git): ").strip()
    repo_name = get_repo_name(url)
    target_path = os.path.join("projekty", repo_name)
    if not check_program("git"):
        log("Git nie jest zainstalowany!")
        pause()
        return
    if not clone_repo(url, target_path):
        pause()
        return
    proj_type = detect_project_type(target_path)
    if not proj_type:
        log("Nie wykryto typu projektu (brak pliku requirements.txt, package.json, Cargo.toml).")
        pause()
        return
    log(f"Wykryto projekt: {proj_type}")
    ok = install_deps_and_run(target_path, proj_type)
    if ok:
        log("\nProjekt został uruchomiony.")
    else:
        log("\nWystąpił błąd podczas uruchamiania projektu.")
    pause()

if __name__ == "__main__":
    main()
