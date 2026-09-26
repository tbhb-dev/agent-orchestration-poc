#!/usr/bin/env python3
"""Experimental observer for the installed Codex daemon; never starts a turn.

The socket grants control authority. This client only sends initialize, list,
read and (when requested) resume. Resume can load an inactive thread, so only
threads already returned by thread/loaded/list are accepted.
"""
import argparse
import json
import queue
import socket
import subprocess
from websockets.sync.client import unix_connect, connect
from websockets.exceptions import ConnectionClosed
import threading
import time
from pathlib import Path


class Client:
    def __init__(self, via_proxy=False):
        self.proxy = None
        if via_proxy:
            parent, child = socket.socketpair()
            self.proxy = subprocess.Popen(["codex", "app-server", "proxy"], stdin=child, stdout=child, stderr=subprocess.DEVNULL)
            child.close()
            self.ws = connect("ws://localhost", sock=parent)
        else:
            self.ws = unix_connect(str(Path.home()/".codex/app-server-control/app-server-control.sock"))
        self.inbox = queue.Queue()
        self.serial = 0
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        try:
            for line in self.ws:
                self.inbox.put((time.time(), json.loads(line)))
        except ConnectionClosed:
            pass
        finally:
            self.inbox.put((time.time(), {"proxyEOF": True}))

    def send(self, method, params, request=True):
        self.serial += 1
        msg = {"method": method, "params": params}
        if request:
            msg["id"] = self.serial
        self.ws.send(json.dumps(msg))
        return self.serial

    def call(self, method, params):
        ident = self.send(method, params)
        pending = []
        deadline = time.monotonic() + 30
        while True:
            stamp, msg = self.inbox.get(timeout=max(.01, deadline-time.monotonic()))
            if msg.get("proxyEOF"):
                raise RuntimeError("WebSocket closed")
            if msg.get("id") == ident:
                for event in pending:
                    self.inbox.put(event)
                return msg
            pending.append((stamp, msg))

    def close(self):
        self.ws.close()
        if self.proxy:
            try:
                self.proxy.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proxy.terminate()
                self.proxy.wait(timeout=3)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--via-proxy", action="store_true")
    ap.add_argument("--cwd", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--thread")
    ap.add_argument("--mode", choices=["list", "read", "resume"], default="list")
    ap.add_argument("--exclude-turns", action="store_true")
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    client = Client(args.via_proxy)
    with args.output.open("w") as out:
        def emit(kind, data, stamp=None):
            out.write(json.dumps({"observed_at": stamp or time.time(), "kind": kind, "data": data})+"\n")
            out.flush()
        try:
            initialized = client.call("initialize", {
                "clientInfo": {"name": "session_stream_probe", "version": "0.1.0"},
                "capabilities": {"experimentalApi": True}})
            emit("initialize", initialized)
            if "error" in initialized:
                raise RuntimeError(initialized["error"])
            client.send("initialized", {}, request=False)
            loaded = []
            cursor = None
            while True:
                response = client.call("thread/loaded/list", {"cursor": cursor})
                if "error" in response:
                    raise RuntimeError(response["error"])
                result = response["result"]
                loaded.extend(result.get("data", []))
                cursor = result.get("nextCursor")
                if not cursor:
                    break
            candidates = []
            for tid in loaded:
                if args.thread and tid != args.thread:
                    continue
                response = client.call("thread/read", {"threadId": tid, "includeTurns": False})
                if "error" in response:
                    raise RuntimeError(response["error"])
                t = response["result"]["thread"]
                if args.thread or t.get("cwd") == args.cwd:
                    candidates.append(t)
                    emit("candidate", {k:t.get(k) for k in ["id", "cwd", "status", "path", "cliVersion", "source"]})
            emit("discovery_summary", {"loaded_count": len(loaded), "matching_count": len(candidates)})
            if args.mode == "list":
                return
            if len(candidates) != 1:
                raise RuntimeError(f"Expected exactly one matching loaded thread, got {len(candidates)}")
            tid = candidates[0]["id"]
            # Keep full protocol content only for this controlled test thread.
            params = {"threadId": tid}
            params.update({"includeTurns": not args.exclude_turns} if args.mode == "read" else {"excludeTurns": args.exclude_turns})
            response = client.call("thread/" + args.mode, params)
            emit(args.mode, response)
            if "error" in response:
                raise RuntimeError(response["error"])
            print("READY", args.mode, tid, flush=True)
            end = time.monotonic()+args.seconds
            while time.monotonic() < end:
                try:
                    stamp, msg = client.inbox.get(timeout=min(.5, max(.01,end-time.monotonic())))
                except queue.Empty:
                    continue
                if msg.get("proxyEOF"):
                    emit("eof", msg, stamp)
                    break
                params = msg.get("params", {})
                # Daemon notifications can cover other sessions; retain only ours.
                event_tid = params.get("threadId") or params.get("conversationId") or params.get("thread", {}).get("id")
                if event_tid == tid:
                    emit("notification", msg, stamp)
        finally:
            client.close()


if __name__ == "__main__":
    main()
