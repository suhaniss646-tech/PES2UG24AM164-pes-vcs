# PES-VCS Lab Report

**Name:** Suhani SS
**SRN:** PES2UG24AM164
**Platform:** Ubuntu 24.04

---

## Build Instructions

```bash
sudo apt update && sudo apt install -y gcc build-essential libssl-dev
export PES_AUTHOR="SUHANI SS <PES2UG24AM164>"
make all
```

---

## Phase 1 — Object Storage Foundation

Files modified: `object.c`

In this phase, the object storage system is implemented.

`object_write` constructs a header in the format `"<type> <size>\0"` and attaches it to the file data. The complete buffer is then hashed using SHA-256. If an object with the same hash already exists, it avoids rewriting it, ensuring deduplication. The object is stored inside a hashed directory structure, and writing is done using a temporary file followed by `fsync` and `rename` to guarantee atomicity.

`object_read` loads the stored object and validates its integrity by recomputing the SHA-256 hash. It extracts the object type and size from the header, checks correctness, and returns only the data portion.




---

## Phase 2 — Tree Objects

Files modified: `tree.c`, `Makefile`

This phase focuses on building tree structures from the index.

`tree_from_index` dynamically allocates memory for the index (to avoid stack overflow), loads all entries, sorts them by path, and passes them to a recursive helper function.

`write_tree_level` processes entries directory-wise. Files are directly converted into blob entries, while directories are grouped and handled recursively to generate subtree hashes. Each directory is represented using mode `040000`. Finally, the tree is serialized and stored in the object database.


---

## Phase 3 — The Index (Staging Area)

Files modified: `index.c`

This phase implements the staging area functionality.

`index_load` opens `.pes/index` in read mode and parses each line using `fscanf`. If the file does not exist, it simply treats it as an empty index.

`index_save` creates a sorted copy of entries in heap memory, writes them into a temporary file, ensures durability using `fflush` and `fsync`, and then atomically renames it.

`index_add` reads file content, stores it as a blob object, collects metadata such as size and modification time, updates or inserts the entry, and finally saves the index.



---

## Phase 4 — Commits and History

Files modified: `commit.c`

This phase introduces commit functionality.

`commit_create` first generates a tree from the current index. It then reads the current HEAD to identify the parent commit if it exists. A commit structure is prepared containing the author, timestamp, and commit message. This structure is serialized and stored using `object_write`. Finally, `head_update` is called to move the branch pointer to the new commit.





### Final — `make test-integration`

![Integration test part 1](images/final_a.png)

![Integration test part 2](images/final_b.png)

---

## Phase 5 — Branching and Checkout

### Q5.1 — How would you implement `pes checkout <branch>`?

A branch is represented as a file in `.pes/refs/heads/` containing a commit hash.

**Changes required:**

1. Update `.pes/HEAD` to point to the target branch
2. Create branch file if it does not exist

**Working directory update:**

* Read commit hash of target branch
* Load its tree
* Recreate files and directories
* Remove files not present in target tree

**Challenges:**

* Prevent overwriting modified files
* Handle untracked file conflicts
* Maintain consistency during updates

---

### Q5.2 — Detecting dirty working directory conflicts

To detect changes:

* Compare file metadata (mtime, size) with index
* If mismatch → recompute hash
* If hash differs → file is modified

Checkout must stop if a modified file conflicts with target branch.

---

### Q5.3 — Detached HEAD and recovery

Detached HEAD occurs when HEAD directly stores a commit hash.

* New commits are created but not linked to any branch
* These commits may become unreachable

**Recovery:**

* Create a new branch pointing to that commit
* Restore HEAD to that branch

---

## Phase 6 — Garbage Collection

### Q6.1 — Finding unreachable objects

Garbage collection uses a mark-and-sweep method.

**Mark phase:**

* Start from all branch references
* Traverse commit → tree → blob
* Store reachable hashes

**Sweep phase:**

* Traverse `.pes/objects`
* Delete objects not marked as reachable

A hash set is used for efficient lookup.

---

### Q6.2 — Race condition between GC and commit

If GC runs during commit:

* Newly created objects may not yet be referenced
* GC may delete them mistakenly
* This leads to corrupted commits

**Prevention:**

* Grace period for new objects
* Temporary references
* Safe ordering of operations

---

# End of Report

