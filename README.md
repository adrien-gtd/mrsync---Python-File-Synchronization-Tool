# mrsync - Python File Synchronization Tool

mrsync is a Python program designed to synchronize files and directories between two locations, inspired by the functionality of the Linux command rsync. It was developed as part of an operating system course. This project includes many of the options available in the rsync command, providing flexibility and functionality for file synchronization tasks.

## Usage
```
mrsync [OPTION]... SRC [SRC]... DEST
mrsync [OPTION]... SRC [SRC]... [USER@]HOST:DEST
mrsync [OPTION]... SRC [SRC]... [USER@]HOST::DEST
mrsync [OPTION]... SRC
mrsync [OPTION]... [USER@]HOST:SRC [DEST]
mrsync [OPTION]... [USER@]HOST::SRC [DEST]
```

## Options
- `--list-only`: List the files instead of copying them.
- `-r`, `--recursive`: Recurse into directories.
- `--size-only`: Skip files that match in size.
- `-I`, `--ignore-times`: Don't skip files that match size and time.
- `--force`: Force deletion of directories even if not empty.
- `--existing`: Skip creating new files on the receiver.
- `--ignore-existing`: Skip updating files that exist on receiver.
- `--times`, `-t`: Preserve permissions.
- `--perms`, `-p`: Preserve times.
- `--delete`: Delete extraneous files from destination directories.
- `-a`, `--archive`: Archive mode; same as `-rpt` (no `-H`).
- `--server`: Shouldn't be used (for SSH in push mode).
- `--pull`: Shouldn't be used (for SSH in pull mode).
- `-v`, `--verbose`: Increase verbosity.
- `-q`, `--quiet`: Suppress non-error messages.
- `--timeout`: Set I/O timeout in seconds.
- `-u`, `--update`: Skip files that are newer on the receiver.
- `-d`, `-dirs`: Transfer directories without recursing.
- `--port`: Specify double-colon alternate port number.

## Update Functionality
The update function aims to optimize file transfer by only sending parts of a file that have changed. It divides the destination file into blocks and computes a hash for each block. The sender compares the hashes of corresponding blocks between source and destination. If they match, no data is sent; otherwise, only the necessary parts are transferred. This approach reduces network traffic for large files while maintaining integrity. Upon completion of the file update, the sender sends a SIGUSR2 signal to inform the generator process of the update's completion.
