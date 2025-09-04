name: Repo Tools (auto-fix imports + smoke test)

on:
  workflow_dispatch:   # handmatig starten vanuit Actions

permissions:
  contents: write
  pull-requests: write

jobs:
  tools:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install streamlit pandas

      - name: Run auto-fix imports
        run: |
          if [ -f tools/auto_fix_imports.py ]; then
            python tools/auto_fix_imports.py
          else
            echo "tools/auto_fix_imports.py ontbreekt"; exit 1
          fi

      - name: Run smoke test (compile pages)
        run: |
          if [ -f tools/smoke_test.py ]; then
            python tools/smoke_test.py
          else
            echo "tools/smoke_test.py ontbreekt"; exit 1
          fi

      - name: Commit changes (if any)
        id: commit
        run: |
          if [ -n "$(git status --porcelain)" ]; then
            git config user.name  "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
            git add -A
            git commit -m "chore: auto-fix imports + smoke-test adjustments"
            echo "changed=yes" >> "$GITHUB_OUTPUT"
          else
            echo "changed=no" >> "$GITHUB_OUTPUT"
          fi

      - name: Push to branch and open PR
        if: ${{ steps.commit.outputs.changed == 'yes' }}
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
        run: |
          BR="tools/auto-fix-$(date +%Y%m%d-%H%M%S)"
          git push -u origin HEAD:"$BR"
          title="chore: auto-fix imports + smoke-test"
          body="Automatische import-fixes en smoke-test. Controleer en merge."
          data=$(jq -n --arg t "$title" --arg h "$BR" --arg b "main" --arg d "$body" '{title:$t, head:$h, base:$b, body:$d}')
          curl -sS -X POST \
            -H "Authorization: Bearer ${GH_TOKEN}" \
            -H "Accept: application/vnd.github+json" \
            -d "$data" \
            "https://api.github.com/repos/${REPO}/pulls" \
          | jq -r '.html_url // "PR kon niet automatisch worden geopend"'
