# Round 2 consolidation: eight candidates K1–K8 (consolidator, 2026-10-07)

Inputs: `01_task.md`, `02_consolidate_task.md`, `00_baseline.md` and the five `10_ideas_R2-*.md` files (18 ideas). Raw English
material; nothing here is decided. Ids: K1–K8 round-2 candidates; R2-A.1 … R2-E.4 round-2 raw ideas (R2-B numbered as in its
file: B.1 habit modes, B.2 corridors, B.3 copy process); C1–C10 and A.1–E.4 round 1 (`00_baseline.md` §3–§4); X1–X14 the
cross-cutting findings at the end. Noise numbers are for n = 91 and were re-checked with the exact debiased-GRR formula
SD = √(f(1 − f)/n)/(p − q), f = q + π(p − q), which includes the sampling term (X3); numbers that depend on unmeasured Geolife
properties are marked as claims.

Standard arms for every K (not repeated below): its prior arm (ε → 0) and oracle arm (ε = ∞); the control "ldptrace lifted to
user level" (X7); the §4 module that targets the same quantity, on the same users; the S2 recovery simulation (n = 10 …
10,000, same `encode_user`/`server_fit` code); the P4 privacy kit. At ε 0.5 every K reduces to its prior arm (SD 0.28–0.41 per share; K1's bit can at most flag a prior ≥ 1.5 spreads off).

| K | Name | Raw ideas | What ε 2 can move at n ≈ 91 | In the edge likelihood? | Main hazard |
|---|---|---|---|---|---|
| K1 | Twin-rank calibration | R2-C.1, R2-D.1 (+ R2-D.2, R2-D.3 as optional cohorts) | log-duration shift ±0.17 spread, coarse spread | not at n ≈ 91 | saturation; Joseph et al. 2019 |
| K2 | Time-budget prisms | R2-A.1, R2-A.3 | 3-way tightness (±0.073) or 9-way (T, u) cell | yes (ring-kernel destinations) | u ≈ C1's speed ratio / detour |
| K3 | Clock-sampled speed states | R2-A.2 | 4 time shares → mean speed ±0.76 m/s | weakly (ν; reach rule) | re-learns C3's mode mix |
| K4 | Via-point route structure | R2-C.2, R2-B.2 | loop and one-piece shares ±0.074 | yes (piece-count mixture) | matcher artefacts |
| K5 | Habit-mode hubs | R2-B.1 | a 5-km hub cell holding ≥ 35 % of users' modes | yes (hub mixture over O, D) | "mode, not sample" = one detail? |
| K6 | Mobility-signature users | R2-E.2, R2-B.3 | distinct-places bins → EPR ρ (≈ 5.4 SD if ρ halves) | EPR part yes, copy layer no | trips-per-user law; visibility |
| K7 | Proxy respondent | R2-E.1 (+ R2-E.3 as ε 8 option) | one simulator parameter (≈ 3.4 SD, design claim) | yes (θ̂) | LDP distillation; C7's shape |
| K8 | Within-user contrasts and couplings | R2-C.3, R2-A.4, R2-E.4 (+ R2-D.4 pooled) | nothing unless the effect is very large | only R2-A.4's clock router | invisible to current metrics |

Lens coverage: R2-A → K2, K3, K8; R2-B → K4, K5, K6; R2-C → K1, K4, K8; R2-D → K1, K8; R2-E → K6, K7, K8.
Compliance: every K emits road-valid routes (P3 Boltzmann walks, alone or concatenated through public vias, with the
shortest-path finish), a departure and per-segment times (needs P1, S5); one report per user through one standard ε-LDP
primitive at full ε (X1), users (never ε) split across question families by a frozen n·ε² table; multi-round only over a
public random partition into disjoint cohorts (K1's sequential form, K8's pooled form); a finite `sequence_log_prob` over edges
(S4). Field 4 of each K names the cited constants it must extract and freeze before any run (S1).

## K1 Twin-rank calibration: one trip ranked among public twins of its own context
1. **Provenance, pitch.** R2-C.1 (3-bin rank, one round, exact-null gate) + R2-D.1 (median bit, saturation-triggered second
   cohort, ordered menu); R2-D.2 (census) and R2-D.3 (validator) as optional cohorts at n ≥ 300 only (X8). The device ranks one
   of its trips among "twins" that the public simulator draws for that trip's own context and sends the coarse rank; the server
   corrects the miscalibrated conditional law and keeps the prior wherever an exact uniform null is not rejected.
2. **Report.** A public per-user draw picks one question in a frozen order: *dur* (travel time given own route and departure),
   *len* (OD road distance given O), *radial* (trip-end distance under the OD prior's radial CDF; probes C2's unchecked
   concentration risk), *route* (surprise log P_router(route | O, D)), *dep* (exact PIT, no twins). Device: one matched trip
   uniformly, K = 29–50 twins at the public θ_t, rank with random tie-break. One-round form: GRR over 3 prior-equal bins (1.6
   bits). Sequential form: 1[u > ½] by binary RR. ε 8: HM on u ∈ [0, 1] (no public range needed) or the 9-way (dep, dur) cell.
3. **Privacy.** Lift lemma (X1): question, θ_t, bins and seeds are public or local coins, twins never leave the device, one
   primitive at full ε. Sequential form: a public random cohort partition fixed before any report; θ_t depends only on earlier
   disjoint cohorts (sequentially interactive LDP), so each user reports once at ε.
4. **Server.** Debias; a public gate (debiased chi-square vs uniform, critical value simulated in advance) decides whether to
   move. Time: quantile mapping, density = prior × g(F_prior(x | context)), exactly normalised as E_prior[g(U)] = 1; 3 bins give
   a shift and a spread of log-duration. len, radial, route: simulated moments against the public expected rank histogram as a
   function of γ, a centrality exponent or β. Sequential: one parameter by simulated moments under a between-user heterogeneity
   law (±0.3 nats; must be cited, S1); a 90 % interval outside [0.25, 0.75] makes the next cohort re-ask at θ_{t+1}. Synthesis
   on the P3 simulator: D by gravity at γ̂, Boltzmann walk at β̂, departure from the mapped diurnal prior, segment times =
   free-flow × factor × jitter with the total quantile-mapped and every segment scaled by the same ratio.
5. **`sequence_log_prob`.** §4.7 with ≤ 2 corrected numbers: log P(O, D; γ̂) + Σ log steps at β̂ + floor; time absent; at
   n ≈ 91 only *dur* is asked, so it equals the prior's (MIA-blind). Ablation: + log g(F_ℓ(ℓ(seq) | O, D)) with twins seeded by
   hash(O, D, map, config). One code path; ≈ 40 ms per queried destination; caches shared by the 17 generators.
6. **n = 91.** ε 0.5: ±0.28 per bin share, ±0.21 for the bit, so the gate keeps the prior. ε 2 (all users on *dur*): ±0.073
   per bin, ±0.069 for the bit; both locate the shift to ±0.17 spreads (re-checked: 0.126/0.727 vs 0.069/0.399), i.e. ±0.07
   nats at a single-trip spread of 0.42 nats, if the pivot is within ≈ 1 spread; otherwise one round says only "≥ 1.3 nats,
   this way" and a second half cohort gives ±0.10 nats. Against C1's PM: length scale ±0.17 vs ±0.25; speed level only if C1
   cannot shrink its range by regime (±0.06 with regimes, R2-D.1's own admission). ε 8: HM on ranks beats the bit (±0.045 vs
   ±0.055 nats); two questions at ≈ 45 users each, or the (dep, dur) copula at ±0.033 per cell. n = 10,000: all questions,
   5–10 dithered bins, maps per period × length tertile, copulas; 8–10 ordered cohorts of ≈ 1,000 users (SD 0.021).
7. **Difference.** C1 (A.1, B.1, C.1, D.2, E.3) sends clipped trip-averaged moments at hand-set ranges; raw idea C.1 ("centred
   on the prior's expectation") is nearest but sends a mean, with clipping and no null. K1's statistic is conditioned on the
   trip's own context, bounded by construction and uniform under a correct prior for any trip count (X4). C3: a label over
   generators, not calibration within one. C5 (D.1, C.3): twins are exchangeable with the trip, not a library. C7 (C.4), D.3:
   no knob surface, no duel, but the sequential form keeps C7's shape (server-set model, one bit back). Closest: Joseph,
   Kulkarni, Mao, Wu 2019 (adaptive two-round LDP Gaussian estimation); Penso et al. 2025 (LDP conformal prediction, conformity
   score by RR); Berrett & Butucea 2020, Lam-Weil et al. 2022 (LDP goodness-of-fit); Calibrate 2019; PIT and simulation-based
   calibration (Dawid 1984; Hamill 2001; Talts et al. 2018); Luo et al. 2020 (central-DP recalibration); Xiong et al. 2023.
8. **Risks, reviewer.** Saturation: a narrow car-speed prior puts every walk or bus trip in the top bin, and the remedies
   disagree (X9); one map per question assumes context-free miscalibration; durations hold stops and GPS gaps; the route rank
   measures the matcher (X13); at n ≈ 91 it moves what C1 and C3 move (X10). Reviewer: C1's PM on the same statistic and
   users; gate on/off; one vs two cohorts; S2 with a misspecified jitter shape.
9. **Novelty queries.** "local differential privacy probability integral transform calibration"; "locally private
   goodness-of-fit rank histogram"; "adaptive two-round local differential privacy re-centring"; "conformal prediction local
   differential privacy randomized response"; "privacy-preserving traffic simulator calibration". Compare: Joseph et al. 2019,
   Penso et al. 2025, Berrett & Butucea 2020, Zhou & Tan 2021 (C7), Xiong et al. 2023, GeoPM-DMEIRL 2024.

## K2 Time-budget prisms: space follows from time on the public network
1. **Provenance, pitch.** R2-A.1 (prism cell) + R2-A.3 (activity clock) as a second question family; K3's stop spells can fill
   the slack. A trip starts as two times, its duration T and its prism tightness u = (public time-dependent fastest time O → D
   at departure)/T; the destination is drawn from the iso-time ring that u·T defines around a public origin, so length, mean
   speed and segment times follow from time plus the public network.
2. **Report.** Family P (R2-A.1): one matched trip uniformly; T, t0, τ (one Dijkstra, daypart-static time-dependent costs),
   u = τ/T; T in public prior terciles, u in {< 0.25, 0.25–0.6, > 0.6}: 9 values by GRR (27 with the coarse daypart at ε 8); a
   3-way u-only fallback fixed before data by S2. Family W (R2-A.3; ε 8 or large n): dwell after one matched trip (start of the
   next own trajectory within 300 m and 16 h) in {< 45 min, 45 min–4 h, > 4 h, undefined}; 12 values with the arrival daypart.
   At n ≈ 91 all users answer P.
3. **Privacy.** Lift lemma (X1); cut points, time-dependent profile, classes and the dwell rule public; 'undefined' is an
   ordinary category (no biased default); one report, no ε split.
4. **Server.** Debias → simplex → shrink to the public prior generator's cell shares. Public (S1): speed v(class, t) = OSM
   free-flow × φ(class, t) from a cited Beijing congestion profile (Beijing Transport Institute report), cited mode speeds; for
   W the China Time Use Survey 2018, travel-time ratios TTR (Dijst & Vidakovic 2000; Schwanen & Dijst 2002), OSM POIs, land use
   and `opening_hours`. Synthesis: daypart d → cell c ~ π̃(·|d) → O by public road mass → D ~ a(x)·k_c(τ_d(O, x)) (ring kernel
   from one forward Dijkstra; W: purpose by public P(type | dwell, daypart), budget T = W·TTR/(1 − TTR), attraction = POIs of
   that type open at arrival) → (T, u) inside c with u·T = τ_d(O, D) → Boltzmann walk with daypart-d costs (distance costs for
   the walk-like class) → FIFO time-dependent segment times from t0 (Ichoua et al. 2003), rescaled to sum to T.
5. **`sequence_log_prob`.** log Σ_d π_d P(O) Σ_c π̃_{c|d} K_{d,c}(O, D) S_{d,ρ(c)}(r) + floor, with K_{d,c}(O, D) =
   a(D)k_c(τ_d(O, D)) / Σ_x a(x)k_c(τ_d(O, x)) and S the step product under router ρ(c) ∈ {distance, car at d}; W adds a
   purpose index; time summed out. Cost: 3 forward Dijkstras per queried origin + 4 reverse per destination ≈ 5 min per arm at
   u182 (budget 1,200 s), keyed by map + config, shared by the 17 generators.
6. **n = 91.** ε 2: 9 cells ±0.079, margins ±0.12 (re-checked), so a margin moves only if the prior misses it by ≥ 0.25,
   plausible for u (the prior has no in-trip stays and few walks); u-only fallback ±0.073; W, if asked, ±0.074 per share and
   ±0.15 conditional on a defined dwell if half are undefined. ε 8: 27 cells ±0.02, margins ±0.05 (sampling): the departure ×
   duration × tightness coupling. n = 10,000: 48 cells (3 dayparts × 4 × 4) by OLH ±0.009; W on 6 arrival bins × 5 dwell
   classes + undefined, and one TTR correction per purpose.
7. **Difference.** C2 (B.2, A.3) estimates where trips go (zones, free-flow cost bands) and inverts gravity; K2 releases no
   spatial quantity. Honest overlap: u = τ/T is C1's speed ratio to free flow divided by a time detour and T is a duration
   moment, so the report folds C1's two n ≈ 91 numbers into one joint categorical item; the distinct element is the generator
   (destinations from iso-time rings of the time-dependent network). C3: u is measured against a public reference, not a
   posterior label, yet the 3-way fallback is close in spirit. C4: no anchors; W treats a stay as a per-trip unlinked quantity,
   so Cond-C4 is claimed unnecessary (a dwell is still a two-trajectory quantity that per-trip LDP cannot release). Raw idea
   A.3's cordon × hour tidal flow is derived here, not measured. Closest: network-time prisms (Miller 1991; Kuijpers & Othman
   2009; Kuijpers, Miller, Neutens, Othman 2010), travel-time budgets (Zahavi 1974; Mokhtarian & Chen 2004), PCATS (Kitamura &
   Fujii 1998), MATSim opening times; RATR and "Time will not tell" 2024 (per-trajectory temporal LDP, snippets); HRNet 2024,
   DP-WHERE 2013, Badu-Marfo et al. 2020 (central DP).
8. **Risks, reviewer.** u conflates mode, congestion, detours and in-trip stays; the slack rule decides walk vs car-with-stop
   (mean speed right by construction, segment speeds possibly wrong); loops (O ≈ D) get u ≈ 0 (K4's loop class would help);
   spatial concentration stays prior. W: dwell badly measured (logging gaps), the undefined share may pass ½, it needs clean
   views (X6), constants from other populations, thin POI and opening-hour coverage, and no metric sees purpose. Reviewer:
   ring-kernel vs gravity destinations with the same time items (does space from time help length W1 and OD JSD?); C1's two
   numbers on the same users; a slack-rule ablation.
9. **Novelty queries.** "space-time prism differential privacy synthetic trajectories"; "travel time budget local
   differential privacy"; "isochrone destination choice privacy"; "temporal local differential privacy trajectory dwell
   time". Compare: Miller 1991, Kuijpers et al. 2010, PCATS 1998, RATR, "Time will not tell", HRNet 2024, TimeGeo 2016.

## K3 Clock-sampled speed states: a time-weighted mode mix drives a state-dependent router
1. **Provenance, pitch.** R2-A.2 alone (R2-A calls it K2's natural slack module; kept apart because its generator and
   likelihood differ). Each user reports the speed state (stopped, walking, slow, fast) at one uniformly random second of their
   recorded travel time, a time-weighted sample whose population share is exactly the time-share mix behind mean speed; the
   generator runs a semi-Markov speed clock and lays it on the graph with a walk whose road classes follow the current state.
2. **Report.** The device concatenates the time intervals of all its matched trips, draws U ~ Uniform(0, total travel time),
   smooths speed over ±30 s at U and classes it with public thresholds (< 0.5, 0.5–2.2, 2.2–8, > 8 m/s): 4 values by GRR. ε 8:
   × the road-class group of the edge being traversed (minor, arterial, expressway), 12 values. No matched trip: public default.
3. **Privacy.** Lift lemma (X1): the time-uniform draw only selects the input of one GRR; thresholds public; one report.
4. **Server.** Debias → time shares π̂_s, shrunk to π0 from cited constants (S1: Beijing driving-cycle idle shares, mode mix,
   mode speeds walk 1.35, cycle ≈ 4, bus ≈ 4.5 m/s). Public mean spell durations m_s (signal stop 30–60 s, walk access, cruise
   between signals); jump-chain weights ν_s ∝ π̂_s/m_s so that time shares match; public persistence per km. Synthesis:
   departure (public profile), O (public), D by P3 gravity or, with the reach rule, by K2's ring kernel at τ* = T·ū/v_car(d),
   ū = Σ_s π̂_s v_s; state path and route together: the state may switch at each node; next edge ∝ exp(−β[c(e) + V_D(head e)]
   + η·compat(class e, s)) with a public table (walk ↔ footway, residential, service; fast ↔ motorway, trunk, primary); edge
   time = length / state speed (time-dependent speed for motor states); stop spells become dwell at the head node.
5. **`sequence_log_prob`.** Forward algorithm over the three moving states (stop folded into the transition matrix A):
   log P(r) = log P(O)P(D|O) + log Σ_paths ν(s_1) Π_i A_{s_{i−1}s_i}(ℓ_{i−1}) q_{s_i}(e_i | node_i, D), q normalised per node and
   state; O(9L) per route on P3's cached cost-to-go; private numbers enter only through ν (and τ* with the reach rule).
6. **n = 91.** ε 2: 4 shares ±0.074; implied mean speed ±0.7–0.8 m/s (re-checked: ≈ 0.76 for a 20/30/30/20 % mix at 0, 1.3,
   5, 12 m/s); a car-heavy prior (≈ 6 m/s) against a walk- and stop-heavy Geolife (≈ 3 m/s) would be ≈ 4 SD (the gap is a
   claim); duration moves through the stop share. ε 8: 12 cells ±0.03–0.05 (sampling), mean speed ±0.4 m/s, class use per
   state. n = 10,000: state × class × daypart (36 cells) by OLH ±0.009 → time-weighted speed corrections per class and daypart.
7. **Difference.** C3 (B.4, C.2, D.3): one regime per trip, a posterior label over complete generators; K3 estimates the
   within-trip time mix, so walk–bus–walk trips and stops exist. C1: a trip-weighted mean speed ratio. C8's raw idea A.4 sent a
   length-uniform point's road node + ±1 speed bit to grow corridors; K3 samples uniformly in time (the measure that makes the
   share exact for mean speed) and sends no place; Cond-C8 is irrelevant. C9 (E.2): no tokens; road class follows from speed.
   Closest: Markov-chain driving-cycle synthesis (Lin & Niemeier 2002–03; Lee & Filipi 2011), stops-and-moves (Spaccapietra et
   al. 2008), "Time will not tell" 2024 and RATR (per-trajectory perturbation, snippets only), HMM map matching (Newson & Krumm
   2009; hides a road position, not a speed state that emits road classes).
8. **Risks, reviewer.** Routes depend on the private numbers only weakly, so spatial metrics stay near the prior unless the
   reach rule is used; GPS sampling (1–5 s vs sparse) blurs stop vs walk; public spell durations set the spread of per-trip
   mean speeds (W1 can stay wrong while the mean is right); footways may be missing (P9); at n ≈ 91 it measures C3's mode mix
   (X10). Reviewer: C3's 3-regime vote on the same users; time-uniform vs trip-uniform sampling; the reach rule on/off.
9. **Novelty queries.** "local differential privacy speed distribution driving cycle"; "hidden Markov speed state route
   generation privacy"; "time-weighted sampling local differential privacy"; "stops and moves synthetic trajectories
   differential privacy". Compare: Lin & Niemeier, Lee & Filipi 2011, Spaccapietra et al. 2008, RATR, "Time will not tell",
   PCKV 2020 with C8's A.4.

## K4 Via-point route structure: pieces, loops and habitual corridors
1. **Provenance, pitch.** R2-C.2 (piece count, loop, sub-path window bit) + R2-B.2 (modal named corridor and loyalty); both
   decode into the same via-point router with the same exact likelihood. One sampled trip carries its route's global structure
   (how many near-shortest pieces, whether it is a loop; at ε 8 or large n also which named corridor the user rides most); the
   server fits a router whose routes concatenate near-shortest walks through public via nodes, which also produces the loops
   that a walk toward the destination cannot.
2. **Report.** Family S (R2-C.2): one matched trip uniformly; greedy split into maximal pieces whose free-flow cost is ≤ (1 + τ)
   × the shortest cost between the piece's ends (τ = 0.05); class ∈ {1 piece, 2, ≥ 3, loop (OD road distance < 0.25 × route
   length)}, GRR over 4. Window variant: a public log-uniform window length in [0.5, 8] km placed uniformly on the sampled
   route, one RR bit "near-shortest", giving λ via points per km. ε 8 or large n: + the main via's lateral offset and position
   (6–20 classes). Family C (R2-B.2): modal corridor among 64 frozen named OSM corridors (ref/name, ≥ secondary) + "none", OLH
   over 65; or loyalty λ_u (share of trips riding the modal corridor ≥ 500 m) by HM. At n ≈ 91 and ε ≤ 2 all users answer S.
3. **Privacy.** Decomposition, classes, corridor list and thresholds are functions of the user's data and the public map,
   frozen on OSM and the fixture before any Geolife run; GRR/RR/OLH/HM at full ε; lift lemma (X1); one report.
4. **Server.** Debias; shrink to cited shares of shortest-path-consistent and anchor-based routes (S1: Zhu & Levinson 2015; Lima
   et al. 2016; Manley et al. 2015) and a cited leisure-loop share, all still to extract and freeze; corridor shares thresholded
   family-wise, the rest to "none". Generator: (O, D) from the prior or C2 (loop: D within a public radius of O); k from the
   shares (or Poisson(λ̂·d_OD)); k − 1 vias from a public anchor set (≈ 500–3,000 junctions of secondary-or-higher roads) under
   a public offset kernel around the OD axis; corridor users pass one of the corridor's ≤ 5 public waypoints with probability
   λ̂; pieces = high-β Boltzmann walks toward the next via (road-valid); departure and segment times from the public time model
   (or K1/K3 corrections).
5. **`sequence_log_prob`.** Σ_class π_class Σ_{via positions on the sequence} P(vias | O, D) Π P_walk(piece | next via) + floor;
   vias must be anchors on the queried sequence (≤ 2 vias, ≈ 40 positions, ≤ 800 pairs), exact by dynamic programming with
   prefix sums; the k = 1 term is the §4 walk; corridor term λ̂ Σ_c π̂_c |W_c|⁻¹ Σ_{w ∈ W_c ∩ seq} P_walk(seq to w)·P_walk(seq
   from w). Caches: one reverse Dijkstra per anchor (≈ 40 s and 140 MB for 1,000 anchors, or lazily for anchors on queried
   routes) and per corridor waypoint (320: ≈ 15 s, 50 MB); public, keyed by map + config, shared by the 17 generators.
6. **n = 91.** ε 2: ±0.074 per share: the loop share (the §4 walk gives loops almost no mass, so a true share ≥ 0.15 is a 2-SD
   gain) and the one-piece share; or λ to ±25 % (window variant; claim). Family C at ε 2: threshold ≈ 0.28 over 65 values, so a
   corridor must be the mode of ≥ 37 % of users: probably nothing. ε 8: ±0.045 per share plus the offset class of two-piece
   trips (λ ±18 %); family C releases essentially every training user's modal corridor, λ̂ ±0.045. n = 10,000: class × offset
   × position (≈ 20 cells) and period splits; corridors of ≥ 3–4 % of users at ε 2.
7. **Difference.** C1 (A.1, B.1, C.1, D.2, E.3) tilts a one-piece walk by route moments (randomness at every step); here a few
   global decisions, and the piece count does not depend on class mix or turn density. C8 (A.4) shares only the corridor target
   with family C: one batch, a user's mode instead of a length-sampled point, a loyalty share, an exact likelihood; Cond-C8 is
   not claimed. No tokens (C9), library (C5) or flows (C10). Closest: DPMM 2022 (per-trajectory waypoints and
   exponential-mechanism paths; releases each user's perturbed path, no population law, likelihood or time); via-node
   alternative routes (Abraham et al. 2013); PRESS (Song et al. 2014); anchor-based route choice (Manley et al. 2015); Yang et
   al. 2020 (hot paths, LDP + secret sharing); AHEAD 2021.
8. **Risks, reviewer.** GPS gaps make the matcher fill straight shortest paths (k biased to 1) and GPS noise creates spurious
   pieces; τ and the cost metric decide k; matched corridors partly describe the matcher (X13); hiking and sport loops may be
   off-graph or fail the match score (P9); the via-location law stays prior at n ≈ 91; anchor caches must fit 300 s at
   u20/u50; family C needs a new OSM name/ref export and at ε 8 shows members' corridors to the MIA (inside the vacuous e^8
   bound). Reviewer: the §4 one-piece walk vs the via router on the same OD; piece counts on matched routes vs raw GPS.
9. **Novelty queries.** "via point route generation local differential privacy"; "differentially private route waypoints
   exponential mechanism"; "local differential privacy popular routes road network"; "loop trips detour structure synthetic
   routes privacy". Compare: DPMM 2022, Abraham et al. 2013, Manley et al. 2015, Yang et al. 2020, AHEAD 2021.

## K5 Habit-mode hubs: report the habit, not a sample
1. **Provenance, pitch.** R2-B.1 alone; K6's copy layer is its optional linked module (R2-B's own recommendation), and K4's
   family C applies the same mode principle to routes. Users report a habit (the modal cell of their trip ends, how strongly
   they return there, their modal departure daypart) instead of a sampled trip item; the server decodes habits into synthetic
   users who own a hub and return to it, and the sharper estimand shows on today's unlinked metrics.
2. **Report.** Frozen n·ε² table: < 100 (ε 0.5) prior arm; 100–2,000 (ε 2) all users on Q1 at 6 × 6; > 2,000 (ε 8) Q1 at
   20 × 20, Q2, Q3 as 50/25/25. Q1: modal cell of the user's trip ends on a regular grid of the map's bounding box, OLH
   (fallback 3 × 3 by GRR; ablation: the land-use class holding most trip ends, 6 classes from a frozen OSM-tag table grouped
   like EULUC-China level I, taxonomy only, never the EULUC map, S1). Q2: habit share h_u by HM on [0, 1]. Q3: modal departure
   daypart, GRR over 6. Ties by local coins; no matched trip: the randomizer runs on a public default input.
3. **Privacy.** Plan §4.6 and the lift lemma (X1): public question draw, a standard primitive on a function of all the user's
   trips, one report, no ε split; grid, class table, dayparts and the n·ε² table frozen by commit hash.
4. **Server.** π̂ = debiased OLH frequencies on the simplex; cells under a public family-wise threshold (≈ 3.0 SD over 36) get
   public road-length mass instead; ĥ and daypart shares debiased and clipped. Public (S1): non-hub kernel k_H = road-length
   mass × exp(−distance/L) with L from the cited radius-of-gyration law (González et al. 2008), prior h, diurnal prior, router,
   speeds. Synthetic user: hub cell H ~ π̂ (hub node by road-length mass); trip count from a public law (X5) or K6; each trip
   end is the hub with probability ĥ, else drawn from k_H; departure in the modal daypart with a public habit share, else from
   the diurnal prior; Boltzmann-walk route; segment times = free-flow × factor × jitter; trips emitted unlinked.
5. **`sequence_log_prob`.** log P(O, D) + log P_route(seq | O, D) + gap term, with P(O, D) = Σ_H π̂_H f_H(O) f_H(D) and node
   distributions f_H = ĥ μ_H + (1 − ĥ) k_H; the route term does not depend on H, so a query costs one cached walk plus a
   ≤ 400-term sum; no private factorisation, no cache filled only for training destinations; time unused.
6. **n = 91.** ε 2 (6 × 6 cells of ≈ 5 km): SD 0.089 for an empty cell, threshold ≈ 0.27; a cell holding ≥ 35 % of users'
   modes is kept with power ≈ 0.8 (re-checked with the frequency term: SD ≈ 0.107 at share 0.35, power ≈ 0.78), while the same
   cell holds only ≈ 0.19 of sampled trip ends (2.1 SD, dropped): the mode principle's claimed gain, a signal factor 1/h ≈ 2–3
   from the cited Zipf visitation law. Fallback 3 × 3: ±0.079 per share (R2-B wrote ±0.062, the vanishing-share value); class
   ablation ±0.076 (R2-B: ±0.055). ε 8: 20 × 20 at SD 0.0055 (45 users) keeps every cell with ≥ 2 users' modes, i.e. it
   releases single users' hubs; ĥ ±0.045, daypart shares ±0.1 (sampling). n = 10,000: 20 × 20 hubs with ≥ 4–5 % of users at
   ε 2, the kernel scale L as a fourth question, a joint hub × trip-count item that trip-weights heavy users' hubs.
7. **Difference.** C2 (B.2, A.3) asks one sampled trip end (signal diluted by h) and inverts gravity on 3 × 3 zones; Q1 could be
   bolted onto C2, but only a whole-user decoder turns modes into trips. C3 votes over generator settings. C4 (B.3 home x/y by
   PM, E.4 home-zone slot, D.4 relations): no semantics or stay detection, defined for m ≥ 1, the land-use class is a private
   report, and the gain is claimed on unlinked metrics, so R2-B holds Cond-C4 unnecessary; a reviewer may still read the modal
   cell as an anchor proxy (a C4 revival), and then Cond-C4 is met only with K6's coherence metric. Closest: a
   mobile-crowd-coverage paper (AAAI, snippet only: one frequently visited location per user under geo-indistinguishability,
   metric DP, no generator, no habit share); Acharya, Liu, Sun 2023 and Kent et al. 2024 (user-level LDP with m samples from
   one shared distribution; here users differ and the estimand is the habit distribution); DP-WHERE 2013; OnTheMap 2008; L-SRR.
8. **Risks, reviewer.** Modes may not concentrate (no 5-km cell with ≥ 35 % of users, a hub split by a cell boundary, badly
   tagged land use), and then ε 2 equals the prior; ĥ is biased upward for users with 1–3 trips (its correction needs the
   trips-per-user law, X5) and modes come from the ≈ 10 % matched subsample (X6); k_H misplaces users with a distant second
   place; ε 8 releases single hubs (the MIA may rise inside the vacuous bound); "the mode instead of a sample" may count as one
   detail (lesson 1). Reviewer: C2's sampled trip-end question vs the modal cell on the same users; hub decoder vs a plain
   zone-share decoder.
9. **Novelty queries.** "user-level local differential privacy most frequent location"; "local differential privacy per-user
   mode estimation"; "frequently visited location geo-indistinguishability crowdsourcing coverage"; "differentially private
   home location synthetic mobility users". Compare: the AAAI coverage paper (to identify), Acharya et al. 2023, Kent et al.
   2024, DP-WHERE 2013, OnTheMap 2008, L-SRR 2022.

## K6 Mobility-signature users: exploration-and-return calibrated by concentration descriptors, with a copy layer
1. **Provenance, pitch.** R2-E.2 (distinct places, radius of gyration, returner ratio → EPR constants) + R2-B.3 (copy process
   with an invariant single-trip marginal, repeat share and trip count, shipped user-level coherence metrics). The
   orchestrator's hint names R2-B.2; in the ideas file the exploration-and-return copy process is Idea 3 (R2-B.3) and Idea 2 is
   the corridor idea (now in K4). The device compresses its period into classic individual-mobility descriptors and releases
   one, binned; the server fits an exploration-and-preferential-return (EPR) population on the OSM graph and emits whole users.
2. **Report.** A public draw picks one descriptor (all users the same one when n·ε² is small). R2-E.2: trip ends snapped to a
   public 500 m grid; S = distinct cells (capped at 2m), r_g in km, k-radius ratio r_g^(2)/r_g; 4 public bins each (S ≤ 4,
   5–7, 8–11, ≥ 12; r_g < 2, 2–5, 5–10, > 10 km; the ratio at quartiles of the public prior simulation), GRR over 4. R2-B.3:
   repeat share r_u = 1 − (distinct OD cell pairs on a public 20 × 20 grid)/m_u by HM; trip-count class {1, 2–4, 5–12, ≥ 13}
   by GRR; at ε 8 or large n also route and time loyalty by HM. Fewer than 2 trips: the public default bin.
3. **Privacy.** Each descriptor is a bounded deterministic function of the whole trip set with public binning and default; the
   descriptor draw is public; full ε; one report; users, never ε, are split across descriptors (X1).
4. **Server.** Debias, shrink to the public prediction, then simulated method of moments on the public graph. Public (S1): EPR
   with Song et al. 2010 constants (ρ = 0.6, γ = 0.21, P_new = ρS^−γ), exploration by a d-EPR gravity law (Pappalardo & Simini
   2018) over OSM building or road-length mass, returns ∝ visit counts, EPR's waiting-time law (β = 0.8, cut-off 17 h). S pins
   ρ (γ at ε 8), r_g the gravity decay, the ratio the returner share, the count class the trips-per-user law (else public,
   X5). Copy layer (R2-B.3): a copy keeps O and D, keeps the route with probability λ (else redraws it from G given OD), keeps
   the departure hour with probability κ; segment times always redrawn. Synthesis per user: m trips, origin by public mass,
   explore-or-return moves, departure by the diurnal profile or the waiting-time law, Boltzmann route, free-flow × factor ×
   jitter; emitted unlinked, linked output one flag (`syn_user_id` in the payload for the coherence metrics).
5. **`sequence_log_prob`.** EPR part: the population's long-run OD over a public 12 × 12 zone grid, simulated once per θ̂ and
   cached by (map, config, θ̂): log P̂(zone_O, zone_D) + log public within-zone node masses + Σ log router steps + floor; 17
   simulations per arm, runtime unmeasured. Copy layer: exactly log G(seq) (verified, X11), so λ and κ add no MIA surface.
6. **n = 91.** ε 2, all users on S: ±0.074 per bin share (R2-E wrote 0.050 + sampling 0.045 = 0.067). EPR's public constants
   predict S ≈ 8.4 of 18 trip ends and ρ = 0.3 gives ≈ 4.7, a bin-share shift of ≈ 0.4 (EPR arithmetic, unverified on matched
   subsets), i.e. ≈ 5.4 SD: ρ at fixed γ, "how concentrated are trip ends", which is C2's unchecked risk. R2-B.3 standalone
   (60/40 split): mean r ±0.08, count shares ±0.11–0.12. ε 8: three descriptors on split users, ±0.08 each (sampling), giving
   ρ, γ and the decay; r ±0.036 and λ. n = 10,000: a joint (S, r_g) 16-cell OLH, EPR constants per regime, the trips-per-user
   law measured, r per count class, λ per road class, κ.
7. **Difference.** No catalogue (C3), no trip moments (C1), no zone shares (C2): geography stays public and only its
   concentration is measured. Revives C4's whole-user part (B.3, D.4, E.4) through a new angle (no anchors, schedules or stay
   detection; defined for every user with ≥ 2 trips, taxis included) and names **Cond-C4**, met by the shipped metrics: W1 of
   per-user repeat share, distinct-cell ratio, log trip count and radius of gyration, plus reach-to-volume per 20 × 20 cell,
   against held-out test users with a user-level bootstrap, unlinked releases scored as "every trip its own user".
   Disagreement: R2-E.2 holds Cond-C4 unnecessary because EPR changes unlinked marginals (length W1, 3 × 3 OD JSD); R2-B.3
   proves that a copy layer does not; whether EPR's ρ does is unverified (X11). Closest: EPR (Song et al. 2010), d-EPR/DITRAS
   (Pappalardo & Simini 2018), returners and explorers (Pappalardo et al. 2015), TimeGeo 2016, ASTRA (snippet), DP-WHERE 2013
   (central), Berke et al. 2022 (no DP); Acharya et al. 2023's presence-style reports (kept here only as a metric).
8. **Risks, reviewer.** S on ≈ 9 matched trips is heavily truncated, so the response surface leans on the trips-per-user law
   (X5) and on matched subsamples (X6); EPR constants come from call records, not GPS; the coherence metrics are noisy with ≈ 36
   held-out test users at u182 and useless at u20/u50; copies cut the effective synthetic sample (bias of pooled JSD) unless
   many synthetic users are generated; map matching inflates route loyalty. Reviewer: a one-hour public simulation showing
   whether ρ moves length W1 and OD JSD at all; EPR vs copy layer vs independent trips on unlinked and coherence metrics.
9. **Novelty queries.** "exploration preferential return differential privacy"; "radius of gyration local differential
   privacy"; "individual mobility model calibration privacy synthetic users"; "user-level coherence metric synthetic
   mobility data". Compare: Song et al. 2010, DITRAS 2018, TimeGeo 2016, DP-WHERE 2013, Berke et al. 2022, Acharya et al. 2023.

## K7 Proxy respondent: the device answers one designed public scenario with a model fitted to its own trips
1. **Provenance, pitch.** R2-E.1; R2-E.3 (exponential-mechanism tilt over public candidates) folded in as an optional ε 8
   decoder. As in a stated-preference survey, but with the device as respondent: it fits the public simulator's parameters to
   its own trips, answers one publicly drawn hypothetical scenario ("for this public origin, destination and departure, which
   of these K alternatives would you take?") and sends the answer by randomized response; the server recovers structural
   parameters through the exactly known channel.
2. **Report.** Public per-user seed → scenario s: a public OD, a departure window and K ≤ 4 alternatives from the public
   simulator (families: K routes trading major-road share against length; K duration bins; K destination zones for a public
   origin; K departure bins). Device: θ_u = maximum likelihood of the simulator's conditional parts (speed ratio by period,
   route coefficients, destination decay, departure profile) on its matched trips, clipped to a public box (< 2 trips: θ_0);
   answer = the alternative θ_u prefers (or a draw from its local choice probabilities); GRR over K at full ε, ≤ 2 bits.
   Option (R2-E.3, ε 8): M public candidate trips, j* drawn ∝ exp((ε/2)·u_j) with u_j ∈ [0, 1] a clipped log-likelihood ratio
   of θ_u against θ_0; log₂M bits.
3. **Privacy.** Public, data-independent scenario; the answer is a function of all the user's trips into {1..K}; GRR at full ε;
   one report; the fit is post-processing (X1). Option: exponential mechanism with utility range 1 at ε/2, ratio ≤ e^(ε/2) ·
   Z(u')/Z(u) ≤ e^ε (McSherry & Talwar 2007); on a one-hot answer it spends twice the ε that GRR needs.
4. **Server.** Target: 1–3 parameters (speed ratio, length scale or decay, major-road bonus). Response surface P(answer = j | s,
   θ) simulated on the public graph with the same local-fit code and a trips-per-user law (X5), so local-fit noise and clipping
   are inside the model; misclassification-corrected discrete-choice MLE L(θ) = Σ_i log Σ_j GRR(r_i | j) P(j | s_i, θ) with
   the known GRR matrix; a D-optimal scenario design under the public prior, frozen by hash (S1: only the P3 simulator's cited
   constants). Synthesis: the public simulator at θ̂ (Boltzmann router to gravity destinations, public departure prior,
   free-flow × fitted speed ratio × jitter): road-valid and timed. Option at ε 8: the released candidates are timed trips too.
5. **`sequence_log_prob`.** The simulator likelihood at θ̂ (§4.7): log P(O, D) + Σ log steps + floor; time marginalised; caches
   keyed by map, config and θ̂. If the option's released trips are mixed into `generate`, they must enter the likelihood as a
   mixture component, or the MIA audits a different model from the one released (X12).
6. **n = 91.** ε 2: a designed scenario moves one alternative's share by ≈ 0.25 between θ_0 and a plausible θ_1 (a design
   claim); SD 0.074 (R2-E wrote 0.067), so 3.4 SD: one parameter solidly; two parameters on a user split at ±0.104 give 2.4
   SD, marginal. ε 8: GRR noise 0.002, sampling 0.045, so 3–4 scenario families on split users. Option at ε 2: about half of
   one HM number (relative SD of a population direction 0.21 at d = 1, 0.42 at d = 4); at ε 8 a timed public sample (the best
   of M = 16 candidates is chosen ≈ 42 % of the time). n = 10,000: SD 0.005 at ε 2, so 10–25 parameters incl. route tastes.
7. **Difference.** C3 asks "which of K models am I" (hypothesis selection on the user); here the alternatives are actions in
   designed scenarios, and the information per answer is set by design, not by where the user happened to travel. C1 reports
   moments of the trips the user made. Not C5 (no library) and not E.4 (no program slots). C7 (C.4): no knob and no reward,
   but a server-designed query with an RR answer and a parametric response surface is C7's and Zhou & Tan 2021's shape, and
   the reviewer will test it. The option is close to C5 (Cond-C5 not claimed): R2-B and R2-C dropped the same
   exponential-mechanism construction as "C5 in disguise", R2-E kept it (disagreement, not averaged). Closest: PATE (Papernot et
   al. 2017), LDP knowledge distillation (arXiv 2202.02971), FedMD-NFDP (arXiv 2009.05537), Warner 1965, stated-choice design
   (Louviere, Hensher & Swait 2000), misclassified discrete response (Hausman, Abrevaya & Scott-Morton 1998); option: DPMM,
   Takagi et al. 2019, Private Evolution and Sim-PE, posterior sampling (Dimitrakakis et al. 2014; Wang, Fienberg, Smola 2015).
8. **Risks, reviewer.** "LDP distillation with a different query"; route scenarios inherit the matcher's shortest-path bias
   (X13), so at n ≈ 91 use speed, duration, departure and destination scenarios; the response surface needs the trips-per-user
   law and a population law for θ_u; local fits on 2–9 trips are noisy; at n ≈ 91 the speed scenario measures the mode mix
   (X10). Reviewer: information per user against C1's PM moment for the same parameter; D-optimal vs random scenarios; S2 with
   a misspecified within-user model.
9. **Novelty queries.** "local differential privacy stated preference choice experiment"; "randomized response discrete choice
   estimation misclassification"; "local differential privacy knowledge distillation one label per client"; "privacy-preserving
   route choice hypothetical scenarios"; "local exponential mechanism public candidates posterior sampling". Compare: PATE,
   arXiv 2202.02971, Zhou & Tan 2021, Hausman et al. 1998, Private Evolution 2024, Sim-PE 2025.

## K8 Within-user contrasts and couplings
1. **Provenance, pitch.** R2-C.3 (paired twin-rank contrast), R2-A.4 (within-user peak-minus-off-peak contrasts, clock-dependent
   router), R2-E.4 (within-user Spearman sign); R2-D.4 (quadrant of one trip at model medians) enters as the pooled, confounded
   comparison form. User-level LDP can release how a person's own trips differ or co-vary (peak vs off-peak speed, length vs
   departure), which no per-trajectory mechanism can produce even in principle; one categorical item about such a relation
   calibrates a contrast or coupling parameter of the public simulator, free of who travels when.
2. **Report.** A public draw picks one item. (a) R2-C.3: one public-rule eligible pair (a peak trip, 7–9 h or 17–19 h, and an
   off-peak trip in 6–22 h, free-flow route times within × 1.5); each duration ranked among 29 twins personalised by the user's
   own mean log-speed ratio (computed locally); d = rank_peak − rank_off as {d < −10, |d| ≤ 10, d > 10, ⊥}, GRR over 4.
   (b) R2-A.4: c_v = mean log(v_obs/v_ff) at peak minus off-peak, or c_a = arterial share of moving time at peak minus off-peak,
   as {below cut, above cut, undefined} (cuts −0.25, −0.1), GRR over 3. (c) R2-E.4: within-user Spearman correlation (≥ 3
   trips) of (length, peak departure), (length, speed) or (detour, length) as {negative, none, positive} at ±0.3 by GRR (HM on
   the clipped value at ε 8; Duchi is unusable there, X3). (d) R2-D.4: quadrant of one trip's two model-conditional ranks, GRR.
3. **Privacy.** Pair selection (data-dependent), twins, ranks, contrasts and correlations are randomized functions of the user's
   data into public finite domains; GRR/HM at full ε; lift lemma (X1); both trips feed one report; ⊥ and undefined are
   categories. Two bits at ε/2 would be far worse (the concordance of two ε = 1 bits acts as one bit at ε ≈ 0.43, re-checked),
   so a coupling needs one categorical report. (d) takes its medians from an earlier disjoint cohort (K1) or the public prior.
4. **Server.** Debias; eligible-class shares ŝ_c/(1 − ŝ_⊥); the sign balance is an exact test of the prior's period factor,
   and an ordered-probit fit with the public jitter scale gives the log-speed error μ̂ of the peak factor. (b): κ_v (amplitude
   of the cited congestion profile, S1) and κ_a (peak penalty per arterial metre) from a public response table. (c), (d):
   Blomqvist β̂ → Gaussian-copula ρ̂ = sin(πβ̂/2), shrunk to 0. Synthesis on a host (§4 prior walk, K1, K2 or K4): segment
   times = free-flow × prior period factor × exp(μ̂·1[peak]) × jitter; (b) a clock-dependent router with step cost
   ℓ/v(class, t; κ_v) + κ_a·g(t)·ℓ·[arterial] at clock t; copula draws of (period, distance class); road-valid.
5. **`sequence_log_prob`.** (a), (c), (d): the host's, unchanged (marginalising the period restores P(O, D)), so MIA-blind by
   construction. (b) with κ_a: log Σ over 96 quarter-hour start slots π(s0) P(O)P(D|O) Π_i q_{daypart(s_i)}(e_i | node_i, D) +
   floor; 96 × L terms, 5 reverse Dijkstras per destination (≈ 220 s per arm at u182, cached).
6. **n = 91.** Eligibility unknown (0.3–0.6 guessed; ≈ 9 matched trips per user, often all in one period). ε 2: (a) ±0.074 per
   share, ±0.15 per class among eligible users, ±0.23 on the sign balance: only a very large prior error shows; (b) κ_v, κ_a
   stay prior; (c) ≈ 0.075 per share (R2-E wrote 0.05), so "60 % positive" against 33 % is ≈ 3.6 SD, not 5, and the Duchi mean
   form sees a mean coupling of 0.3 at 2.1 SD before dilution by users with < 3 trips; (d) at 45 users the cell SD is ≈ 0.105
   (R2-D wrote 0.07), β ±0.24, ρ ±0.38, so only |ρ| ≳ 0.75 shows. ε 8: one coarse effect (sign balance ±0.14, c_v shares
   ±0.11, ρ ±0.25). n = 10,000: period × road-class contrasts, weekday/weekend, a 3 × 3 copula; κ_v and κ_a to ±0.03.
7. **Difference.** C1 (C.1, E.3) estimates period × road-class speed factors across users, confounded with the mode mix; C3
   gives regime shares only; C4's D.4 relates anchors to build tours, whereas here two trips' prior-relative times identify one
   effect of an unlinked-trip time model, so Cond-C4 is not invoked; couplings do need a joint metric (duration W1 within
   departure period, a 2-D JSD) that does not exist yet, a condition analogous to Cond-C4. Per-trajectory LDP randomizes each
   trajectory separately, so a within-person contrast is impossible there by construction; only (d) could be imitated.
   Closest: Ding et al. 2018 (LDP A/B tests contrast public groups, between users); Kent, Berrett & Yu 2024 (user-level LDP
   rates, no within-user contrasts); Rameshwar et al. 2024, Levy et al. 2021 (central user-level DP); LoPub 2018, CALM 2018
   (correlations among one record's attributes); Blomqvist 1950; Gao, Frejinger & Ben-Akiva 2008; MTNet 2022.
8. **Risks, reviewer.** Low eligibility (n_eff ≈ 30–45); within-user noise (different purposes and modes on different days);
   P2 does not reward de-confounding, so the gain is mostly scientific (a clean congestion effect); a Gaussian copula is
   assumed; it may be called a C1 question family rather than a mechanism. Reviewer: within-user vs pooled (d) on a simulated
   population where who travels when is confounded; the joint metric.
9. **Novelty queries.** "user-level local differential privacy within-user correlation"; "local differential privacy paired
   comparison within subject"; "local differential privacy copula estimation"; "privacy-preserving time-of-day congestion
   effect travel time". Compare: Kent et al. 2024, Ding et al. 2018, LoPub 2018, CALM 2018, Rameshwar et al. 2024, MTNet 2022.

## Cross-cutting findings (V = verified here by algebra or recomputation; C = claim, source named)
- **X1 Lift lemma: privacy of a data-dependent trip choice. V.** If R is ε-LDP on a public finite domain X and f maps the user's
  whole data into X (uniform trip, eligible pair, time-uniform second, rank against device-simulated twins, local fit, public
  default; deterministic or randomized, even data-dependent), then P(y | D) = Σ_x P(f(D) = x)·P(R(x) = y) ≤ max_x P(R(x) = y)
  ≤ e^ε min_x P(R(x) = y) ≤ e^ε P(y | D'). Selection is free for privacy but defines the estimand, so the server must know the
  selection law to debias (K8's eligible pairs). It holds per user in sequentially interactive protocols over disjoint cohorts.
  Domains, thresholds, bins, windows, defaults and question tables must be public and frozen by commit hash (lesson 7). K7's
  exponential-mechanism option needs its own proof (ε/2 tilt).
- **X2 One sampled trip vs Duchi's mechanism on the user's share. V for binary items; C for the variance ratios.** Sampling one
  trip and then binary RR gives P(1) = q + f_u(p − q), which is exactly Duchi's one-bit mechanism on x = 2f_u − 1, because
  (e^ε − 1)/(e^ε + 1) = p − q and ½(1 − (p − q)) = q. For scalar moments, averaging all trips and using PM/HM wins when a
  user's trips differ (R2-C: ≈ 2.7× lower variance at ε 2, 40–150× at ε 8, depending on the unmeasured within-user spread).
  Categorical, structural and joint items need one trip (a user's histogram can only be sampled), which is what the K
  candidates carry; moments stay with C1.
- **X3 Noise corrections. V.** With the exact formula, k shares near 1/k at ε 2 have SD 0.073 (k = 3), 0.074 (4), 0.076 (6),
  0.079 (9). The cheat sheet's ±0.048 for 3 shares is the vanishing-share limit (the randomization-only part at 1/3 is 0.053;
  the sampling term adds the rest). R2-A and R2-C used the exact formula; R2-E.1 and R2-E.2 (0.067 → 0.074), R2-E.4 (0.05 →
  0.075), R2-B.1's fallbacks (0.062 → 0.079, 0.055 → 0.076) and R2-D.4 (cell 0.07 → 0.105 at 45 users) did not. OLH at ε 2:
  0.089 is right for an empty cell; a cell with share 0.35 has ≈ 0.107 (randomization) and ≈ 0.118 with sampling. Duchi at ε 8
  has SD √(C² − x̄²)/√n with C = (e^ε + 1)/(e^ε − 1) → 1, i.e. up to 0.105 at n = 91, not 0.017 (that is HM's value): a one-bit
  output cannot beat the Bernoulli variance, so numeric items at ε 8 use HM or PM. R2-D's binary RR SDs (0.214 / 0.069 /
  0.052) are right. Net effect: detection margins shrink by 10–40 % (K7 3.7 → 3.4 SD; K6 6 → 5.4 SD; K8 (c) 5 → 3.6 SD; K8 (d)
  |ρ| ≥ 0.6 → ≈ 0.75); no verdict flips.
- **X4 Heavy vs light users and user weighting. C (R2-C §0 menu); Kish arithmetic V.** (a) One uniform trip per user (cap
  M = 1): user-weighted estimand, no extra variance; the default at n ≈ 91. (b) Padding and sampling with ⊥ and cap M: capped
  trip-weighted estimand, SD × 1/mean(w_u). (c) A weight-class tag inside the GRR domain. Any trip weighting obeys Kish's
  n_eff = n/(1 + CV²(w)): with CV(m) ≈ 2 (a guess; per-user counts are undocumented) uncapped trip weighting leaves ≈ 18 of 91
  users. R2-C proposes the user-weighted estimand with P2's user-weighted reference and (b) at M = 4 as a sensitivity arm;
  R2-D.2 instead wants a census to set M for a trip-weighted reference; the baseline left the choice open, so it is the
  author's decision. K1's rank is exactly uniform under a correct prior for every m_u (PIT argument, V), so heavy users cannot
  fake a miscalibration there. 'Undefined' as a category (K2-W, K8) avoids a biased default but divides n by the defined share.
- **X5 The chosen design's "public trips-per-user law" is not publicly knowable (R2-D.2). V by reasoning.** The law of matched
  trips per user is set by the cleaning thresholds and the ≈ 10 % match pass rate (baseline §7: 1,770 of 17,313 trajectories;
  per-user counts undocumented), so no cited constant describes it, and fitting it on Geolife would be an unprotected release
  (S1, lesson 7). It feeds C3's confusion matrix, K5's ĥ correction, K6's EPR moments, K7's response surface and every
  default-report dilution. Remedies: ask it inside the report (K6's count class); a census cohort (R2-D.2: 20 users at ε 2 give
  ±0.15 and cost the main cohort SD × 1.13; it pays at ε 8 for a no-trip share ≥ 0.1, at ε 2 only for ≥ 0.3, never at ε 0.5);
  estimators invariant to it (K1); a sensitivity sweep in S2. In the benchmark only users with ≥ 1 matched trip reach `fit`
  (baseline §1), so the no-trip share is 0 by construction there and a census could measure only the shape of the law.
- **X6 `fit` receives only map-matched trips. V by R2-E in code (`orchestrator.py:1503`), consistent with baseline §1 and §7;
  not re-read here.** Every user-level descriptor (K5's modal cell, K6's S and r_g, K8's pairs, K2-W's dwell, which needs the
  next own trajectory) is computed on a ≈ 10 % subsample of each user's trips: S truncated, dwell mostly undefined, few
  eligible pairs. Passing each user's clean views to the device simulation is privacy-neutral (the guarantee covers all of the
  user's data) but a harness change, so it is a prerequisite decision.
- **X7 Control arm "ldptrace lifted to user level" (R2-C §0). V for privacy; C for performance.** One uniformly sampled matched
  trip per user at full user ε through LDPTrace, its grid walk snapped to OSM by the public router, departure and times from the
  public prior; user-level ε-LDP by X1. Every K must beat it and its own prior arm on P2's metrics; it is the comparison a
  CLOSE-VARIANT reviewer asks for first. A second control worth adding (consolidator): `rn_ldp_synth` lifted the same way.
- **X8 Rounds and splits at n = 91 (R2-D §0). V for the binary-RR arithmetic; C for the value of structural choices.** ε 0.5:
  one round; ε 2: at most two cohorts, the second only after saturation; ε 8: no re-centring round (HM is near exact) but one
  structural cohort can pay (e.g. choosing the pedestrian graph layer). Never pays: an ε split across rounds or modules
  (variance ∝ 1/ε²; every brainstormer splits users), refining a categorical domain (AHEAD/C8 zoom), regime-conditional second
  questions, Neyman allocation (< 10 %), three cohorts for one parameter. Adaptivity turns frozen design constants (graph layer,
  regime set, band edges) into measured, protected quantities (lesson 7).
- **X9 Saturation of rank and bit questions: three remedies, not averaged.** R2-C.1: a diffuse mode-mixture prior (then *dur*
  partly re-learns C3's regime shares); R2-D.1: a re-centring second cohort (√2 cost) or ranks under the user's locally chosen
  C3 regime; R2-C.3: personalised twins shifted by the user's own mean log-speed ratio (removes the level, keeps contrasts). The
  choice decides whether K1 differs from C3 at n ≈ 91.
- **X10 Convergence on the mode mix. C (consolidator).** The one item ε 2 can move in K1 (*dur*), K2 (u), K3 (state shares), K7
  (speed scenario), C1 (speed ratio) and C3 (regime) is largely the same quantity, Geolife's walk/vehicle mix and speed level,
  where the public prior is most likely wrong (lesson 10). Utility at n ≈ 91 will therefore not separate these candidates from
  each other or from §4; separation has to come from structure (exact null, time allocation, joint items, route or user
  structure) and from S2 at large n.
- **X11 Benchmark blindness. V for the copy layer; C otherwise.** The MIA reads only the edge likelihood and P2 has single-trip
  marginals. MIA-blind by construction: K1 at n ≈ 91, K8 (a, c, d), K3 without the reach rule, K6's copy layer. Copy-layer
  invariance: copy decisions depend only on indices and counts and redraws use G's own conditionals, so every trip's marginal
  is G. EPR's returns depend on content (visit counts, chained origins), so ρ may change length W1 and OD JSD, but by how much is
  unverified (one hour of public simulation). Couplings need a joint metric, whole users a coherence metric (K6 ships one).
  Conversely, K5 and K4's family C at ε 8 release single users' habits through the likelihood, so the MIA may rise above
  chance there (inside the vacuous e^8 bound).
- **X12 `generate` and `sequence_log_prob` must describe the same edge model. C (consolidator).** Time may be summed out, but a
  component that `generate` emits and the likelihood omits (K7's released trips) makes the MIA audit another object than the
  release.
- **X13 Matcher bias (lesson 4).** It hits K4 (k biased to 1, corridors snapped to arterials), K1's route rank, K7's route
  scenarios and K6's route loyalty. R2-A.4's claim that a within-user contrast cancels it holds only for a bias that is equal at
  peak and off-peak (C).
- **X14 Shared prerequisites and budgets. C (brainstormer estimates).** All K: P1 timed payload, P2 time metrics. K2, K3, K8: a
  cited Beijing time-dependent congestion profile, extracted and frozen. New OSM exports: names/refs (K4 family C), POIs and
  opening hours (K2-W), land-use tags (K5 ablation); footway coverage P9 (K3's walk state, K4's loops, R2-D.1's pedestrian
  layer). Cache budgets at ≈ 40 ms per scipy Dijkstra: K2 ≈ 5 min per arm at u182, K8 (b) ≈ 220 s, K4 anchors ≈ 40 s and 140 MB;
  K6's 17 EPR simulations per arm unmeasured; u20/u50 allow 300 s per attack call.

## Dropped ideas
- R2-D.2 Census-first as a standalone candidate: a prerequisite, not a mechanism (its author agrees); kept as K1's optional
  cohort and as a remedy in X5.
- R2-D.3 Do-no-harm validator as a standalone candidate: a probable CLOSE VARIANT of LDP hypothesis selection (Gopi et al. 2020)
  and of D.3's duel; at n ≈ 91 it certifies only fits that win for ≥ 75 % of users at ε 2 and costs 30 users; kept as an
  optional last cohort for the S2 misspecified run at n ≥ 300.
- R2-E.3 Tilted-prior sampling as a standalone candidate: about half of one HM number at ε ≤ 2, a likely CLOSE VARIANT (C5 with
  graded utility, Private Evolution, posterior sampling), and R2-B and R2-C dropped the same construction independently; kept
  only as K7's ε 8 option.
- R2-A.4's departure-daypart question (Q1): round-1 content (A.1, C.1, D.2, C2's period item); only its contrasts and its clock
  router enter K8.
- Already dropped inside the ideas files (their reasons): private twins (R2-B: an exponential mechanism over user templates puts
  < 1 % of the mass on the true cell at ε 2; GRR per coordinate dominates; a joint template is D.3/C3); "ever visited zone"
  reach bits (R2-B, R2-C: ≈ 10 users per zone, ±0.14 at ε 2; kept as a K6 metric); one exponential-mechanism trip per user over
  the public simulator (R2-C: weaker than one 27-way GRR item, C5/D.1 in disguise, Cond-C5 not met); a public stratum +
  presence + value report (R2-C: PrivKV on a trip alphabet); day sampling (R2-C: a Geolife recording session is not a day, and
  per-day quantities are invisible to unlinked metrics).

## Proposed groups for parallel novelty checks
- G1 LDP statistics and protocol design: K1, K7, K8 (Joseph et al. 2019, Penso et al. 2025, LDP goodness-of-fit, Zhou & Tan
  2021, PATE and LDP distillation, Kent et al. 2024, Ding et al. 2018, LoPub, CALM).
- G2 Time and route generators: K2, K3, K4 (network-time prisms, travel-time budgets, driving cycles, RATR, "Time will not
  tell", DPMM, via-node routing, hot paths).
- G3 Whole users and mobility laws: K5, K6 (EPR, DITRAS, TimeGeo, DP-WHERE, OnTheMap, Acharya et al. 2023, the AAAI coverage
  paper).
