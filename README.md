# Exam Rank 06 — 42 Network

Solution for the 1337 Coding School Exam Rank 06, focused on implementing a non-blocking TCP chat server in C using sockets and I/O multiplexing.

## Subject

| Subject | Description | Tester |
| --- | --- | --- |
| mini\_serv | TCP chat server — multiple clients, message broadcasting, client identification and connection/disconnection handling | tester.py |

## Key Concepts

C

- TCP sockets and network programming
- Socket creation, binding and listening
- I/O multiplexing using `select()`
- Non-blocking I/O
- Managing multiple client connections
- File descriptor management
- Message broadcasting between clients
- Client IDs and connection tracking
- Dynamic memory management
- Error handling and system calls

## Main Requirements

- Create a server listening on `127.0.0.1`.
- Accept multiple clients simultaneously.
- Assign a unique ID to each connected client.
- Notify all clients when someone joins or leaves.
- Broadcast incoming messages to all other connected clients.
- Handle partial messages and newline characters correctly.
- Use `select()` to monitor multiple file descriptors without blocking.

## Disclaimer

Attempt the subject yourself before reading any solution. Understanding socket programming, `select()`, and non-blocking I/O is essential to passing this exam.

The exam gives you the same subject repeatedly until you pass or time runs out.
