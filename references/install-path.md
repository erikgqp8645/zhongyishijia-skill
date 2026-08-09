# Install Path Notes for zhongyishijia-skill

What `git clone` actually gives you, and where the data really lives.

## TL;DR

- `git clone git@github.com:erikgqp8645/zhongyishijia-skill.git` only gives you **code + small JSON metadata** (~3MB total).
- The big data files (`evidence_cards.jsonl` 269MB, `books_json/*.json` 207MB across 689 files, `20120413mssql.sqlite` 711MB) are **NOT in LFS** — they live in **GitHub Releases** as assets:
  - `v1.1-lfs-data` release: `evidence_cards.jsonl` + `books_json.tar.gz`
  - `v1.0-raw-sqlite` release: `20120413mssql.sqlite`
- `git lfs pull` does **NOT** work — LFS is configured in `.gitattributes` but the actual LFS server doesn't serve these files. Following the README's `git lfs install && git lfs pull` step will silently leave you with empty/placeholder files.

## Three install scenarios

### Scenario A — First-time install on a new machine

```bash
# 1. Clone code
git clone git@github.com:erikgqp8645/zhongyishijia-skill.git
cd zhongyishijia-skill

# 2. Download data files from Releases
mkdir -p references/text_distillation references/raw

# 2a. evidence_cards.jsonl (269MB)
curl -L -o references/text_distillation/evidence_cards.jsonl \
  https://github.com/erikgqp8645/zhongyishijia-skill/releases/download/v1.1-lfs-data/evidence_cards.jsonl

# 2b. books_json.tar.gz (75MB)
curl -L -o /tmp/books_json.tar.gz \
  https://github.com/erikgqp8645/zhongyishijia-skill/releases/download/v1.1-lfs-data/books_json.tar.gz
tar -xzf /tmp/books_json.tar.gz -C references/

# 2c. SQLite (711MB)
curl -L -o references/raw/20120413mssql.sqlite \
  https://github.com/erikgqp8645/zhongyishijia-skill/releases/download/v1.0-raw-sqlite/20120413mssql.sqlite

# 3. Install to Hermes
cp -R . ~/.hermes/skills/zhongyishijia-expert-mentor-lineage/
```

**On slow networks**, use `aria2c -x 16 -s 16` instead of `curl` for any of the 100MB+ files — see `proxy-workarounds` / `torrent-download` skills. The release assets are single files (no chunking), so `-x 16 -s 16` will parallelize the connection.

**Common failure modes**:
- `curl ... | tail -N` (SIGPIPE truncation) — download completes "successfully" but file ends in a few KB of NUL bytes. Always verify with `wc -c` against the expected size from the release page.
- Skipping `tar -xzf` and trying to use `books_json.tar.gz` directly — won't work.
- Skipping `mkdir -p references/raw` — the SQLite download will fail with "No such file or directory".

### Scenario B — Already have data on another machine

This is the **fastest** path when the user already has a working install elsewhere:

```bash
# Local install (target)
DST=~/.hermes/skills/zhongyishijia-expert-mentor-lineage

# Code (sync from origin/main)
cd $DST && git fetch origin && git reset --hard origin/main

# Data (rsync from a known-good source)
rsync -avP user@other-machine:$DST/references/text_distillation/evidence_cards.jsonl \
                    $DST/references/text_distillation/

rsync -avP user@other-machine:$DST/references/books_json/ \
                    $DST/references/books_json/

rsync -avP user@other-machine:$DST/references/raw/20120413mssql.sqlite \
                    $DST/references/raw/
```

Or if the user has a local copy in `/tmp/...` or similar:
```bash
cp -v /path/to/evidence_cards.jsonl $DST/references/text_distillation/
cp -R /path/to/books_json $DST/references/
cp -v /path/to/20120413mssql.sqlite $DST/references/raw/
```

Total ~1.2GB, completes in seconds locally.

### Scenario C — Just syncing code, data already correct

```bash
cd ~/.hermes/skills/zhongyishijia-expert-mentor-lineage
git fetch origin
git status               # check what diverged
git reset --hard origin/main   # discard local changes to code (NOT data)
```

## Pitfalls

- **The README is partly wrong.** It tells you to `git lfs pull` for the data files. This command will silently fail or no-op. The data is in Releases, not LFS. Always check `gh release list -R erikgqp8645/zhongyishijia-skill` or the Releases page before assuming LFS works.
- **Don't `git pull` blindly if data is staged as a `git status` "deleted" entry.** If you copied real data files over LFS placeholder files, git's working tree will report `deleted: evidence_cards.jsonl` because the LFS pointer file got replaced. `git reset --hard` would re-fetch the placeholder and DELETE your real data. Either `git stash` the data first, or commit the real data first (`git add -A && git commit -m "data: replace LFS placeholders with real files"`), or just don't run reset on the data files.
- **Verify `evidence_cards.jsonl` row count after download:** expect 317,580. If you see 41,745 or some other short number, the file was truncated — re-download with `aria2c -c --check-integrity=true` or via `curl` with `-C -`.
- **Verify `books_json/` file count:** expect 689. If the directory is empty or has only a few files, the tarball extraction failed or wasn't run.
- **SQLite SHA256** should be `6fa194c9a4177dfdd483c8fd7aa37a9e24e371d0692a85a338777bb6e9aee26f` (per the upstream README). Verify after download.