"""Disposable BV-05 fixture: PKI, public-only kit, and loopback HTTPS receiver.

Every key stays under the PKI root outside the repository. The receiver logs
fingerprints of request credentials, never their values.
"""

import argparse
import hashlib
import json
import select
import ssl
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, override
from urllib.parse import parse_qs, urlsplit

type LeafSpec = tuple[str, tuple[str, ...], tuple[str, str] | None]
type Record = dict[str, Any]

GOOD_SANS = ("host.docker.internal", "localhost")
LEAVES: dict[str, LeafSpec] = {
    "valid": ("ca", GOOD_SANS, None),
    "hdi-only": ("ca", ("host.docker.internal",), None),
    "localhost-only": ("ca", ("localhost",), None),
    "wrong-host": ("ca", ("wrong.bv05.invalid",), None),
    "expired": ("ca", GOOD_SANS, ("20260101000000Z", "20260102000000Z")),
    "unrelated": ("unrelated-ca", GOOD_SANS, None),
}
KIT_CA_NAME = "bv05-ca.crt"
LOG_LOCK = threading.Lock()


def openssl(*args: str) -> None:
    """Run openssl with argv and fail on a nonzero exit."""
    subprocess.run(["openssl", *args], check=True, capture_output=True)


def fingerprint(path: Path) -> str:
    """Return the SHA-256 fingerprint of a PEM certificate."""
    out = subprocess.run(
        ["openssl", "x509", "-in", str(path), "-noout", "-fingerprint", "-sha256"],
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip().split("=", 1)[1]


def make_ca(root: Path, name: str) -> bool:
    """Create a persistent CA once; return whether this call issued it."""
    crt = root / f"{name}.crt"
    if crt.exists():
        return False
    openssl(
        "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256",
        "-nodes", "-keyout", str(root / f"{name}.key"), "-out", str(crt),
        "-days", "30", "-subj", f"/CN=BV-05 disposable {name}",
        "-addext", "basicConstraints=critical,CA:TRUE",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign",
    )  # fmt: skip
    return True


def make_leaf(root: Path, name: str, spec: LeafSpec) -> None:
    """Issue one leaf; a validity window overrides the default seven days."""
    ca, sans, window = spec
    ext = root / f"{name}.ext"
    alt = ",".join(f"DNS:{s}" for s in sans)
    usage = "clientAuth" if ca == "client-ca" else "serverAuth"
    ext.write_text(f"subjectAltName={alt}\nextendedKeyUsage={usage}\n")
    csr = root / f"{name}.csr"
    openssl(
        "req", "-new", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256",
        "-nodes", "-keyout", str(root / f"{name}.key"), "-out", str(csr),
        "-subj", f"/CN={sans[0]}",
    )  # fmt: skip
    validity = (
        ["-not_before", window[0], "-not_after", window[1]]
        if window
        else ["-days", "7"]
    )
    openssl(
        "x509", "-req", "-in", str(csr), "-CA", str(root / f"{ca}.crt"),
        "-CAkey", str(root / f"{ca}.key"), "-set_serial", str(time.time_ns()),
        "-extfile", str(ext), "-out", str(root / f"{name}.crt"), *validity,
    )  # fmt: skip


def cmd_pki(args: argparse.Namespace) -> None:
    """Create or reuse the CAs, issue the leaf set, and write a public manifest."""
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    issued = {ca: make_ca(root, ca) for ca in ("ca", "unrelated-ca", "client-ca")}
    names = list(args.leaf or LEAVES)
    for name in names:
        make_leaf(root, name, LEAVES.get(name, LEAVES["valid"]))
    make_leaf(root, "client", ("client-ca", ("bv05-client",), None))
    manifest_path = root / "manifest.json"
    manifest: Record = (
        json.loads(manifest_path.read_text())
        if manifest_path.exists()
        else {"runs": []}
    )
    manifest["runs"].append(
        {
            "at": datetime.now(tz=UTC).isoformat(),
            "ca_issued": issued,
            "leaves": {n: fingerprint(root / f"{n}.crt") for n in [*names, "client"]},
        }
    )
    manifest["ca"] = {ca: fingerprint(root / f"{ca}.crt") for ca in issued}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest["runs"][-1], indent=2))


def cmd_kit(args: argparse.Namespace) -> None:
    """Write the public-only mixin kit that trusts the disposable CA in the guest."""
    kit = Path(args.kit)
    home = kit / "files" / "home" / "bv05"
    home.mkdir(parents=True, exist_ok=True)
    pem = (Path(args.root) / "ca.crt").read_text()
    if "PRIVATE KEY" in pem:
        sys.exit("refusing: CA file holds a private key")
    (home / KIT_CA_NAME).write_text(pem)
    port = args.port
    (kit / "spec.yaml").write_text(f"""---
schemaVersion: "2"
kind: mixin
name: bv05-kit
version: "0.1.0"
description: BV-05 disposable public-only CA and agentd host route
credentials:
  - service: bv05-agentd
    description: BV-05 fake bearer for a disposable receiver
    required: true
    apiKey:
      name: BV05_TOKEN
      proxyManaged: true
      inject:
        - domain: host.docker.internal
          scheme: bearer
permissions:
  network:
    allow:
      - localhost:{port}
      - host.docker.internal:{port}
setup:
  install:
    - command: >-
        install -m 0644 /home/agent/bv05/{KIT_CA_NAME}
        /usr/local/share/ca-certificates/{KIT_CA_NAME} && update-ca-certificates
      description: Add the disposable public CA to the existing system trust
""")
    print(kit / "spec.yaml")


def log(path: Path, record: Record) -> None:
    """Append one JSON line to the receiver log."""
    record["at"] = datetime.now(tz=UTC).isoformat(timespec="milliseconds")
    with LOG_LOCK, path.open("a") as f:
        f.write(json.dumps(record) + "\n")


def digest(value: str | None) -> str | None:
    """Fingerprint a header value so the log never holds it."""
    return hashlib.sha256(value.encode()).hexdigest()[:16] if value else None


class Handler(BaseHTTPRequestHandler):
    """Receiver handler; TLS runs per connection so failures are logged."""

    @property
    def rx(self) -> Receiver:
        """Return the owning receiver with its concrete type."""
        if not isinstance(self.server, Receiver):
            raise TypeError(self.server)
        return self.server

    @override
    def setup(self) -> None:
        """Wrap the accepted socket and record SNI or the handshake failure."""
        self.sni: str | None = None
        self.ok = False
        tls = self.rx.ctx.wrap_socket(
            self.request, server_side=True, do_handshake_on_connect=False
        )
        self.tls = tls
        tls.settimeout(30)
        try:
            tls.do_handshake()
            self.ok = True
        except (ssl.SSLError, OSError) as exc:
            log(self.rx.log, {"event": "tls_error", "error": str(exc)})
        self.sni = self.rx.sni_seen.pop(id(tls), None)
        self.request = tls
        super().setup()

    @override
    def handle(self) -> None:
        """Skip HTTP when the handshake failed; a TLS 1.3 client rejects on first read."""
        if not self.ok:
            return
        try:
            super().handle()
        except (ssl.SSLError, OSError) as exc:
            log(
                self.rx.log,
                {"event": "tls_read_error", "sni": self.sni, "error": str(exc)},
            )

    @override
    def log_message(self, format: str, *args: object) -> None:
        """Silence the default stderr access log."""

    def base_record(self) -> Record:
        """Collect TLS and header observations without credential values."""
        tls = self.tls
        peer = tls.getpeercert(binary_form=True)
        auth = self.headers.get("Authorization")
        return {
            "method": self.command,
            "path": self.path,
            "sni": self.sni,
            "tls": tls.version(),
            "client_cert_sha256": hashlib.sha256(peer).hexdigest()[:16]
            if peer
            else None,
            "host": self.headers.get("Host"),
            "auth_scheme": auth.split(" ", 1)[0] if auth else None,
            "auth_sha256_16": digest(auth),
            "header_names": sorted(self.headers.keys()),
        }

    def reply(self, code: int, body: Record) -> None:
        """Send a JSON reply."""
        data = (json.dumps(body) + "\n").encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        """Serve whoami and the non-consuming wait."""
        url = urlsplit(self.path)
        record = self.base_record()
        if url.path == "/wait":
            self.wait(record, parse_qs(url.query))
            return
        log(self.rx.log, {"event": "request", **record})
        self.reply(200, record)

    def do_POST(self) -> None:
        """Record one delivery as the positive control for the delivery store."""
        record = self.base_record()
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        with LOG_LOCK, self.rx.deliveries.open("a") as f:
            f.write(json.dumps({"id": hashlib.sha256(body).hexdigest()[:16]}) + "\n")
        log(self.rx.log, {"event": "delivery", **record})
        self.reply(201, {"delivered": True})

    def wait(self, record: Record, query: dict[str, list[str]]) -> None:
        """Hold without consuming anything until the hold ends or the peer leaves."""
        hold = float(query.get("hold", ["30"])[0])
        wid = query.get("id", ["-"])[0]
        start = time.monotonic()
        log(self.rx.log, {"event": "wait_start", "id": wid, "hold": hold, **record})
        reason = "hold_elapsed"
        while time.monotonic() - start < hold:
            readable, _, _ = select.select([self.tls], (), (), 0.25)
            if readable:
                try:
                    gone = self.tls.recv(1) == b""
                except ssl.SSLError, OSError:
                    gone = True
                if gone:
                    reason = "peer_closed"
                    break
        elapsed = round(time.monotonic() - start, 3)
        log(
            self.rx.log,
            {"event": "wait_end", "id": wid, "reason": reason, "elapsed_s": elapsed},
        )
        if reason == "hold_elapsed":
            self.reply(200, {"permit": False, "id": wid, "elapsed_s": elapsed})


class Receiver(ThreadingHTTPServer):
    """Threaded loopback HTTPS receiver with a per-connection handshake."""

    def __init__(self, args: argparse.Namespace) -> None:
        """Load the leaf and optional client CA, then bind loopback only."""
        root = Path(args.root)
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain(root / f"{args.leaf}.crt", root / f"{args.leaf}.key")
        if args.client_ca:
            self.ctx.verify_mode = ssl.CERT_OPTIONAL
            self.ctx.load_verify_locations(root / "client-ca.crt")

        # Keyed by the connection's id() because the callback cannot reach the handler.
        self.sni_seen: dict[int, str | None] = {}

        def on_sni(tls: ssl.SSLObject, name: str, _ctx: ssl.SSLContext) -> None:
            self.sni_seen[id(tls)] = name

        self.ctx.sni_callback = on_sni
        self.log = Path(args.log)
        self.deliveries = Path(args.deliveries)
        self.deliveries.touch()
        super().__init__(("127.0.0.1", args.port), Handler)


def cmd_serve(args: argparse.Namespace) -> None:
    """Run the receiver until interrupted."""
    server = Receiver(args)
    log(
        server.log,
        {
            "event": "listen",
            "port": args.port,
            "leaf": args.leaf,
            "client_ca": args.client_ca,
        },
    )
    print(f"listening 127.0.0.1:{args.port} leaf={args.leaf}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.socket.close()


def main() -> None:
    """Parse the subcommand and run it."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True)
    pki = sub.add_parser("pki")
    pki.add_argument("--root", required=True)
    pki.add_argument(
        "--leaf",
        action="append",
        help="issue only these leaves; unknown names reuse valid SANs",
    )
    pki.set_defaults(func=cmd_pki)
    kit = sub.add_parser("kit")
    kit.add_argument("--root", required=True)
    kit.add_argument("--kit", required=True)
    kit.add_argument("--port", type=int, default=18443)
    kit.set_defaults(func=cmd_kit)
    serve = sub.add_parser("serve")
    serve.add_argument("--root", required=True)
    serve.add_argument("--leaf", default="valid")
    serve.add_argument("--port", type=int, default=18443)
    serve.add_argument("--log", required=True)
    serve.add_argument("--deliveries", required=True)
    serve.add_argument("--client-ca", action="store_true")
    serve.set_defaults(func=cmd_serve)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
