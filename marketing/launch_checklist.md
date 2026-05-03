# 🚀 Launch Checklist — VeritasGraph + VeritasReason v0.4.0

Manual posting only. Each row is one human action.

## 0. Pre-flight
- [ ] Tag the release: `git tag v0.4.0 && git push --tags`
- [ ] Draft GitHub Release with the `marketing/post_copy.md` LinkedIn body
- [ ] Confirm `demos/policy-compliance/demo.gif` renders on the README from a
      logged-out browser
- [ ] Run the smoke test one last time:
      `pip install -q dist/veritas_reason-0.4.0-py3-none-any.whl && veritasreason-policy-demo`

## 1. PyPI publish (once you have your token)
- [ ] **TestPyPI first**:
      ```bash
      python -m twine upload --repository testpypi dist/*
      pip install --index-url https://test.pypi.org/simple/ veritas-reason
      veritasreason-policy-demo   # must print "All four SoD rules fired"
      ```
- [ ] **Real PyPI**:
      ```bash
      python -m twine upload dist/*
      ```
- [ ] Verify install from a fresh machine: `pip install veritas-reason`

## 2. Social (manual paste — do not automate logged-in browsers)
- [ ] X / Twitter — copy from `marketing/post_copy.md` § *X / Twitter*
- [ ] LinkedIn — copy from `marketing/post_copy.md` § *LinkedIn*
- [ ] Reddit r/LocalLLaMA — § *Reddit*
- [ ] Reddit r/MachineLearning *Show* thread — same body
- [ ] Hacker News *Show HN* — § *Hacker News*
- [ ] Dev.to article — expand § *Dev.to / Medium* hook into 800-1200 words
- [ ] Discord communities (LangChain, Ollama, LlamaIndex) — short version

## 3. Programmatic posting (optional, ToS-compliant only)
If you want to actually script this, use the **official developer APIs** with
**your own application credentials** — not a browser-driver against your
personal logged-in profile.
- X API v2 — https://developer.x.com  (requires an approved project)
- LinkedIn Marketing API — https://learn.microsoft.com/linkedin/marketing/
- Reddit script-app OAuth — https://www.reddit.com/prefs/apps

We deliberately do **not** ship a Playwright/Puppeteer poster in this repo,
because driving a logged-in human profile to post at scale violates every
major platform's Terms of Service and gets accounts permanently banned.
