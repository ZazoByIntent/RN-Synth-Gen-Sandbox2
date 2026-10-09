# Objection round: the authors' rebuttals (verbatim, 2026-10-09)

The evaluator's objections are in `40_evaluation.md` §5. Each rebuttal comes from the
brainstormer whose raw idea is the candidate's core. The evaluator answers them in
`40_evaluation.md` §6 and writes `45_digest.md`. Also relevant: the T6 addendum in
`30_novelty_G3.md` (T6's core report and estimator EXIST, Liu, Hu and Kong, ICML 2024,
now high confidence; T6 as a whole CLOSE VARIANT, high confidence; the only possible
novelty of T6, R3-C4's certified W1 release, is at most a NOVEL COMBINATION with low
confidence; new close work Hu and Liu, ICML 2026 poster, multi-category CDF under
asymmetric local privacy, abstract only).

## T1 Opportunity-rank destination law (author of R3-C2 ORC)

O1, the users with no eligible trip and the weak gate: ACCEPTED. I switch to one
uniformly drawn eligible trip's PIT tercile plus a ⊥ class, sent by GRR over 4 at
ε ≤ 2. At ε 8 the item becomes 6 classes plus ⊥, GRR over 7.
- Why it costs no variance at ε 2: the tercile balance P(u > 2/3) − P(u ≤ 1/3) moves
  −0.64 per unit κ, against −0.50 for HM's mean. That offsets HM's averaging gain.
  SD(κ̂) at κ = 1 is 0.21 against HM's 0.22 at d = 0. At d = 0.3 it is 0.27 and
  unbiased, against HM's 0.31 with a bias of −0.39. Because ⊥ is its own class, the
  shares among eligible users carry no attenuation.
- Gate: under the null the three eligible classes have equal report probabilities
  whatever d and the trip counts. Given their total, their counts are exactly
  Multinomial(1/3, 1/3, 1/3). The level is exact and the power is CLT-like, so the
  Hoeffding gate goes.
- Price: at ε 8, HM's averaging would roughly halve the SD of ln ρ̂ (about 0.1
  against 0.19–0.22), but only with the unknown (1 − d) bias. I accept that loss. If
  any HM report survives (for example in T5), its gate should be a testing-by-betting
  gate (Waudby-Smith and Ramdas 2024). That gate keeps an exact level when every
  user's output has mean 0 under the null, and its power is near the CLT test's.
- K1's report form: the carrier is now K1's, on purpose, because it is the smallest
  carrier with an exact null. The substance differs in four ways. (i) The ranked
  component is the destination given the origin, which K1 never ranks. (ii) The PIT
  is exact from one public forward Dijkstra, with no simulated twins. (iii) The
  estimate enters P(d | o) at n = 91, so the MIA sees it. (iv) The estimator is
  origin-pivotal and closed-form. Novelty rests on the statistic, the law and that
  estimator; "narrow" stays the honest label.

O2, the radius behind m_o: PARTLY ACCEPTED, with a third fix instead of a citation or
the rank law. The scale becomes the estimand: m = ρ·c₀, one constant opportunity
mass, so the radius disappears. The shape stays the radiation law's published form
P(S > s) = m/(m + s) (Simini 2012).
- Under the prior, u = s/(c₀ + s) is uniform from every origin. The class
  probabilities are 1/(1 + 2ρ) for the lowest tercile and ρ/(ρ + 2) for the highest,
  the same from every origin, so the estimator stays origin-pivotal. The balance
  moves 0.44 per unit ln ρ, so SD(ln ρ̂) at ε 2 is 0.30 at d = 0 and 0.38 at d = 0.3.
- Honest result: a factor-2.5 error in median reach sits at 2.3 SD at d = 0.3; a
  factor 2 only at 1.8 SD.
- c₀ now only centres the prior arm and the null. It still needs a cited Beijing
  trip-distance figure (candidate: the CAUPD–Baidu commuting monitoring report, to be
  verified), frozen by hash, but it needs no precision.
- T1-e: the one number fixes the median reach, which drives length W1 and the 3 × 3
  OD JSD; the tail follows the published 1/s law. At ε 8 the 6-class item identifies
  scale and tail exponent κ jointly from the same report. The Noulas rank law is not
  needed: with α = 0.84 < 1 its scale sits in the map's total mass, so it is not
  scale-free either.

Still unresolved: (1) whether the radiation shape fits mixed-mode sessions can show
only in Geolife's length W1, not in P6; the family choice stays the largest
unverified prior decision (Lenormand 2016 favours gravity for commuting); (2) a
commute-based c₀ can make the prior arm poor at ε 0.5; (3) loops before P10 have
u ≈ 0 and pull ρ̂ down; (4) at ε 2 the reach may still be the walk/vehicle mix (X10),
so T1 needs a head-to-head with C2's band item; (5) the ε-8 SD loss against HM.

## T3 Within-trip segment-time contrasts (author of R3-D3 Frontage clock)

(a) Partly accepted. The sign test is exact only if the two windows of a pair are
interchangeable when frontage has no effect. Junctions break this: their delay is a
fixed wait, which is a bigger share of a fast trip, so the walk/car mix comes back. I
drop the junction covariate and with it the numeric junction form, which is a close
variant of Roth and Avella-Medina Cor. 6.8 and also blind to the MIA. Only the
categorical paired frontage form remains.
Fix: pair only junction-free 100 m mid-block windows of matched length, of one
road-class group, inside one trip and at most 3 minutes apart. Each window is trimmed
40 m at every node and 80 m upstream of signals. No signal wait then sits on either
side. If frontage changes nothing, the two windows are interchangeable for any mix of
fixed and proportional delays and for any mode. The conditional binomial test
therefore stays exact: the "+" count among "±" reports is Binomial(m, 1/2), because
GRR's false-report probability is the same for both signs.
Bias and variance: the trim removes the mode-dependent bias where it arises and keeps
the per-pair SD near 0.5 nat. But short blocks drop out and the ⊥ share rises, so the
fix buys exactness, not power. γ = 0.15 nat stays at 2.0–2.5 SD (⊥ share 0.5 to 0.3,
the evaluator's numbers), and γ = 0.10 nat stays below 2 SD.
Public check before the freeze (about one hour, P3 only, no Geolife data): draw
20,000 P3 routes over the Geolife bounding box in a walk regime and a car regime;
group them into users of m ∈ {1, 3, 9, 30} routes, because the trips-per-user law is
not public (F2). Output: the ⊥ share and distinct-pair counts per m; the test's
false-rejection rate at n = 91 with cited signal waits, queue spill-back and a car
share from 0 to 100 %; the same with junction zones kept, as a negative control whose
false-rejection rate should grow with the car share; and the power at
γ ∈ {0.05, 0.10, 0.15}.
Pre-registered rule: keep shop and retail frontage (OSM land use plus shop/amenity
points) if the ⊥ share at m = 9 is at most 0.5 and the false-rejection rate stays at
most 0.06 for every car share. Otherwise switch once to the better-mapped
built-frontage layer (any OSM building within 30 m, against walls, parks and fences).
If neither passes, T3 becomes a large-n module shown only in the P6 recovery
simulation.
Unresolved for (a): the real ⊥ share on Geolife. Frontage is confounded with unmapped
street features such as parking and lane width, so the test is exact for a slowdown
that goes with frontage, not for a causal one; this is harmless for synthesis. Peak
queues longer than the trim remain a risk. The size of γ̂ (not the test) still
depends on the public noise scale.

(b) Partly accepted. The metric is frozen before any result and computed the same way
for every arm (the prior arm, T1, T2, C1 and K1). It is the W1 distance between
window speeds on 100 m mid-block windows, comparing synthetic times (P1) with
held-out test-split matched trips, with a bootstrap over users. It is reported per
OSM road-class group, signalised versus not, and the frozen frontage class. A second
number is the W1 of the within-route spread of log window speeds, which no uniform
rescaling such as K1's can move. The road-class and signal strata are built-in
controls. T3 should beat its prior arm only in the frontage stratum and in the
within-route spread; a gain in the controls would point to an artefact.
Claim: I accept the label "K8 extended from across-trip to within-trip contrasts on
an edge covariate" (R2-A.4's report form, K8 item a's server), and the paper will say
so. What it adds beyond that: (1) a new estimand on a part of the model neither round
touches, the time structure of segments inside a route (R1); (2) inside one trip the
mode and the trip's own speed level cancel by design, which K8's peak/off-peak pair of
two trips (possibly in two modes) cannot do, so T3 is the only round-3 estimand that
does not end up measuring the walk/car mix (X10, Y7); (3) the exact null needs no
twins and no trips-per-user law; (4) the estimate changes segment times and router
costs, so routes change, whereas K8 only shifts whole-trip durations.
Against the strict reading of Roth and Avella-Medina Cor. 6.10: a per-user regression
slope cancels neither each trip's speed level nor mode switches within a user, has no
exact null, and feeds no synthesizer.
Unresolved for (b): the gain shows only on a metric family added for the time side;
it is pre-registered and mechanism-independent, but it is new. The held-out window
speeds rest on the same noisy interpolation. The MIA sees γ̂ only weakly, through
router costs; a time-aware MIA (P8) would be the real test. Novelty stays at "novel
combination", not a new protocol.

## T2 Hierarchy-ceiling route law (author of R3-A1 Apex ceilings)

O1 (estimate and test depend on the origin–destination law): PARTLY ACCEPTED. The
flaw is real in the written version, and the fix below makes both the test and the
estimate exact using public structure only.
Fix ("equalized operating point"): for its own (O, D) the device computes exactly, by
K-γ's absorbing-chain solve (seconds per trip), the probability s_t that P3's router
stays below the shortest path's top band. It computes the same probability s_l under
the public low-ceiling mixture. It then sends Z = 1 with probability a + b·1[δ ≥ 1],
with a and b set so that P(Z = 1) is α under "no ceiling" and β under "low ceiling".
α and β are the same public numbers for every context, e.g. (0.15, 0.9).
Eligible trips are those whose (O, D) makes this feasible, decided from (O, D) alone.
Then E[Z | eligible] = α + (β − α)·ρ̄ exactly, for any O–D law and any trips-per-user
law. So the gate (ρ = 0 gives E[Z] = α) and ρ̂ = (Ẑ − α)/(β − α) are both exact.
Eligibility by (O, D) is harmless because the law holds exactly inside each context
(X6 does not apply).
Variance: GRR over {1, 0, ⊥} at ε 2 and d = 0.3 gives ≈ 0.096 on E[Z], so
SD(ρ̂) ≈ 0.096/0.75 ≈ 0.13 against ≈ 0.15 for the biased version. The only cost is
randomizing down to the weakest eligible context. This is not K1's form (no rank,
twins or PIT): it is a Neyman–Pearson randomization to a fixed public size and power
per trip. It applies F2's "public confusion matrix by construction" principle to the
O–D context instead of the trip count.
Unresolved for O1: the null is still "P3's router is right". A wrong public
temperature shifts s_t and can reject with no ceiling present. I would bound this
with a pre-freeze run over the cited temperature range (worst-case α). Also, the GPS
guard must become a filter on the GPS record alone, because a filter on the route
breaks exactness.

O2 (artefacts; versus C3; if OSM classes tie with CH bands): PARTLY ACCEPTED. Fix:
measure the deficit against the trip's length-shortest path, not the car-fastest one,
and send only the avoidance indicator δ ≥ 1.
- Time-seeking cars climb above that path's apex and walkers follow it, so neither
  reads as "below"; the walker bias from car-fastest paths disappears.
- HMM matchers fill gaps with length-shortest paths (still to verify in the repo's
  matcher), and walkers matched onto an arterial of that path also give δ = 0. So the
  named artefacts now push toward the null: ρ̂ is attenuated, not inflated, and P6's
  gap-fill run measures by how much.
- Versus C3: at ε 2, C3's signal is a speed-driven regime mix, and routes stay each
  regime's prior. T2's report never reads time. The pre-registered check on the same
  users is whether C3's fitted mix (oracle arm) predicts T2's avoidance share. If it
  does, T2 adds nothing on Geolife (X10), and we say so.
- If OSM classes tie with CH bands: accepted that the hierarchy is then not the
  contribution. What remains is the exact equalized report plus the nested-ceiling
  likelihood with public caches, i.e. C1's direction with a different estimator and
  likelihood family (novelty ≈ 2.5). We would then ship OSM classes and skip the CH
  build, which helps benchmark fit.
- Kaplan–Meier at ε 8: accepted as published (Egéa and Escobar-Bach 2023). It becomes
  a cited tool, not a claim.
Unresolved for O2: whether the avoidance share differs from the prior at all
(unverified until s_t is simulated on the public graph), campus and park footpaths
missing from the graph (P9), and ties in the gap-fill paths, which can rarely create a
false "below". The n = 91 signal stays weak (S 2, one number needing ρ ≥ 0.26 for
2 SD).
