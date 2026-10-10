# Round 2, lens R2-A (time-first): four ideas

Brainstormer R2-A, 2026-10-07. Inputs: 01_task.md, 00_baseline.md. Three web searches (LDP + prism /
isochrone / travel time; LDP + dwell / stop / driving cycle; LDP + time-dependent routing) found no LDP
work on prisms, isochrones, dwell-driven or speed-state synthesis; the nearest temporal LDP items (RATR,
"Time will not tell") perturb each released trajectory (judged from snippets). Ids here: R2-A.1 … R2-A.4;
A.x / B.x … are round-1 raw ideas, C1–C10 round-1 candidates.

**Shared public time layer** (S1: OSM + cited constants only, frozen by commit hash before any run).
- Clock: Beijing time (UTC+8). Coarse dayparts AM peak 07–10, PM peak 17–20, off-peak; fine dayparts
  0–6, 6–10, 10–16, 16–20, 20–24.
- Time-dependent (TD) speed v(class, t) = OSM free-flow speed × φ(class, t); φ from a cited Beijing hourly
  congestion profile (Beijing Transport Institute annual report: traffic performance index → speed ratio per
  road class). Cited mode speeds: walk 1.35 m/s, cycle ≈ 4 m/s, bus ≈ 4.5 m/s.
- Likelihoods and destination draws use daypart-static costs; emitted per-segment times propagate through
  the clock with FIFO-consistent TD speeds (Ichoua, Gendreau, Potvin 2003). Times never enter
  `sequence_log_prob`. All four ideas need the timed payload (P1) and the P2 time metrics.
- Noise: SD of a debiased GRR share = sqrt(f(1−f)/n)/(p−q) with f = q + π(p−q), sampling term included,
  n = 91. A gain needs a prior error of about 2 SD.
- Why time first: all users share one clock, so time items have a strong public shape and need few free
  numbers, while spatial items at n ≈ 91 are hopeless; space is then derived from the public graph.

## R2-A.1 Prism-first synthesis: two times decide where a trip can go
1. **Pitch.** A trip starts as two times, its duration T and its prism tightness u = (public TD fastest time
   from its origin to its destination at its departure) / T; the destination is drawn from the iso-time ring
   that u·T defines around a public origin at that departure time, so length, mean speed and per-segment
   times all follow from time plus the public network.
2. **Report.** The device draws one matched trip J uniformly (local coins) and computes T_J (last − first
   timestamp), departure t0, τ_J = TD fastest time O_J → D_J at t0 (daypart-static costs, one Dijkstra on
   the public graph) and u_J = τ_J / T_J. Public classes: T in terciles of the public prior's duration law;
   u in < 0.25 (walk-like or stay-heavy), 0.25–0.6 (bike, bus), > 0.6 (car-like). Value = (T-class,
   u-class): 9 values, 3.2 bits; at ε 8 also the coarse daypart of t0: 27 values, 4.8 bits. GRR at full ε
   (OLH at ε 0.5). No matched trip → public default cell.
3. **Privacy.** The value c is any function of the user's whole period data and local coins; for any users
   V, V' and output y, P(y|V) ≤ max_c P(y|c) ≤ e^ε min_c P(y|c) ≤ e^ε P(y|V'). One report, no ε split,
   no composition; cut points, TD profile and classes are public; everything after is post-processing.
4. **Server.** Debias → simplex projection → shrink to π0 = cell shares of the public prior generator (OSM +
   cited mode mix + TD speeds, no in-trip stays). Synthesis: daypart d (public profile; private at ε 8) →
   cell c ~ π̃(·|d) → origin O by public road mass → D ~ a(x)·k_c(τ_d(O,x)), with k_c the public density of
   u·T inside cell c and a a public attraction mass (exact ring kernel from one forward Dijkstra) → (T, u)
   drawn inside c with u·T = τ_d(O,D) → Boltzmann walk to D with daypart-d TD costs (distance costs for the
   walk-like u-class) → TD segment times from t0, rescaled to sum to T (slack = uniform slowdown; option:
   dwell at public stop nodes as in R2-A.2). Road-valid by P3's construction.
5. **`sequence_log_prob`.** O, D = ends of the route. log P(r) = log Σ_d π_d P(O) Σ_c π̃_{c|d} K_{d,c}(O,D)
   S_{d,ρ(c)}(r) + public floor, where K_{d,c}(O,D) = a(D)k_c(τ_d(O,D)) / Σ_x a(x)k_c(τ_d(O,x)) and S is
   the Boltzmann step product under router ρ(c) ∈ {distance, TD car at d}. Cache by map + config: 3 forward
   Dijkstras per queried origin and 4 reverse per destination, ≈ 7 × 40 ms × 1,100 ≈ 5 min per arm at u182
   (budget 1,200 s), shared by the 17 generators, one code path for members and non-members.
6. **n = 91.** ε 0.5: even a 3-way item is ±0.28 → prior arm. ε 2: 9 cells ±0.08, margins ±0.12; moves only
   if the prior misses a margin by ≥ 0.25, plausible for u (the prior has no in-trip stays and few walks;
   Geolife likely has many). Public fallback, fixed before data by the recovery simulation: 3-way u only
   (±0.07). ε 8: 27 cells, sampling-limited ±0.02 per cell and ±0.05 per margin, i.e. the departure ×
   duration × tightness coupling. n = 10,000: 48 cells (3 dayparts × 4 × 4) by OLH, ±0.009 per cell.
7. **Closest.** Network-time prisms (Miller 1991; Kuijpers & Othman 2009; Kuijpers, Miller, Neutens, Othman
   2010), travel-time budgets (Zahavi 1974; Mokhtarian & Chen 2004), prism-constrained activity simulation
   (PCATS, Kitamura & Fujii 1998): all non-private. LDP: LDPTrace/RetraSyn randomise grid transitions,
   L-SRR/DPMM randomise O/D; none releases only times. vs §4: C2 estimates where trips go (zones) and
   free-flow cost bands, then inverts gravity; R2-A.1 releases no spatial quantity and needs no zones. C1's
   two numbers (length scale, speed ratio) become one joint time item tied by τ = u·T. C3's label is a
   posterior over complete generators; u is a measured, public-referenced ratio that also absorbs in-trip
   stays. C4–C10: no anchors, library, spectral basis, likelihood gain, corridors, tokens or flows.
8. **Risk.** u conflates mode, congestion, detours and in-trip stays; the slack rule decides whether a slow
   trip is a walk or a car with a long stop (mean speed right by construction, segment speeds possibly
   wrong); loops and round trips (O ≈ D) get u ≈ 0 and become short routes with long dwells; Geolife's
   spatial concentration stays prior. Novelty check: the 3-way fallback is close in spirit to C3's label.

## R2-A.2 Clock-sampled speed states: one random second of travel time drives a speed-first embedding
1. **Pitch.** Each user reports the speed state (stopped, walking, slow, fast) at one uniformly random second
   of their recorded travel time, a time-weighted sample whose average is exactly the time-share mix behind
   mean speed; the generator first runs a semi-Markov speed clock and then lays it on the graph with a walk
   whose road classes follow the current state.
2. **Report.** The device concatenates the time intervals of all matched trips, draws U ~ Uniform(0, total
   travel time), smooths speed over ±30 s at that instant and classes it with public thresholds (< 0.5,
   0.5–2.2, 2.2–8, > 8 m/s): 4 values, 2 bits. At ε 8 also the road-class group of the edge being traversed
   (minor, arterial, expressway): 12 values. GRR at full ε; no matched trip → public default.
3. **Privacy.** As R2-A.1: the time-uniform draw only selects the input of one GRR; thresholds are public.
4. **Server.** Debias → time shares π̂_s, shrink to π0 (cited Beijing driving-cycle idle shares, mode mix and
   speeds). Public mean spell durations m_s (signal stop 30–60 s, walking access spells, cruise between
   signals); jump-chain weights ν_s ∝ π̂_s/m_s so that time shares match; public persistence per km.
   Synthesis: departure (public profile), O (public); D from P3's gravity, or, so that reach follows from the
   speed mix, from R2-A.1's ring kernel with τ* = T·ū/v_car(d) (T from the public duration prior, ū =
   Σ_s π̂_s v_s). State path and route are then generated together: at each node the state may switch, the
   next edge is chosen ∝ exp(−β[c(e) + V_D(head e)] + η·compat(class e, s)) with a public table (walk ↔
   footway, residential, service; fast ↔ motorway, trunk, primary); edge time = length / state speed (TD
   speed for motor states); stop spells become dwell at the head node (signals preferred).
5. **`sequence_log_prob`.** Forward algorithm over the three moving states (the stop state emits dwell, not
   edges, so it is folded into the transition matrix A): log P(r) = log P(O)P(D|O) + log Σ_paths ν(s_1)
   Π_i A_{s_{i−1}s_i}(ℓ_{i−1}) q_{s_i}(e_i | node_i, D), with q normalised per node and state. O(9L) per route
   on P3's cached cost-to-go; private numbers enter only through ν (and τ* if the reach rule is used).
6. **n = 91.** ε 0.5: ±0.33 per share, nothing. ε 2: 4 shares ±0.07, implied mean speed Σ π_s v_s ±0.7–0.8
   m/s; if the prior is car-heavy (≈ 6 m/s) and Geolife walk- and stop-heavy (≈ 3 m/s), the gap is ≈ 4 SD;
   duration moves through the stop share. ε 8: 12 cells ±0.03–0.05 (sampling), mean speed ±0.4 m/s, road
   class use per state calibrated. n = 10,000: state × class × daypart (36 cells) by OLH, ±0.009, giving
   time-weighted TD speed corrections per class and daypart.
7. **Closest.** Markov-chain driving-cycle synthesis (Lin & Niemeier 2002–03; Lee & Filipi 2011) and
   stops-and-moves (Spaccapietra et al. 2008), non-private; "Time will not tell" (Helsinki 2024, Markov-chain
   speed perturbation of released trajectories) and RATR (PolyU, temporal LDP trajectory release) perturb
   each trajectory, no user-level synthesis (snippets only); HMM map matching (Newson & Krumm 2009) hides a
   road position, not a speed state that emits road classes. vs §4: C1 averages a per-trip speed ratio
   (trip-weighted mean only), C3 gives one regime per trip; R2-A.2 estimates the time-weighted within-trip
   state mix, so walk–bus–walk trips and stops exist. vs round 1: A.4 (C8) sent a length-uniform point's
   road node + speed bit to grow corridors, E.2 (C9) sent manoeuvre × road-class bigrams; R2-A.2 sends no
   place and no token, and road class follows from speed.
8. **Risk.** Routes depend on private numbers only weakly, so spatial metrics stay near the prior unless the
   reach rule is used; GPS sampling (1–5 s vs sparse) blurs stop vs walk; public spell durations set the
   spread of per-trip mean speeds, so W1 can stay wrong while the mean is right; footways may be missing
   from the graph (P9).

## R2-A.3 Activity clock: arrival time and stay length decide purpose, reach and destination
1. **Pitch.** Users report only when a trip ended and how long they stayed afterwards; cited time-use,
   travel-time-ratio and opening-hour constants turn this into the trip's purpose, time budget, reach and
   destination, so the tidal pattern (mornings toward workplaces, evenings toward housing) comes from the
   clock and public land use, not from spatial reports.
2. **Report.** The device (it needs all of its own clean trajectories, not only the matched ones) draws one
   matched trip J; dwell W_J = start of the next own trajectory − arrival of J if that start lies within
   300 m and 16 h, else undefined. Value = dwell class (< 45 min, 45 min–4 h, > 4 h, undefined): 4 values,
   2 bits; at ε 8 also the arrival daypart: 12 values. GRR at full ε.
3. **Privacy.** As R2-A.1; 'undefined' is an ordinary category, so a missing dwell needs no biased default.
4. **Server.** Debias → dwell-class shares (joint with arrival daypart at ε 8; public arrival prior below);
   shrink to π0 from cited time-use constants (China Time Use Survey 2018: activity durations, time-of-day
   participation). Synthesis: (arrival daypart, dwell class) → activity type by public P(type | dwell,
   daypart) (work or study, home or overnight, errand, leisure or eating) → W inside its class → budget
   T = W·TTR_type/(1 − TTR_type) with cited travel-time ratios (Dijst & Vidakovic 2000; Schwanen & Dijst
   2002) → arrival inside the daypart, departure t0 = arrival − T → O public → D from R2-A.1's ring kernel
   with τ* = u0·T (u0 = public tightness prior) and attraction = OSM POIs and land use of that type open at
   arrival (OSM `opening_hours`, cited defaults per amenity) → route and segment times as in R2-A.1, with
   the arrival daypart's costs (public rule, identical in the likelihood).
5. **`sequence_log_prob`.** R2-A.1's formula with the type as an extra mixture index: log Σ_{d,c} π̃(d,c)
   Σ_type P(type|c,d) P(O) K_{d,type,c}(O,D) S_d(r) + floor; one forward Dijkstra from O per daypart yields
   all type normalisers; cache cost as in R2-A.1.
6. **n = 91.** ε 0.5: nothing. ε 2: 4 shares ±0.07; conditional dwell shares ±0.07/(1 − undefined share),
   i.e. ±0.15 if half the trips lack a dwell; moves only if the time-use prior is far off (e.g. researchers'
   long office stays). ε 8: 12 cells ±0.03–0.05; arrival rhythm × stay length, with departure, duration,
   length and tidal OD derived. n = 10,000: 6 arrival bins × 5 dwell classes + undefined by OLH (±0.009),
   plus one TTR correction per type through a public user split.
7. **Closest.** Travel-time ratio and spatial reach (Dijst & Vidakovic 2000; Schwanen & Dijst 2002) and
   facility opening times in MATSim (Horni, Nagel, Axhausen 2016), non-private; HRNet 2024 (central DP,
   stay points as waypoints); DP-WHERE 2013 (central, calling times); Badu-Marfo et al. 2020 (central DP GAN
   of activity diaries). vs round 1: D.4 used stays only to find anchors, and B.3/E.4 (C4) released home/work
   anchors, leave/return times and the away time of tours; R2-A.3 is anchor-free, per trip and unlinked, so
   Cond-C4 is not needed (its gain shows on unlinked departure, duration, length and OD metrics). Raw idea
   A.3 measured tidal flow with cordon × hour bits; here it is derived. vs §4: C2 estimates zones and cost
   bands; C1 and C3 ignore stays.
8. **Risk.** Dwell is badly measured in Geolife (logging gaps inflate W; the undefined share may pass one
   half, halving the effective n); the harness passes only matched train views to `fit`, so the device
   simulation needs each user's full clean history (privacy-neutral, same user); TTR and time-use constants
   come from other populations; OSM POI and opening-hour coverage in Beijing is thin; no metric sees purpose.

## R2-A.4 Peak-contrast router: users as their own control for a clock-driven router
1. **Pitch.** Routes are walked on a clock (link costs and edge choice follow the cited congestion profile,
   scaled by two population numbers), and users calibrate those numbers with within-user peak-minus-off-peak
   contrasts, which cancel everything constant per user (mode, home area, map-matcher bias);
   `sequence_log_prob` sums the unobserved clock out.
2. **Report.** A public coin (hash of the enrolment id with a public seed) picks the question; at n ≈ 91 and
   ε ≤ 2 everyone gets Q1. Q1: fine daypart of one sampled trip's departure (5 values). Q2: speed contrast
   c_v = mean log(v_obs/v_ff) over the user's peak segments (weekdays 07:00–09:30, 17:00–19:30) minus the
   same off-peak, classes {< −0.25, ≥ −0.25, undefined}. Q3: arterial contrast c_a = share of moving time on
   primary/trunk/motorway at peak minus off-peak, classes {< −0.1, ≥ −0.1, undefined}. GRR; 2–3 bits.
3. **Privacy.** The question index is public and independent of the data; given it, one GRR at full ε, so
   (index, answer) is ε-LDP; one report; 'undefined' is a category.
4. **Server.** Q1 → departure shares; Q2/Q3 class shares → κ_v (amplitude of the public congestion profile)
   and κ_a (peak penalty per arterial metre) by inverting a public response table (simulate the public
   generator over a κ grid, as in C1's moment matching). Synthesis: t0 from the shares and a public
   within-daypart shape; O, D public (or C2); Boltzmann walk whose step cost at clock t is ℓ/v(class, t; κ_v)
   + κ_a·g(t)·ℓ·[arterial], cost-to-go from one reverse Dijkstra per (D, daypart); the clock advances by each
   edge's TD time; segment times = TD times × public AR(1) jitter.
5. **`sequence_log_prob`.** For each of 96 quarter-hour start slots s0 the clock path along r is
   deterministic, so log P(r) = log Σ_{s0} π(s0) P(O)P(D|O) Π_i q_{daypart(s_i)}(e_i | node_i, D) + floor:
   96 × L terms; 5 reverse Dijkstras per destination (≈ 220 s per arm at u182, cached).
6. **n = 91.** ε 0.5: nothing. ε 2: 5 departure shares ±0.075; moves only where the cited Beijing profile
   misses Geolife by ≥ 0.15; κ_v, κ_a stay prior. ε 8 (public split Q1/Q2): departure ±0.06, c_v shares
   among defined users ±0.11, so κ_v is coarse. n = 10,000: three questions on 3,333 users each, shares
   ±0.012, κ_v and κ_a to about ±0.03, departure in 12 two-hour bins.
7. **Closest.** Time-dependent stochastic route choice (Gao, Frejinger, Ben-Akiva 2008) and FIFO TD travel
   times (Ichoua et al. 2003), non-private; MTNet 2022 (central DP-SGD, next edge conditioned on time);
   LDP A/B testing (Ding et al. 2018) contrasts publicly assigned groups (between users), R2-A.4 contrasts
   conditions within one user. vs round 1: C.1/E.3 (C1) reported speed and class-share levels per period,
   A.3 used a time-dependent logit inside a cordon assignment; R2-A.4 reports differences, not levels, and
   makes the route itself clock-dependent with an exact clock-marginal likelihood. Lesson 4 is answered
   structurally: a time-invariant matcher bias cancels in a contrast.
8. **Risk.** At n ≈ 91 only the departure profile moves, which is round-1 content; many users travel in only
   one period (large undefined share); the route-level gain is a large-n claim; 5 Dijkstras per destination.

Sources from the three searches: RATR, https://research.polyu.edu.hk/en/publications/ratr-optimized-trajectory-release-with-temporal-local-differentia/ ;
"Time will not tell", https://researchportal.helsinki.fi/en/publications/time-will-not-tell-temporal-approaches-for-privacy-preserving-tra/ ;
HRNet, https://arxiv.org/abs/2405.08043 .

## Self-ranking
1. R2-A.1 Prism-first: one ≤ 9-way time item at ε 2 moves duration, mean speed and length together through an exact, cacheable likelihood; the most time-first structure; doubt = slack and loops.
2. R2-A.2 Clock-sampled speed states: cleanest estimator (time-uniform sampling targets the mean-speed mix, ±0.7 m/s at ε 2) and cheapest likelihood; spatial gain only via the reach rule; natural slack module for R2-A.1.
3. R2-A.3 Activity clock (most novel but fragile: dwell is poorly measured, needs a harness change), then R2-A.4 Peak-contrast router (elegant own-control statistic, but at n ≈ 91 only the departure profile moves).
