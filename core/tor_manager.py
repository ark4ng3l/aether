"""
TorManager — Autonomous Embedded Tor Service & SOCKS5 Gateway for AETHER.

Features:
- Zero-Configuration Bootstrap: Automatically downloads & extracts official standalone Tor binaries
  (Windows, Linux, macOS) into `data/tor/`.
- Embedded Daemon Controller: Asynchronously starts, monitors, and stops local `tor.exe` subprocess.
- Live Bootstrap Tracking: Parses Tor stdout log to monitor consensus and bootstrap progress (0-100%).
- Circuit Rotation: Sends NEWNYM signal to rotate exit nodes and obtain fresh identities.
- SOCKS5 & Onion Routing: Provides seamless HTTP proxy routing (`socks5://127.0.0.1:9050`) for darkweb recon.
"""

from __future__ import annotations

import asyncio
import io
import os
import platform
import re
import shutil
import socket
import sys
import tarfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import httpx

from aether.core.logger import logger
from aether.config.settings import settings

BASE_DIR = Path(__file__).resolve().parent.parent
TOR_DIR = BASE_DIR / "data" / "tor"
TOR_BIN_DIR = TOR_DIR / "bin"
TOR_DATA_DIR = TOR_DIR / "data"
TOR_CONF_FILE = TOR_DIR / "torrc"

# Official Tor Expert Bundle archive versions
TOR_VERSION = "14.0.6"
TOR_VERSION_FILE = TOR_DIR / "version.json"
TOR_ARCHIVE_BASE = "https://archive.torproject.org/tor-package-archive/torbrowser/"


class TorManager:
    """
    Autonomous Manager for embedded Tor daemon.
    Handles downloading, process lifecycle, circuit rotation, version inspection, and hot upgrades.
    """

    def __init__(
        self,
        socks_port: int = 9050,
        control_port: int = 9051,
        host: str = "127.0.0.1",
    ):
        self.socks_port = socks_port
        self.control_port = control_port
        self.host = host
        self._process: Optional[asyncio.subprocess.Process] = None
        self._log_monitor_task: Optional[asyncio.Task] = None
        self.bootstrap_progress: int = 0
        self.bootstrap_summary: str = "Stopped"
        self.is_bootstrapped: bool = False
        self.last_error: Optional[str] = None
        self._exit_ip_cache: Optional[str] = None
        self._exit_ip_updated_at: float = 0
        self._installed_bundle_version: str = self._load_installed_bundle_version()

    def _load_installed_bundle_version(self) -> str:
        """Reads installed bundle version from version.json or defaults to TOR_VERSION."""
        if TOR_VERSION_FILE.exists():
            try:
                import json
                data = json.loads(TOR_VERSION_FILE.read_text(encoding="utf-8"))
                return data.get("bundle_version", TOR_VERSION)
            except Exception:
                pass
        return TOR_VERSION

    def _save_installed_bundle_version(self, version: str):
        """Persists the installed bundle version to version.json."""
        try:
            import json
            TOR_DIR.mkdir(parents=True, exist_ok=True)
            TOR_VERSION_FILE.write_text(
                json.dumps({
                    "bundle_version": version,
                    "updated_at": time.time(),
                }, indent=2),
                encoding="utf-8",
            )
            self._installed_bundle_version = version
        except Exception as exc:
            logger.warning(f"Failed to write version.json: {exc}")

    @property
    def socks_proxy_url(self) -> str:
        return f"socks5://{self.host}:{self.socks_port}"

    @property
    def is_installed(self) -> bool:
        """Checks if standalone tor binary exists in data/tor/bin."""
        tor_exe = self._get_tor_executable()
        return tor_exe is not None and tor_exe.exists()

    @property
    def is_running(self) -> bool:
        """Checks if embedded Tor process is running or port 9050 is open."""
        if self._process is not None and self._process.returncode is None:
            return True
        return self._is_port_listening(self.host, self.socks_port)

    def _get_tor_executable(self) -> Optional[Path]:
        """Locates the tor binary based on platform."""
        system = platform.system().lower()
        if system == "windows":
            exe_name = "tor.exe"
        else:
            exe_name = "tor"

        # 1. Check inside data/tor/bin/tor/tor.exe
        candidate = TOR_BIN_DIR / "tor" / exe_name
        if candidate.exists():
            return candidate

        # 2. Check inside data/tor/bin/tor.exe
        candidate = TOR_BIN_DIR / exe_name
        if candidate.exists():
            return candidate

        # 3. Check system PATH fallback
        which_path = shutil.which(exe_name)
        if which_path:
            return Path(which_path)

        return None

    def get_installed_version(self) -> Dict[str, Any]:
        """Queries local tor.exe binary for engine version and reports bundle release."""
        tor_exe = self._get_tor_executable()
        if not tor_exe or not tor_exe.exists():
            return {
                "installed": False,
                "engine_version": None,
                "bundle_version": None,
            }

        engine_ver = "Unknown"
        try:
            import subprocess
            out = subprocess.check_output([str(tor_exe), "--version"], stderr=subprocess.STDOUT, timeout=5).decode(errors="ignore")
            first_line = out.strip().splitlines()[0] if out.strip() else ""
            if "Tor version" in first_line:
                engine_ver = first_line.split("(")[0].strip()
            else:
                engine_ver = first_line
        except Exception as exc:
            engine_ver = f"Probe error: {exc}"

        return {
            "installed": True,
            "engine_version": engine_ver,
            "bundle_version": self._installed_bundle_version,
            "binary_path": str(tor_exe),
        }

    async def check_updates(self) -> Dict[str, Any]:
        """
        Scans official Tor Project distribution archive for latest release bundles.
        Compares with local version to determine upgrade availability.
        """
        current_ver_info = self.get_installed_version()
        installed_bundle = self._installed_bundle_version

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(TOR_ARCHIVE_BASE)
                if resp.status_code != 200:
                    return {
                        "check_success": False,
                        "error": f"HTTP {resp.status_code} from Tor Project Archive",
                        "current_bundle": installed_bundle,
                        "latest_bundle": installed_bundle,
                        "update_available": False,
                    }

                matches = [m for m in re.findall(r'href="([0-9]+\.[0-9]+(?:\.[0-9]+)?)/"', resp.text) if m[0].isdigit()]
                if not matches:
                    return {
                        "check_success": False,
                        "error": "No version tags discovered",
                        "current_bundle": installed_bundle,
                        "latest_bundle": installed_bundle,
                        "update_available": False,
                    }

                # Sort by semver (ignoring alpha/beta tags)
                valid_versions = []
                for v in matches:
                    parts = v.split(".")
                    if len(parts) >= 2 and all(p.isdigit() for p in parts):
                        # Filter for stable 14.x branch
                        if parts[0] == "14":
                            valid_versions.append(v)

                sorted_v = sorted(valid_versions, key=lambda v: [int(x) for x in v.split(".")]) if valid_versions else matches
                latest_bundle = sorted_v[-1] if sorted_v else installed_bundle

                # Compare versions
                curr_parts = [int(x) for x in installed_bundle.split(".") if x.isdigit()]
                latest_parts = [int(x) for x in latest_bundle.split(".") if x.isdigit()]
                update_available = latest_parts > curr_parts

                return {
                    "check_success": True,
                    "installed_engine_version": current_ver_info.get("engine_version"),
                    "installed_bundle": installed_bundle,
                    "latest_bundle": latest_bundle,
                    "update_available": update_available,
                    "release_archive_url": f"{TOR_ARCHIVE_BASE}{latest_bundle}/",
                }

        except Exception as exc:
            return {
                "check_success": False,
                "error": str(exc),
                "installed_bundle": installed_bundle,
                "latest_bundle": installed_bundle,
                "update_available": False,
            }

    async def upgrade(self, target_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs an in-place hot upgrade to target_version (or latest discovered release).
        Gracefully pauses daemon, extracts new binaries, and resumes Tor service.
        """
        if not target_version:
            up_info = await self.check_updates()
            target_version = up_info.get("latest_bundle") or TOR_VERSION

        logger.info(f"Initiating Tor upgrade to bundle version: {target_version}")
        was_running = self.is_running
        prev_version = self._installed_bundle_version

        if was_running:
            logger.info("Stopping active Tor daemon for binary replacement...")
            await self.stop()

        ok = await self.bootstrap_binaries(version=target_version)
        if not ok:
            return {
                "success": False,
                "error": self.last_error or "Failed to install new Tor bundle",
                "current_version": prev_version,
            }

        self._save_installed_bundle_version(target_version)
        logger.info(f"Tor upgraded successfully from {prev_version} to {target_version}")

        if was_running:
            logger.info("Restarting upgraded Tor daemon...")
            await self.start()

        return {
            "success": True,
            "previous_version": prev_version,
            "current_bundle_version": target_version,
            "current_engine_version": self.get_installed_version().get("engine_version"),
            "running": self.is_running,
        }

    @staticmethod
    def _is_port_listening(host: str, port: int, timeout: float = 0.5) -> bool:
        """Probes whether a TCP port is currently open."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (OSError, ConnectionRefusedError):
            return False

    # --------------------------------------------------------------------------
    # Autonomous Download & Setup (Bootstrap)
    # --------------------------------------------------------------------------

    async def bootstrap_binaries(self, version: Optional[str] = None, on_progress=None) -> bool:
        """
        Automatically downloads and extracts official Tor Expert Bundle for the host OS.
        """
        target_v = version or self._installed_bundle_version or TOR_VERSION
        TOR_DIR.mkdir(parents=True, exist_ok=True)
        TOR_BIN_DIR.mkdir(parents=True, exist_ok=True)
        TOR_DATA_DIR.mkdir(parents=True, exist_ok=True)

        system = platform.system().lower()
        machine = platform.machine().lower()

        if system == "windows":
            pkg_name = f"tor-expert-bundle-windows-x86_64-{target_v}.tar.gz"
        elif system == "linux":
            pkg_name = f"tor-expert-bundle-linux-x86_64-{target_v}.tar.gz"
        elif system == "darwin":
            pkg_name = f"tor-expert-bundle-macos-{'aarch64' if 'arm' in machine or 'aarch64' in machine else 'x86_64'}-{target_v}.tar.gz"
        else:
            pkg_name = f"tor-expert-bundle-windows-x86_64-{target_v}.tar.gz"

        download_url = f"{TOR_ARCHIVE_BASE}{target_v}/{pkg_name}"
        logger.info(f"Downloading standalone Tor bundle from: {download_url}")
        self.bootstrap_summary = f"Downloading Tor bundle ({pkg_name})..."

        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                resp = await client.get(download_url)
                if resp.status_code != 200:
                    raise RuntimeError(f"Failed to download Tor package: HTTP {resp.status_code}")

                self.bootstrap_summary = "Extracting Tor binaries..."
                logger.info(f"Extracting Tor package ({len(resp.content)} bytes)...")

                with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
                    tar.extractall(path=TOR_BIN_DIR)

            # Ensure execution permissions on Unix
            if system != "windows":
                exe = self._get_tor_executable()
                if exe and exe.exists():
                    os.chmod(exe, 0o755)

            self._save_installed_bundle_version(target_v)
            self._write_torrc()
            logger.info(f"Tor binaries v{target_v} successfully installed and configured in data/tor/")
            self.bootstrap_summary = "Installed & Ready"
            return True

        except Exception as exc:
            self.last_error = f"Tor bootstrap failed: {exc}"
            self.bootstrap_summary = f"Error: {exc}"
            logger.error(self.last_error)
            return False

    def _write_torrc(self):
        """Generates a secure, embedded torrc configuration file."""
        TOR_DATA_DIR.mkdir(parents=True, exist_ok=True)
        geoip_file = TOR_BIN_DIR / "data" / "geoip"
        geoip6_file = TOR_BIN_DIR / "data" / "geoip6"

        config_lines = [
            "# AETHER Autonomous Tor Daemon Configuration",
            f"SocksPort {self.host}:{self.socks_port}",
            f"ControlPort {self.host}:{self.control_port}",
            f'DataDirectory "{TOR_DATA_DIR.as_posix()}"',
            "CookieAuthentication 0",  # Simple local control
            "AvoidDiskWrites 1",
            "Log notice stdout",
        ]

        if geoip_file.exists():
            config_lines.append(f'GeoIPFile "{geoip_file.as_posix()}"')
        if geoip6_file.exists():
            config_lines.append(f'GeoIPv6File "{geoip6_file.as_posix()}"')

        TOR_CONF_FILE.write_text("\n".join(config_lines) + "\n", encoding="utf-8")

    # --------------------------------------------------------------------------
    # Process Lifecycle (Start / Stop)
    # --------------------------------------------------------------------------

    async def start(self) -> bool:
        """
        Starts the Tor daemon. If binaries are missing, automatically downloads them first.
        """
        # If an external Tor instance is already active on 9050, use it
        if self._is_port_listening(self.host, self.socks_port):
            logger.info(f"Existing Tor SOCKS5 proxy detected on {self.socks_proxy_url}. Ready.")
            self.is_bootstrapped = True
            self.bootstrap_progress = 100
            self.bootstrap_summary = "Connected to Active Tor Proxy"
            return True

        if not self.is_installed:
            logger.info("Tor binaries not found locally. Initiating autonomous download...")
            ok = await self.bootstrap_binaries()
            if not ok:
                return False

        self._write_torrc()
        tor_exe = self._get_tor_executable()
        if not tor_exe:
            self.last_error = "Tor executable binary not found"
            return False

        logger.info(f"Starting embedded Tor daemon: {tor_exe}")
        self.bootstrap_progress = 0
        self.is_bootstrapped = False
        self.bootstrap_summary = "Starting daemon..."

        try:
            self._process = await asyncio.create_subprocess_exec(
                str(tor_exe),
                "-f",
                str(TOR_CONF_FILE),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(TOR_DIR),
            )

            # Start background stdout reader
            self._log_monitor_task = asyncio.create_task(self._monitor_tor_output())

            # Wait up to 30 seconds for bootstrap or port availability
            for _ in range(60):
                if self.is_bootstrapped or self._is_port_listening(self.host, self.socks_port):
                    self.is_bootstrapped = True
                    self.bootstrap_progress = 100
                    self.bootstrap_summary = "Bootstrapped 100% (Done)"
                    logger.info("Embedded Tor daemon successfully bootstrapped & ready!")
                    return True
                if self._process.returncode is not None:
                    self.last_error = f"Tor process exited prematurely with code {self._process.returncode}"
                    return False
                await asyncio.sleep(0.5)

            return self.is_bootstrapped
        except Exception as exc:
            self.last_error = f"Failed to spawn Tor subprocess: {exc}"
            logger.error(self.last_error)
            return False

    async def _monitor_tor_output(self):
        """Reads stdout of Tor process to track bootstrapping percentage."""
        if not self._process or not self._process.stdout:
            return

        while self._process.returncode is None:
            line = await self._process.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="ignore").strip()
            if "Bootstrapped" in text:
                match = re.search(r"Bootstrapped (\d+)%", text)
                if match:
                    self.bootstrap_progress = int(match.group(1))
                    self.bootstrap_summary = text.split("]:")[-1].strip() if "]:" in text else text
                    if self.bootstrap_progress >= 100:
                        self.is_bootstrapped = True
            elif "[err]" in text or "[warn]" in text:
                logger.warning(f"Tor: {text}")

    async def stop(self) -> bool:
        """Stops the embedded Tor subprocess."""
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

        if self._log_monitor_task and not self._log_monitor_task.done():
            self._log_monitor_task.cancel()

        self.is_bootstrapped = False
        self.bootstrap_progress = 0
        self.bootstrap_summary = "Stopped"
        logger.info("Embedded Tor daemon stopped.")
        return True

    # --------------------------------------------------------------------------
    # Circuit Rotation & Diagnostics
    # --------------------------------------------------------------------------

    async def new_circuit(self) -> bool:
        """Sends SIGNAL NEWNYM to rotate Tor identity / circuit."""
        try:
            reader, writer = await asyncio.open_connection(self.host, self.control_port)
            writer.write(b"AUTHENTICATE\r\n")
            await writer.drain()
            auth_resp = await reader.readline()

            writer.write(b"SIGNAL NEWNYM\r\n")
            await writer.drain()
            signal_resp = await reader.readline()

            writer.write(b"QUIT\r\n")
            await writer.drain()
            writer.close()
            await writer.wait_closed()

            self._exit_ip_cache = None
            logger.info("Tor circuit rotated (SIGNAL NEWNYM sent).")
            return True
        except Exception as exc:
            logger.warning(f"Failed to send SIGNAL NEWNYM via control port: {exc}")
            return False

    async def get_exit_ip(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Queries check.torproject.org through the SOCKS5 proxy to verify Tor routing."""
        now = time.time()
        if not force_refresh and self._exit_ip_cache and (now - self._exit_ip_updated_at < 60):
            return {"tor_active": True, "ip": self._exit_ip_cache, "cached": True}

        if not self.is_running:
            return {"tor_active": False, "ip": None, "error": "Tor daemon is not running"}

        try:
            async with httpx.AsyncClient(
                proxy=self.socks_proxy_url,
                timeout=15.0,
            ) as client:
                resp = await client.get("https://check.torproject.org/api/ip")
                if resp.status_code == 200:
                    data = resp.json()
                    self._exit_ip_cache = data.get("IP")
                    self._exit_ip_updated_at = now
                    return {
                        "tor_active": data.get("IsTor", True),
                        "ip": self._exit_ip_cache,
                        "cached": False,
                    }
        except Exception as exc:
            return {"tor_active": False, "ip": None, "error": str(exc)}

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive diagnostic status of the Tor subsystem."""
        ver_info = self.get_installed_version()
        return {
            "installed": self.is_installed,
            "running": self.is_running,
            "bootstrapped": self.is_bootstrapped,
            "bootstrap_progress_pct": self.bootstrap_progress,
            "bootstrap_summary": self.bootstrap_summary,
            "engine_version": ver_info.get("engine_version"),
            "bundle_version": self._installed_bundle_version,
            "socks_proxy_url": self.socks_proxy_url,
            "socks_port": self.socks_port,
            "control_port": self.control_port,
            "last_error": self.last_error,
            "exit_ip": self._exit_ip_cache,
        }


# Global singleton instance
tor_manager = TorManager()
