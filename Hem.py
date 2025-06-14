import os
import sys
import subprocess
import shutil
import re
import tempfile
import urllib.request
import json

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

def install_via_pkg_mgr(packages):
    """Install the given packages using the available package manager."""
    try:
        if shutil.which("apt-get"):
            subprocess.run(["sudo", "apt-get", "update", "-y"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y"] + packages, check=True)
        elif shutil.which("yum"):
            subprocess.run(["sudo", "yum", "-y", "install"] + packages, check=True)
        elif shutil.which("brew"):
            subprocess.run(["brew", "install"] + packages, check=True)
        else:
            return False
    except Exception as exc:
        log(f"Błąd instalacji pakietu: {exc}")
        return False
    return True

def get_latest_git_url():
    """Return download URL for the latest Git for Windows installer."""
    api = "https://api.github.com/repos/git-for-windows/git/releases/latest"
    try:
        with urllib.request.urlopen(api) as resp:
            data = json.load(resp)
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if name.endswith("64-bit.exe"):
                return asset.get("browser_download_url")
    except Exception as exc:
        log(f"Nie udało się pobrać info o najnowszym Git: {exc}")
    return "https://github.com/git-for-windows/git/releases/latest/download/Git-64-bit.exe"

def install_git():
    """Attempt to download and install Git silently."""
    log("Próba automatycznej instalacji Git...")
    try:
        if os.name == "nt":
            if shutil.which("winget"):
                subprocess.run(["winget", "install", "--id", "Git.Git", "-e", "--silent"], check=True)
            elif shutil.which("choco"):
                subprocess.run(["choco", "install", "git", "-y"], check=True)
            else:
                url = get_latest_git_url()
                installer = os.path.join(tempfile.gettempdir(), "git_installer.exe")
                urllib.request.urlretrieve(url, installer)
                subprocess.run([installer, "/VERYSILENT", "/NORESTART"], check=True)
        else:
            if not install_via_pkg_mgr(["git"]):
                log("Automatyczna instalacja Git nie jest obsługiwana na tym systemie.")
                return False
    except Exception as exc:
        log(f"Błąd instalacji Git: {exc}")
        return False
    return check_program("git")

def install_python():
    log("Próba automatycznej instalacji Pythona...")
    try:
        if os.name == "nt":
            url = "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe"
            installer = os.path.join(tempfile.gettempdir(), "python_installer.exe")
            urllib.request.urlretrieve(url, installer)
            subprocess.run([installer, "/quiet", "InstallAllUsers=1", "PrependPath=1"], check=True)
        else:
            if not install_via_pkg_mgr(["python3", "python3-pip"]):
                return False
    except Exception as exc:
        log(f"Błąd instalacji Pythona: {exc}")
        return False
    return check_program("python3") or check_program("python")

def install_node():
    log("Próba automatycznej instalacji Node.js...")
    try:
        if os.name == "nt":
            url = "https://nodejs.org/dist/v20.10.0/node-v20.10.0-x64.msi"
            installer = os.path.join(tempfile.gettempdir(), "node_installer.msi")
            urllib.request.urlretrieve(url, installer)
            subprocess.run(["msiexec", "/i", installer, "/quiet", "/norestart"], check=True)
        else:
            if not install_via_pkg_mgr(["nodejs", "npm"]):
                return False
    except Exception as exc:
        log(f"Błąd instalacji Node.js: {exc}")
        return False
    return check_program("npm")

def install_rust():
    log("Próba automatycznej instalacji Rust...")
    try:
        if os.name == "nt":
            url = "https://win.rustup.rs/x86_64"
            installer = os.path.join(tempfile.gettempdir(), "rustup-init.exe")
            urllib.request.urlretrieve(url, installer)
            subprocess.run([installer, "-y"], check=True)
        else:
            subprocess.run(["sh", "-c", "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"], check=True)
    except Exception as exc:
        log(f"Błąd instalacji Rust: {exc}")
        return False
    return check_program("cargo")

def ensure_program(cmd):
    if check_program(cmd):
        return True
    installers = {
        "git": install_git,
        "python": install_python,
        "python3": install_python,
        "npm": install_node,
        "node": install_node,
        "cargo": install_rust,
    }
    installer = installers.get(cmd)
    if installer:
        return installer()
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
            if not ensure_program("python3"):
                log("Python nie jest zainstalowany!")
                return False
            python = shutil.which("python") or shutil.which("python3")
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
        if not ensure_program("npm"):
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
        if not ensure_program("cargo"):
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
    if not ensure_program("git"):
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
