#!/usr/bin/env python3
"""
Tester for mini_serv — Exam Rank 06
Usage: python3 tester.py [./mini_serv]
"""

import socket, subprocess, time, sys, os

G = '\033[92m'; R = '\033[91m'; Y = '\033[93m'
C = '\033[96m'; B = '\033[1m';  X = '\033[0m'

BIN = sys.argv[1] if len(sys.argv) > 1 else './mini_serv'


# ── Infrastructure ────────────────────────────────────────────────

class Server:
    def __init__(self, port):
        self.proc = subprocess.Popen(
            [BIN, str(port)],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE
        )
        time.sleep(0.15)

    def kill(self):
        if self.proc.poll() is None:
            self.proc.kill(); self.proc.wait()

    def __enter__(self): return self
    def __exit__(self, *_): self.kill()


class Client:
    def __init__(self, port):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect(('127.0.0.1', port))
        time.sleep(0.05)

    def send(self, msg):
        self.s.sendall(msg.encode() if isinstance(msg, str) else msg)

    def recv(self, t=0.4):
        buf = b''
        self.s.settimeout(t)
        try:
            while True:
                chunk = self.s.recv(4096)
                if not chunk: break
                buf += chunk
        except (socket.timeout, OSError):
            pass
        return buf.decode(errors='replace')

    def drain(self):
        self.recv(0.15)
        return self

    def close(self):
        try: self.s.close()
        except OSError: pass


def ok():           return True,  ''
def fail(msg):      return False, msg
def eq(got, want, lbl=''):
    if got == want: return True, ''
    return False, f'{lbl}\n      want: {repr(want)}\n       got:  {repr(got)}'
def has(got, want, lbl=''):
    if want in got: return True, ''
    return False, f'{lbl}: {repr(want)}\n  not in: {repr(got)}'


# ── Test registry ─────────────────────────────────────────────────

TESTS = []
def test(name, cat):
    def deco(fn): TESTS.append((cat, name, fn)); return fn
    return deco


# ══════════════════════════════════════════════════════════════════
# ARGUMENTS
# ══════════════════════════════════════════════════════════════════

@test('No args → "Wrong number of arguments\\n" on stderr', 'Arguments')
def _(p):
    r = subprocess.run([BIN], capture_output=True)
    return eq(r.stderr.decode(), 'Wrong number of arguments\n')

@test('No args → exit code 1', 'Arguments')
def _(p):
    r = subprocess.run([BIN], capture_output=True)
    return eq(r.returncode, 1, 'exit code')

@test('Extra arg → "Wrong number of arguments\\n" on stderr', 'Arguments')
def _(p):
    r = subprocess.run([BIN, str(p), 'extra'], capture_output=True)
    return eq(r.stderr.decode(), 'Wrong number of arguments\n')

@test('Extra arg → exit code 1', 'Arguments')
def _(p):
    r = subprocess.run([BIN, str(p), 'extra'], capture_output=True)
    return eq(r.returncode, 1, 'exit code')


# ══════════════════════════════════════════════════════════════════
# ARRIVAL
# ══════════════════════════════════════════════════════════════════

@test('First client receives nothing on connect', 'Arrival')
def _(p):
    with Server(p):
        c = Client(p)
        got = c.recv(0.2)
        c.close()
    return eq(got, '')

@test('Client 1 arrival notifies client 0', 'Arrival')
def _(p):
    with Server(p):
        c0 = Client(p); c0.drain()
        c1 = Client(p); time.sleep(0.1)
        got = c0.recv()
        c0.close(); c1.close()
    return eq(got, 'server: client 1 just arrived\n')

@test('Arriving client does NOT receive own arrival', 'Arrival')
def _(p):
    with Server(p):
        c0 = Client(p)
        c1 = Client(p); time.sleep(0.1)
        got = c1.recv(0.2)
        c0.close(); c1.close()
    return eq(got, '')

@test('Client 2 arrival: both c0 and c1 notified', 'Arrival')
def _(p):
    with Server(p):
        c0 = Client(p); c1 = Client(p)
        c0.drain(); c1.drain()
        c2 = Client(p); time.sleep(0.1)
        g0 = c0.recv(); g1 = c1.recv()
        c0.close(); c1.close(); c2.close()
    want = 'server: client 2 just arrived\n'
    for g, l in [(g0, 'c0'), (g1, 'c1')]:
        r, d = eq(g, want, l)
        if not r: return r, d
    return ok()

@test('Client IDs are sequential: 0, 1, 2', 'Arrival')
def _(p):
    with Server(p):
        c0 = Client(p); c0.drain()
        c1 = Client(p); time.sleep(0.05); m1 = c0.recv()
        c2 = Client(p); time.sleep(0.05); m2 = c0.recv()
        c0.close(); c1.close(); c2.close()
    r1, d1 = eq(m1, 'server: client 1 just arrived\n', 'id=1')
    r2, d2 = eq(m2, 'server: client 2 just arrived\n', 'id=2')
    if not r1: return r1, d1
    return r2, d2

@test('IDs never reset after a disconnect', 'Arrival')
def _(p):
    with Server(p):
        c0 = Client(p); c0.close(); time.sleep(0.1)   # id 0 gone
        c1 = Client(p); c1.drain()                     # id 1
        c2 = Client(p); time.sleep(0.1)                # id 2
        got = c1.recv()
        c1.close(); c2.close()
    return eq(got, 'server: client 2 just arrived\n')


# ══════════════════════════════════════════════════════════════════
# MESSAGE FORWARDING
# ══════════════════════════════════════════════════════════════════

@test('Message forwarded to other client', 'Forwarding')
def _(p):
    with Server(p):
        c0 = Client(p); c1 = Client(p); c0.drain()
        c0.send('hello\n'); time.sleep(0.1)
        got = c1.recv()
        c0.close(); c1.close()
    return eq(got, 'client 0: hello\n')

@test('Sender does NOT receive own message', 'Forwarding')
def _(p):
    with Server(p):
        c0 = Client(p); c1 = Client(p); c0.drain()
        c0.send('echo?\n'); time.sleep(0.1)
        got = c0.recv(0.2)
        c0.close(); c1.close()
    return eq(got, '')

@test('Multi-line single send: each line gets prefix', 'Forwarding')
def _(p):
    with Server(p):
        c0 = Client(p); c1 = Client(p); c0.drain()
        c0.send('a\nb\nc\n'); time.sleep(0.1)
        got = c1.recv()
        c0.close(); c1.close()
    return eq(got, 'client 0: a\nclient 0: b\nclient 0: c\n')

@test('No \\n → nothing forwarded (buffered)', 'Forwarding')
def _(p):
    with Server(p):
        c0 = Client(p); c1 = Client(p); c0.drain()
        c0.send('no newline here'); time.sleep(0.2)
        got = c1.recv(0.2)
        c0.close(); c1.close()
    return eq(got, '')

@test('Partial sends join into one message on \\n', 'Forwarding')
def _(p):
    with Server(p):
        c0 = Client(p); c1 = Client(p); c0.drain()
        c0.send('hel'); time.sleep(0.1)
        c0.send('lo w'); time.sleep(0.1)
        c0.send('orld\n'); time.sleep(0.1)
        got = c1.recv()
        c0.close(); c1.close()
    return eq(got, 'client 0: hello world\n')

@test('Broadcast: 3 receivers all get message', 'Forwarding')
def _(p):
    with Server(p):
        c0=Client(p); c1=Client(p); c2=Client(p); c3=Client(p)
        for c in [c0,c1,c2,c3]: c.drain()
        c0.send('broadcast\n'); time.sleep(0.15)
        gs = [c1.recv(), c2.recv(), c3.recv()]
        for c in [c0,c1,c2,c3]: c.close()
    for g, l in zip(gs, ['c1','c2','c3']):
        r, d = eq(g, 'client 0: broadcast\n', l)
        if not r: return r, d
    return ok()

@test('Middle client sends: others receive, sender does not', 'Forwarding')
def _(p):
    with Server(p):
        c0=Client(p); c1=Client(p); c2=Client(p)
        for c in [c0,c1,c2]: c.drain()
        c1.send('mid\n'); time.sleep(0.1)
        g0=c0.recv(); g2=c2.recv(); g1=c1.recv(0.2)
        for c in [c0,c1,c2]: c.close()
    for g, want, l in [(g0,'client 1: mid\n','c0 recv'),
                       (g2,'client 1: mid\n','c2 recv'),
                       (g1,'','c1 no echo')]:
        r, d = eq(g, want, l)
        if not r: return r, d
    return ok()

@test('Empty line (just \\n) forwarded with prefix', 'Forwarding')
def _(p):
    with Server(p):
        c0 = Client(p); c1 = Client(p); c0.drain()
        c0.send('\n'); time.sleep(0.1)
        got = c1.recv()
        c0.close(); c1.close()
    return eq(got, 'client 0: \n')

@test('Large message >3000 bytes arrives intact', 'Forwarding')
def _(p):
    with Server(p):
        c0 = Client(p); c1 = Client(p); c0.drain()
        payload = 'X' * 3000 + '\n'
        c0.send(payload); time.sleep(0.4)
        got = c1.recv(0.6)
        c0.close(); c1.close()
    return eq(got, 'client 0: ' + 'X' * 3000 + '\n')

@test('50 sequential messages all received in order', 'Forwarding')
def _(p):
    with Server(p):
        c0 = Client(p); c1 = Client(p); c0.drain()
        for i in range(50): c0.send(f'msg{i}\n')
        time.sleep(0.5)
        got = c1.recv(0.6)
        c0.close(); c1.close()
    want = ''.join(f'client 0: msg{i}\n' for i in range(50))
    return eq(got, want)

@test('Two-way exchange (ping-pong)', 'Forwarding')
def _(p):
    with Server(p):
        c0 = Client(p); c1 = Client(p); c0.drain()
        c0.send('ping\n'); time.sleep(0.1); c1.drain()
        c1.send('pong\n'); time.sleep(0.1)
        got = c0.recv()
        c0.close(); c1.close()
    return eq(got, 'client 1: pong\n')

@test('Special printable chars forwarded correctly', 'Forwarding')
def _(p):
    with Server(p):
        c0 = Client(p); c1 = Client(p); c0.drain()
        msg = '!@#$%^&*()_+-={}|;<>?\n'
        c0.send(msg); time.sleep(0.1)
        got = c1.recv()
        c0.close(); c1.close()
    return eq(got, 'client 0: ' + msg)

@test('10 lines in one send: all prefixed correctly', 'Forwarding')
def _(p):
    with Server(p):
        c0 = Client(p); c1 = Client(p); c0.drain()
        c0.send(''.join(f'line{i}\n' for i in range(10)))
        time.sleep(0.2)
        got = c1.recv()
        c0.close(); c1.close()
    want = ''.join(f'client 0: line{i}\n' for i in range(10))
    return eq(got, want)

@test('Buffered msg not lost when a peer departs', 'Forwarding')
def _(p):
    with Server(p):
        c0=Client(p); c1=Client(p); c2=Client(p)
        for c in [c0,c1,c2]: c.drain()
        c0.send('partial')          # no \n — stays buffered
        time.sleep(0.1)
        c1.close()                  # c1 leaves while c0 has buffered data
        time.sleep(0.1)
        c2.drain()                  # drain c1 departure notice
        c0.send(' complete\n')      # finish the message
        time.sleep(0.1)
        got = c2.recv()
        c0.close(); c2.close()
    return eq(got, 'client 0: partial complete\n')


# ══════════════════════════════════════════════════════════════════
# DEPARTURE
# ══════════════════════════════════════════════════════════════════

@test('Departure message sent to remaining client', 'Departure')
def _(p):
    with Server(p):
        c0=Client(p); c1=Client(p)
        c0.drain(); c1.drain()
        c0.close(); time.sleep(0.15)
        got = c1.recv()
        c1.close()
    return eq(got, 'server: client 0 just left\n')

@test('Departure message contains correct client ID', 'Departure')
def _(p):
    with Server(p):
        c0=Client(p); c1=Client(p); c2=Client(p)
        for c in [c0,c1,c2]: c.drain()
        c1.close(); time.sleep(0.15)   # c1 leaves, not c0
        g0=c0.recv(); g2=c2.recv()
        c0.close(); c2.close()
    want = 'server: client 1 just left\n'
    for g, l in [(g0,'c0'), (g2,'c2')]:
        r, d = eq(g, want, l)
        if not r: return r, d
    return ok()

@test('ALL remaining clients notified of departure', 'Departure')
def _(p):
    with Server(p):
        c0=Client(p); c1=Client(p); c2=Client(p); c3=Client(p)
        for c in [c0,c1,c2,c3]: c.drain()
        c0.close(); time.sleep(0.15)
        gs = [c1.recv(), c2.recv(), c3.recv()]
        for c in [c1,c2,c3]: c.close()
    for g, l in zip(gs, ['c1','c2','c3']):
        r, d = eq(g, 'server: client 0 just left\n', l)
        if not r: return r, d
    return ok()

@test('Server keeps working after a client departs', 'Departure')
def _(p):
    with Server(p):
        c0=Client(p); c1=Client(p); c2=Client(p)
        for c in [c0,c1,c2]: c.drain()
        c0.close(); time.sleep(0.1)
        c1.drain(); c2.drain()
        c1.send('still works\n'); time.sleep(0.1)
        got = c2.recv()
        c1.close(); c2.close()
    return eq(got, 'client 1: still works\n')

@test('Solo client sending to nobody: no crash, no echo', 'Departure')
def _(p):
    with Server(p):
        c0 = Client(p); c0.drain()
        c0.send('alone\n'); time.sleep(0.1)
        got = c0.recv(0.2)
        c0.close()
    return eq(got, '')

@test('After all depart, new client gets id N (not reset)', 'Departure')
def _(p):
    with Server(p):
        c0=Client(p); c1=Client(p)
        c0.drain(); c1.drain()
        c0.close(); c1.close(); time.sleep(0.1)
        c2=Client(p); c2.drain()  # id=2
        c3=Client(p); time.sleep(0.1)  # id=3
        got = c2.recv()
        c2.close(); c3.close()
    return eq(got, 'server: client 3 just arrived\n')


# ══════════════════════════════════════════════════════════════════
# EDGE CASES
# ══════════════════════════════════════════════════════════════════

@test('8 clients connect+disconnect: server survives', 'Edge Cases')
def _(p):
    with Server(p):
        clients = [Client(p) for _ in range(8)]
        time.sleep(0.4)
        for c in clients: c.drain()
        for c in clients:
            c.close(); time.sleep(0.1)  # let server process each departure
        try:
            probe = Client(p); probe.close()
            return ok()
        except Exception as e:
            return fail(f'server died after mass disconnect: {e}')

@test('Interleaved arrival + messages arrive in order', 'Edge Cases')
def _(p):
    with Server(p):
        c0=Client(p); c1=Client(p)
        c0.drain(); c1.drain()
        c0.send('first\n'); time.sleep(0.05)
        c2 = Client(p);   time.sleep(0.05)
        c0.send('second\n'); time.sleep(0.1)
        got = c1.recv()
        c0.close(); c1.close(); c2.close()
    r1,d1 = has(got, 'client 0: first\n',              'first msg')
    r2,d2 = has(got, 'server: client 2 just arrived\n','arrival')
    r3,d3 = has(got, 'client 0: second\n',             'second msg')
    if not r1: return r1, d1
    if not r2: return r2, d2
    return r3, d3

@test('Multiple rapid reconnects: IDs keep incrementing', 'Edge Cases')
def _(p):
    with Server(p):
        for _ in range(5):
            c = Client(p); c.close(); time.sleep(0.05)
        c5 = Client(p); c5.drain()  # id=5
        c6 = Client(p); time.sleep(0.1)  # id=6
        got = c5.recv()
        c5.close(); c6.close()
    return eq(got, 'server: client 6 just arrived\n')

@test('Message from client 2 while c0,c1 connected', 'Edge Cases')
def _(p):
    with Server(p):
        c0=Client(p); c1=Client(p); c2=Client(p)
        for c in [c0,c1,c2]: c.drain()
        c2.send('from two\n'); time.sleep(0.1)
        g0=c0.recv(); g1=c1.recv(); g2=c2.recv(0.2)
        for c in [c0,c1,c2]: c.close()
    for g, want, l in [(g0,'client 2: from two\n','c0'),
                       (g1,'client 2: from two\n','c1'),
                       (g2,'','c2 no echo')]:
        r, d = eq(g, want, l)
        if not r: return r, d
    return ok()

@test('Very long line split across 5 sends', 'Edge Cases')
def _(p):
    with Server(p):
        c0=Client(p); c1=Client(p); c0.drain()
        chunk = 'Z' * 600
        for _ in range(4): c0.send(chunk); time.sleep(0.05)
        c0.send(chunk + '\n'); time.sleep(0.4)
        got = c1.recv(0.6)
        c0.close(); c1.close()
    want = 'client 0: ' + 'Z' * 3000 + '\n'
    return eq(got, want)

@test('Concurrent bursts from 3 senders, receivers get all', 'Edge Cases')
def _(p):
    with Server(p):
        c0=Client(p); c1=Client(p); c2=Client(p); c3=Client(p)
        for c in [c0,c1,c2,c3]: c.drain()
        c1.send('from1\n')
        c2.send('from2\n')
        c3.send('from3\n')
        time.sleep(0.3)
        got = c0.recv()
        for c in [c0,c1,c2,c3]: c.close()
    r1,d1 = has(got, 'client 1: from1\n', 'msg from c1')
    r2,d2 = has(got, 'client 2: from2\n', 'msg from c2')
    r3,d3 = has(got, 'client 3: from3\n', 'msg from c3')
    if not r1: return r1, d1
    if not r2: return r2, d2
    return r3, d3


# ══════════════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if not os.path.isfile(BIN):
        print(f'{Y}Binary not found: {BIN} — compiling...{X}')
        r = subprocess.run(['cc', '-Wall', '-Wextra', '-Werror', 'mini_serv.c', '-o', BIN])
        if r.returncode != 0:
            print(f'{R}Compilation failed.{X}'); sys.exit(1)
        print(f'{G}Compiled OK.{X}\n')

    print(f'{B}mini_serv tester  →  {BIN}{X}')

    p = n = 0
    port = 4200
    cur_cat = None

    for cat, name, fn in TESTS:
        if cat != cur_cat:
            print(f'\n{C}{B}{cat}{X}')
            cur_cat = cat

        try:
            result, detail = fn(port)
        except Exception as e:
            result, detail = False, f'Exception: {e}'

        port += 1
        time.sleep(0.05)

        if result:
            p += 1
            print(f'  {G}✓{X} {name}')
        else:
            n += 1
            print(f'  {R}✗{X} {name}')
            if detail:
                print(f'    {Y}→ {detail}{X}')

    total = p + n
    col = G if not n else R
    print(f'\n{"─"*54}')
    print(f'  {B}{col}{p}/{total}{X} passed', end='')
    print(f'  {R}({n} failed){X}' if n else f'  {G}All good!{X}')
