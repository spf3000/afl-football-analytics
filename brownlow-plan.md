AFL Brownlow Predictor — Hackathon Build Spec

Goal: Ship a public page that shows predicted Brownlow 3-2-1 votes + a season leaderboard, with a live Stripe paywall on a "premium" tier. Win condition = a stranger can pay on Sunday.

The edge: The data pipeline already exists (scraper → Databricks → dbt → Elo/Monte Carlo). The weekend is spent on the product + payment layer, not plumbing. Don't touch the lakehouse.

Scope (what ships)

- Free: current-round predicted 3-2-1 per game; live predicted leaderboard (top 20).
- Premium ($5–10/mo or $39 season): full leaderboard, per-player vote probability + confidence, "winner odds" from the Monte Carlo sim, round-by-round history.
- One Stripe payment link / Checkout gating the premium view. Even a hardcoded "enter email after pay" is fine for the demo.

Stack (fastest path)

- Data out: export current model predictions to a flat table/CSV/Parquet from Databricks — don't serve live from the warehouse. A nightly/manual dump is enough.
- App: Streamlit (fastest to ship, least product-y) or Next.js (more product-y, more time). Pick Streamlit if you want to be done; Next.js if the demo polish matters more than features.
- Payments: Stripe Payment Link → on success, unlock premium (gate by a passcode emailed on purchase, or Stripe Checkout + a paid flag). Don't build real auth.
- Host: Streamlit Community Cloud / Vercel. Free tier.

Hour budget (~2 days)

- Sat AM: export prediction table; stand up app skeleton + free view (leaderboard + per-game 3-2-1).
- Sat PM: premium view (probabilities, winner odds, history); visual polish (one good chart — reuse your Monte Carlo heatmap style).
- Sun AM: Stripe link + gating; deploy; test a real payment end-to-end.
- Sun PM: landing copy + the launch post (the umpire-troll piece is your content cannon), buffer for breakage.

Hard cuts (do NOT build this weekend)

- Auth/user accounts, SMS alerts, watchlists, betting-edge analysis, live in-game updates, the zone-defence/tracking stuff. All post-hackathon.

Revenue story for judges

"Existing data pipeline → predictions → freemium product, payable today, peaking at the September Brown via shareable analytics content (e.g. the 50m-penalty-is-random piece)."

Stretch (only if ahead)

- Email capture for a weekly "this round's predicted votes" digest → top of funnel.
- The umpire-rule mini-experiment as a launch blog post (not in the app).
