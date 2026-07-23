# Lead Digest

A small pipeline that watches podcasts, newsletters, and local papers you
choose, and emails you a daily digest of potential story leads — modeled on
the New York Times' internal "Manosphere Report."

**How it works:**
1. Every 3 hours, it checks each source's RSS feed for new episodes/posts.
2. New podcast episodes get transcribed (AssemblyAI); newsletter/paper posts
   get their article text extracted.
3. Each new item is run past Claude with your "beat" description — if it
   contains something worth flagging, it's saved as a lead.
4. Once a day, it gathers everything flagged since the last digest, asks
   Claude to spot patterns across sources, and emails you the result.

Nothing here publishes anything automatically — it's a tip line for you,
same as the Times' tool is for their reporters. Always go back to the
original source before reporting anything out.

## Running it locally in Cursor (test before you deploy)

You don't need GitHub Actions to try this out — run it straight from
Cursor's terminal first. That's the fastest way to see real output and
tune your `beat` description before scheduling anything.

1. **Open the folder in Cursor**: `File → Open Folder` → select this
   unzipped `lead-digest` folder.

2. **Create a virtual environment and install dependencies**, in
   Cursor's built-in terminal (`` Ctrl+` `` / `` Cmd+` ``):
   ```bash
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up your config and secrets**:
   ```bash
   cp config.example.yaml config.yaml
   cp .env.example .env
   ```
   Edit `config.yaml` (your beat + sources) and `.env` (your API keys —
   see "Get API keys" below). Both files are gitignored, so this is safe
   to do even before you've decided on a repo.

4. **Run ingestion**:
   ```bash
   python -m src.run_ingest
   ```
   Watch the terminal output — it prints each item it's processing and
   flags anything it decides is a lead. First run will pull in
   everything from the last 48 hours (see `lookback_hours_first_run` in
   config.yaml); after that it only looks at the last 6 hours, since
   `state.json` now remembers what it's already seen.

5. **Check what landed in the buffer**:
   ```bash
   cat state.json
   ```
   You'll see your leads sitting in the `buffer` array — this is what
   the digest step will turn into an email.

6. **Send yourself a test digest**:
   ```bash
   python -m src.run_digest
   ```
   This builds the digest from whatever's in the buffer, emails it to
   `email.to` in config.yaml, then clears the buffer.

Repeat steps 4–6 as you tune `beat` in config.yaml — that's the fastest
feedback loop for dialing in what counts as a lead. Once you're happy
with the output, move on to "Setup" below to schedule it so you're not
running it by hand.

**A debugging tip for Cursor specifically:** if a step errors out, paste
the traceback into chat and ask Claude/Cursor's assistant to fix it
directly against these files — the error messages from `run_ingest.py`
are printed per-item (`[warn]`/`[error]`) so a single bad source won't
stop the rest from processing, but ask it to trace failures back to the
specific module (`sources.py`, `link_mining.py`, `pdf_extract.py`, etc.)
listed in the print statement.

## Setup (about 15 minutes)

### 1. Get the code into your own repo
Create a **private** GitHub repo and push this folder to it. (Private,
because `config.yaml` will list the sources and beat you're tracking.)

### 2. Configure your sources
```
cp config.example.yaml config.yaml
```
Edit `config.yaml`:
- `beat`: describe what counts as a lead for you. Be specific — this is
  the prompt that decides what gets flagged.
- `sources`: add your podcasts/newsletters/papers as RSS feed URLs.
  - Podcast RSS: check the show's own website, or a lookup tool like
    castos.com/tools/find-podcast-rss-feed
  - Substack newsletters: usually `https://name.substack.com/feed`
  - Local papers: look for `/rss` or `/feed`, often in the site footer
- `email.to`: where the digest should land.

Commit `config.yaml` to your repo.

### 3. Get API keys
- **Anthropic API key** — console.anthropic.com (used for summarizing
  items and building the daily digest)
- **AssemblyAI API key** — assemblyai.com, free tier is enough to start
  (used for podcast transcription)
- **Email sending** — easiest is a Gmail account with an
  [App Password](https://myaccount.google.com/apppasswords) (needs 2FA
  turned on first). SMTP host is `smtp.gmail.com`, port `587`.

### 4. Add secrets to your repo
In your repo: **Settings → Secrets and variables → Actions → New repository
secret**. Add:
- `ANTHROPIC_API_KEY`
- `ASSEMBLYAI_API_KEY`
- `SMTP_HOST` (e.g. `smtp.gmail.com`)
- `SMTP_PORT` (e.g. `587`)
- `SMTP_USER` (your email address)
- `SMTP_PASS` (your app password)

### 5. Turn it on
Go to the **Actions** tab of your repo and enable workflows if prompted.
That's it — `ingest.yml` runs every 3 hours, `digest.yml` runs once a day.

You can also trigger either one manually from the Actions tab
(**Run workflow** button) to test without waiting for the schedule —
worth doing once end-to-end before you trust it.

## Customizing

- **What counts as a lead**: edit `beat` in `config.yaml`. This is the
  highest-leverage thing to tune — start narrow, widen if you're not
  getting enough, narrow further if you're getting too much noise.
  This version's screening prompt and digest layout are built around a
  specific narrative-journalism rubric (a central character, a real
  two-sided conflict, a hidden engine, a "condition" the story
  crystallizes, a magazine-caliber ceiling) — the field names in
  `src/summarize.py` and `src/digest.py` (`central_character`,
  `the_conflict`, `hidden_engine`, `the_condition`, `magazine_fit`)
  reflect that rubric directly. If the beat changes to something with a
  fundamentally different shape (e.g. back to general accountability
  reporting), those field names are worth revisiting too, not just the
  beat text — ask Claude/Cursor to adjust them together next time.
- **Roundup newsletters that link out to source documents** (Court Watch
  is the example, but this pattern shows up elsewhere too): set
  `mine_document_links: true` on that newsletter in `config.yaml`. Instead
  of summarizing the newsletter issue as one blob, the pipeline pulls out
  every linked document (PDFs, mostly), downloads it, extracts its text,
  and runs each one past your beat individually — so a 40-link weekly
  roundup becomes 40 individually-evaluated potential leads instead of one
  vague digest of the newsletter itself. `link_domains` lets you control
  which linked destinations count as "documents" (defaults to
  CourtListener/RECAP, `*.uscourts.gov`, and justice.gov).
  - Court Watch's own RSS feed is `https://rss.beehiiv.com/feeds/BTVqUNjsIO.xml`
    (found via the "RSS FEED" link in their site footer).
  - Most RECAP/CourtListener PDFs extract cleanly since they're built from
    typed PACER filings. A minority are scanned images with no text
    layer and will come back empty — the newsletter blurb still gets
    used as fallback context in that case, just without the full filing.
- **How often it checks sources**: edit the cron schedule in
  `.github/workflows/ingest.yml`.
- **What time the email arrives**: edit the cron schedule in
  `.github/workflows/digest.yml` (currently 12:00 UTC ≈ 8am ET; see the
  comment in that file re: daylight saving).
- **Model choice**: `src/summarize.py` and `src/digest.py` both use
  Claude Sonnet. The per-item screening step was bumped up from Haiku to
  Sonnet because this rubric calls for real editorial judgment (spotting
  an obsessive character, a hidden engine, a magazine-caliber angle),
  not just topic matching — and the volume here is modest enough that
  the cost difference is negligible. If you add enough high-volume
  sources that cost becomes real, consider a cheap Haiku pre-filter pass
  that only promotes borderline items to the full Sonnet screening.

## Setting this up for someone else

If you're building this for another person — a journalist who isn't
going to touch code — the goal is that their entire interaction with
this tool is opening an email. Everything technical stays on your side:

- **Use your own accounts for everything.** Your GitHub account owns the
  repo, your Anthropic/AssemblyAI keys pay for the API calls, your email
  account sends the digest. They never need a GitHub login, an API key,
  or Cursor.
- **Get their "beat" from them in plain English**, then translate it
  into the `beat` field yourself. Ask them what kind of stories they're
  chasing and what would make them say "yes, flag that" vs. "that's
  noise" — that conversation is worth more than any config option.
- **Set `email.to` to their address, and use `email.greeting_name` and
  `email.reply_to`** (see `config.example.yaml`) so the digest reads
  like something built for them, and any reply lands with you instead
  of disappearing into a sending account they don't recognize.
- **Add your own address to `email.bcc`.** You'll get a silent copy of
  every digest, so if a source breaks or the lead count drops to zero
  for a few days, you notice before they have to say anything.
- **Failures notify you, not them.** Since it's your GitHub account, any
  workflow that errors out emails GitHub's failure notification to you
  (per your GitHub notification settings), not to their inbox.
- **For ongoing tweaks — adding a source, adjusting the beat, changing
  the send time — you don't need to reopen Cursor.** Once the repo's on
  GitHub, you can edit `config.yaml` (or the cron schedule in
  `.github/workflows/digest.yml`) directly in GitHub's web-based file
  editor and commit from the browser; the next scheduled run just picks
  it up. Cursor is for the initial build and any real debugging, not for
  routine changes.


Small-to-medium volume (a few dozen items/day, mostly text with a
handful of podcast episodes): a few dollars a month between Claude API
usage and AssemblyAI transcription. Transcription is the main cost driver
if you're tracking many long-running podcasts — AssemblyAI bills per
audio hour, so that's the number to watch as you add sources.

A link-mining source like Court Watch adds volume: one weekly issue can
produce 30-40 individual document-screening calls. Since those now run
on Sonnet rather than Haiku (see "Model choice" below), check your
Anthropic usage dashboard after the first week or two to see where you
actually land — it should still be modest at this volume, but "modest"
is worth confirming rather than assuming.

## Known limitations
- **RSS only.** Newsletters without a public RSS feed (e.g. some that
  are email-only with no web archive) aren't supported here — you'd need
  to add an email-parsing step (e.g. a dedicated inbox + IMAP polling).
- **No de-duplication of near-identical leads** across different items
  from the same source in one day — the cross-source pattern step will
  usually note it, but won't merge them.
- **DST drift** on the digest send time, noted above.
# leadgen
