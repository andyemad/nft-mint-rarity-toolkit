#!/usr/bin/env bash
# Install the NFT mint & rarity toolkit skills into a Hermes Agent installation.
#
#   From a clone:      ./install.sh
#   One-liner:         curl -fsSL https://raw.githubusercontent.com/andyemad/nft-mint-rarity-toolkit/main/install.sh | bash
#   Named profile:     ./install.sh --profile work
#   Custom location:   ./install.sh --dest /path/to/skills
#   Preview only:      ./install.sh --dry-run
#
# Existing skills with the same name are backed up to <name>.bak-<timestamp>
# rather than overwritten, unless --force is given.
set -euo pipefail

REPO_SLUG="andyemad/nft-mint-rarity-toolkit"
BRANCH="${TOOLKIT_BRANCH:-main}"
RAW_BASE="https://raw.githubusercontent.com/${REPO_SLUG}/${BRANCH}"

PROFILE=""
DEST=""
FORCE=0
DRY=0
SRC=""

while [ $# -gt 0 ]; do
  case "$1" in
    --profile) PROFILE="${2:?--profile needs a name}"; shift 2 ;;
    --dest)    DEST="${2:?--dest needs a path}"; shift 2 ;;
    --force)   FORCE=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

# ---- locate the skills to install ------------------------------------------
script_dir=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

if [ -n "$script_dir" ] && [ -d "$script_dir/skills" ]; then
  SRC="$script_dir/skills"
else
  echo "==> fetching toolkit (no local clone found)"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  # Prefer git (gets everything in one shot); fall back to the tarball.
  if command -v git >/dev/null 2>&1; then
    git clone --depth 1 --branch "$BRANCH" "https://github.com/${REPO_SLUG}.git" "$tmp/repo" >/dev/null 2>&1
  fi
  if [ ! -d "$tmp/repo/skills" ]; then
    curl -fsSL "https://codeload.github.com/${REPO_SLUG}/tar.gz/refs/heads/${BRANCH}" \
      | tar -xz -C "$tmp" 2>/dev/null || true
    found="$(find "$tmp" -maxdepth 2 -type d -name skills | head -1)"
    [ -n "$found" ] || { echo "ERROR: could not download the toolkit" >&2; exit 1; }
    SRC="$found"
  else
    SRC="$tmp/repo/skills"
  fi
fi

# ---- resolve the destination ------------------------------------------------
if [ -z "$DEST" ]; then
  if [ -n "$PROFILE" ]; then
    DEST="$HOME/.hermes/profiles/$PROFILE/skills"
  else
    DEST="${HERMES_SKILLS:-$HOME/.hermes/skills}"
  fi
fi

[ -d "$SRC" ] || { echo "ERROR: no skills directory at $SRC" >&2; exit 1; }

count="$(find "$SRC" -name SKILL.md | wc -l | tr -d ' ')"
echo "==> toolkit source : $SRC"
echo "==> destination    : $DEST"
echo "==> skills to install: $count"
[ "$DRY" = "1" ] && { echo "==> dry run, nothing written"; exit 0; }

mkdir -p "$DEST"
stamp="$(date +%Y%m%d-%H%M%S)"
installed=0
backed_up=0

# Each category directory (web3/, business/, ...) maps onto the Hermes skills
# tree, so a skill ends up at <dest>/<category>/<name>/SKILL.md.
while IFS= read -r skill_md; do
  rel="${skill_md#"$SRC"/}"          # e.g. web3/nft-rarity-engine/SKILL.md
  target="$DEST/$rel"
  target_dir="$(dirname "$target")"
  name="$(basename "$target_dir")"

  if [ -d "$target_dir" ] && [ "$FORCE" != "1" ]; then
    src_dir="$(dirname "$skill_md")"
    if diff -rq "$src_dir" "$target_dir" >/dev/null 2>&1; then
      echo "    = $name (already installed, identical)"
      continue
    fi
    echo "    ! $name exists and differs -> backup $name.bak-$stamp"
    mv "$target_dir" "$target_dir.bak-$stamp"
    backed_up=$((backed_up + 1))
  fi

  mkdir -p "$target_dir"
  # copy the skill dir contents, minus junk
  ( cd "$(dirname "$skill_md")" && tar cf - \
      --exclude='.git' --exclude='__pycache__' --exclude='.DS_Store' . ) \
    | ( cd "$target_dir" && tar xf - )
  installed=$((installed + 1))
  echo "    + $name"
done < <(find "$SRC" -name SKILL.md | sort)

echo
echo "==> installed $installed skill(s), backed up $backed_up"
echo "==> activate them:"
echo "      hermes skills list | head"
echo "      hermes chat -s nft-rarity-engine      # preload one skill"
echo "      /reload-skills                        # inside a running session"
echo
echo "Optional toolkit dependency (signing / trading paths):"
echo "      pip install eth-account coincurve pycryptodome"
echo
echo "Keys are never installed by this script. See SECURITY.md for the"
echo "~/.hermes/secrets/ convention."
