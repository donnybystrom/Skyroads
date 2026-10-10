#!/usr/bin/env python3
"""Start/reuse this project's Ghidra backend; optionally launch the stdio bridge."""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "runtime"
GHIDRA = ROOT / "tools/ghidra_12.1.4_PUBLIC"
JAVA = Path("/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home/bin/java")
BRIDGE_PYTHON = ROOT / "ghidra-mcp/.venv/bin/python"
URL = "http://127.0.0.1:8089"
PIDFILE = RUNTIME / "ghidra.pid"


def identity():
    try:
        with urllib.request.urlopen(URL + "/mcp/instance_info", timeout=2) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


def owned(info):
    return info and PIDFILE.exists() and info.get("pid") == int(PIDFILE.read_text())


def main():
    RUNTIME.mkdir(exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    with (RUNTIME / "ghidra-start.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        info = identity()
        if "--stop" in sys.argv:
            if owned(info):
                os.kill(info["pid"], signal.SIGTERM)
                print("Stopping SRE Ghidra backend", file=sys.stderr)
                deadline = time.monotonic() + 15
                while owned(identity()) and time.monotonic() < deadline:
                    time.sleep(0.25)
                if owned(identity()):
                    raise RuntimeError("Ghidra did not stop within 15 seconds")
            elif info:
                raise RuntimeError("Port 8089 belongs to another instance; leaving it running")
            return
        if info and not owned(info):
            raise RuntimeError("Port 8089 belongs to another instance; refusing to reuse it")
        if not info:
            jars = [ROOT / "ghidra-mcp/build/libs/GhidraMCP-7.0.0.jar"]
            jars += sorted((GHIDRA / "Ghidra").glob("**/lib/*.jar"))
            for directory in [RUNTIME / "ghidra-user", RUNTIME / "java-tmp", RUNTIME / "sockets"]:
                directory.mkdir(exist_ok=True)
            vmargs = subprocess.check_output([
                str(JAVA), "-cp", str(GHIDRA / "support/LaunchSupport.jar"),
                "LaunchSupport", str(GHIDRA), "-vmargs",
            ], text=True).splitlines()
            command = [str(JAVA), *vmargs, "-Xmx2G", "-Djava.awt.headless=true",
                       f"-Duser.home={RUNTIME / 'ghidra-user'}",
                       f"-Djava.io.tmpdir={RUNTIME / 'java-tmp'}",
                       f"-Dghidra.home={GHIDRA}", "-cp", os.pathsep.join(map(str, jars)),
                       "com.xebyte.headless.GhidraMCPHeadlessServer", "--bind", "127.0.0.1", "--port", "8089"]
            project = ROOT / "projects/SkyRoads.gpr"
            if project.exists():
                command += ["--project", str(project), "--program", "SKYROADS.EXE"]
            with (ROOT / "logs/ghidra-server.log").open("a") as log:
                child = subprocess.Popen(command, cwd=GHIDRA, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=log, start_new_session=True)
            PIDFILE.write_text(str(child.pid))
            deadline = time.monotonic() + 100
            while time.monotonic() < deadline:
                info = identity()
                if owned(info):
                    break
                if child.poll() is not None:
                    raise RuntimeError("Ghidra exited; see logs/ghidra-server.log")
                time.sleep(0.5)
            else:
                raise RuntimeError("Ghidra startup timed out; see logs/ghidra-server.log")
        if (ROOT / "projects/SkyRoads.gpr").exists():
            if info.get("project") != "SkyRoads" or not any(
                p.get("name") == "SKYROADS.EXE" and p.get("open")
                for p in info.get("programs", [])
            ):
                raise RuntimeError("SkyRoads project/program was not opened; see logs/ghidra-server.log")
        print(f"SRE Ghidra ready: {URL} (PID {info['pid']})", file=sys.stderr)
    if "--start-only" not in sys.argv:
        os.execv(str(BRIDGE_PYTHON), [str(BRIDGE_PYTHON), "-m", "bridge_mcp_ghidra", "--transport", "stdio", "--no-lazy"])


if __name__ == "__main__":
    main()
