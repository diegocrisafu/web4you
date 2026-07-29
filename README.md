# web4you

Websites for Montreal workshops and small trades. This repo holds the pitch page,
a client demo, and the outreach tooling.

```
index.html                  the pitch page — what prospects see
demos/ebenisterie.html      full demo site for a cabinetmaking shop
outreach/                   CSV-driven email sender, CASL-compliant
outreach/PASTABLE.md        the same message, ready to paste into Gmail by hand
.github/workflows/          CI: lints the list on push, sends only on demand
```

---

## Publish it

```bash
git remote add origin https://github.com/diegocrisafu/web4you.git
git push -u origin main
```

Then turn on Pages: **Settings → Pages → Source: Deploy from a branch →
`main` / `(root)` → Save.** Give it a minute and you'll have:

- `https://diegocrisafu.github.io/web4you/`
- `https://diegocrisafu.github.io/web4you/demos/ebenisterie.html`

That second URL is the one you put in emails and open on your phone in the shop.
`.nojekyll` is already in place so Pages serves the files as-is.

---

## What is deliberately not in here

**This repo is public**, because that's what makes Pages serve the demo to a
prospect's phone. So the prospect research stays out of it, via `.gitignore`:

| Ignored | Why |
|---|---|
| `outreach/prospects.csv` | Real business names, phone numbers, and a personal `hook` for each |
| `montreal_prospects.xlsx` | The full tracker, including candid notes on who's a hard sell |
| `outreach/sent_log.csv` | Who you emailed and when |
| `PLAN.md` | Your sequencing and targeting |

`outreach/prospects.example.csv` is committed in their place so the format is
documented and CI has something to lint.

Nobody should be able to google their own shop and find your notes about them.

### Running the sender on GitHub anyway

The workflow rebuilds `prospects.csv` at runtime from a repository secret, so the
list works in Actions without ever being committed:

```bash
gh secret set PROSPECTS_CSV < outreach/prospects.csv
```

Re-run that whenever you edit the list. With no secret set, CI just lints the
example file. The send job writes `sent_log.csv` to a workflow artifact and an
Actions cache — never a commit.

---

## The demo

`demos/ebenisterie.html` is a working site for **Atelier Rivard**, a fictional
cabinetmaker. Fictional on purpose: a demo ribbon runs across the top and the
footer says so, which is both honest and a better sales posture — you're showing
a capability, not implying you already have clients you don't have.

It's built for cabinetmakers because that's the strongest prospect category on the
list: nine shops with between 5 and 48 reviews, kitchen jobs in the five figures,
and reviews that name the owner personally.

The hero is a **measured shop elevation in SVG** — dimension lines, extension
lines, arrows, monospaced callouts, drawn on load. That's the point. An ébéniste
recognises a shop drawing instantly, and it says you understood the trade before
you built the page. A stock photo of a kitchen says the opposite.

Design: finished-walnut ground (`#241A15`), pale maple text, diazo-blueprint blue
(`#4E93C4`) for anything measured, brass (`#C9A227`) for hardware. Archivo for
display, Newsreader for body, JetBrains Mono restricted to dimensions and specs
where monospace is what a real drawing uses. French-first copy, since most of
these shops run in French.

### Reskinning it for a real prospect

Roughly three hours:

1. Copy to `demos/<shopname>.html`
2. Swap name, address, phone, hours from their Google listing
3. Replace the three project cards with their actual work
4. Pull one real sentence from their reviews into the testimonial
5. Adjust the SVG drawing's dimension text to something they actually build
6. **Delete the demo ribbon and the fictional-company footer**

The wood swatches are CSS gradients, not images, so there's nothing to source
until they hand you real photos.

### Other categories

Same structure, different signature element:

- **Cobbler** — before/after sole comparison; leather-and-oxblood palette
- **Upholsterer** — fabric swatch grid, since choosing fabric *is* the process
- **Caterer** — menu with per-head pricing and a headcount calculator
- **Watchmaker** — exploded movement diagram; the SVG approach transfers directly

---

## Outreach

See `outreach/README.md`. Two things worth knowing before you open it:

**CASL is not CAN-SPAM.** Canada requires consent *before* you send, with
penalties up to $1M for an individual. There's a real exemption for
conspicuously-published business addresses that likely covers this, but the burden
of proving consent sits with you. The sender refuses to email any row where you
haven't recorded where the address came from.

**You have no email addresses.** Google Places returns phone numbers. More to the
point, a 60-year-old ébéniste with eleven reviews doesn't read email. The script
earns its keep as a *follow-up* tool after you've walked in — not for discovery.
Discovery is the walk-in.

```bash
cd outreach
python validate.py                  # lint the list
python send.py                      # preview, sends nothing
python send.py --send --limit 3     # live, asks you to type SEND
```

---

## Order of operations

1. Push, enable Pages, confirm both URLs load on your phone
2. Reskin the demo for one specific shop from the prospect list
3. Walk in with it on your phone

Step 3 is the one that produces a client. The rest is preparation for step 3.
Email is the follow-up that evening, not the opener — see `outreach/PASTABLE.md`.
