# Domain LLM POC — Demo Question Set

> **How to use**: Submit each question below in the Gradio UI. Compare the Standard Model and Specialized Model panels against the **Expected** notes. At least 4 of 5 domain-specific questions should show a clear quality improvement in the Specialized Model panel (SC-001).

---

## Domain-Specific Questions

Questions answerable only from laytime and charterparty expertise. The Specialized Model should clearly outperform the Standard Model here.

1. Under a berth charterparty with a WIBON clause, the vessel arrives at anchorage on Friday at 18:00 and tenders NOR at 18:30. The charterparty provides for a 12-hour turn time and WWDSHEX EIU. When does laytime commence?
   **Expected**: NOR effective at 18:30 Friday (WIBON applies). 12-hour turn time expires 06:30 Saturday. Saturday is a working day (not Sunday/holiday), so laytime commences at 06:30 Saturday — subject to confirming Saturday is not a local public holiday and that no office-hours restriction applies to the turn time.

2. What is the correct sequence of checks when analyzing a Statement of Facts to determine whether a specific interval of time should count as laytime?
   **Expected**: (1) Confirm valid NOR has been tendered and is effective. (2) Confirm laytime has commenced (notice period elapsed). (3) Check if the interval is a SHEX exception (Sunday/holiday) — apply EIU or UU as agreed. (4) Check for weather exception — did weather actually stop operations (WWD)? (5) Check for other exceptions (ship's gear breakdown, force majeure, etc.). (6) If on demurrage, apply 'once on demurrage always on demurrage' — SHEX/WWD do not apply unless the charterparty provides otherwise. (7) Prorate partial-day exceptions. Only after all checks assign the interval as counting or not counting.

3. A charterparty contains the string 'WIPON WIBON WICCON WIFPON' in a rider clause, but the printed GENCON Clause 6 requires the vessel to be in berth before NOR can be tendered. The vessel tenders NOR at anchorage before free pratique is granted. Is the NOR valid?
   **Expected**: Yes. The rider clause prevails over the printed GENCON clause because riders override printed form provisions in case of conflict. WIBON makes NOR valid at anchorage; WIFPON makes NOR valid before free pratique. All conditions of the printed clause are waived by the rider. The NOR is valid and laytime commences after any notice period.

4. Under a WWDSHEX UU charterparty, operations run through a Sunday and loading progresses. A rain stoppage from 10:00 to 14:00 also occurs on the same Sunday. How is the Sunday treated in the laytime calculation?
   **Expected**: The entire Sunday is excluded from laytime under SHEX UU — unconditionally, regardless of whether operations took place. UU means the Sunday exception applies even if used, so neither the operations nor the rain stoppage affects the calculation for that day. The Sunday is simply excluded. The rain stoppage on Sunday is irrelevant — the day is already excepted and there is no 'double exclusion' benefit.

5. The SOF records 'rain' at 13:40 on a Wednesday but no entry stating operations were stopped or suspended. Operations completed later that afternoon. Under a WWDSHEX EIU regime, does the 13:40–completion interval count as laytime?
   **Expected**: Yes, it counts. Under a WWD clause, weather must actually prevent operations for time to be excluded. The SOF records rain but no stoppage of operations — meaning work continued through the rain. Since operations were not suspended, the weather exception is not triggered. The time counts as laytime. The charterer would need additional evidence (surveyor reports, stevedore records) to prove operations were in fact stopped if the SOF does not record it.

---

## Terminology Questions

Questions using laytime-specific terms the base model is unlikely to define correctly without domain training.

1. What is the difference between SHEX EIU and SHEX UU, and which is more favorable to the charterer?
   **Expected**: SHEX EIU (Even If Used) = Sundays and holidays excluded unless operations actually take place on those days — if the vessel is worked, the time counts. SHEX UU (Unless Used) = Sundays and holidays excluded unconditionally even if operations take place. UU is more favorable to the charterer — they can work the vessel on Sundays without it consuming laytime.

2. What does the acronym string 'WIBON WICCON WIFPON' mean and what practical effect does it have on NOR validity?
   **Expected**: WIBON = Whether In Berth Or Not (NOR valid at anchorage). WICCON = Whether In Custom Clearance Or Not (NOR valid before customs entry). WIFPON = Whether In Free Pratique Or Not (NOR valid before health clearance). Combined effect: the master can tender a valid NOR the moment the vessel anchors in the port, before any port authority formalities are completed. This is the broadest NOR trigger string and protects the shipowner by starting the laytime clock at the earliest possible moment.

---

## General Sanity-Check Questions

Not domain-specific. Both models should answer reasonably. Used to verify fine-tuning did not degrade general capability (SC-006).

1. What is the capital of France?
   **Expected**: Both panels answer "Paris" or equivalent — verifies no catastrophic forgetting.

2. Explain what a neural network is in simple terms.
   **Expected**: Both panels give a reasonable, jargon-free explanation — tests general language capability.

---

*Question set covers laytime commencement logic, SOF analysis sequence, NOR validity under WIBON/WIFPON, SHEX UU vs EIU interaction with weather, and key acronym definitions. Satisfies FR-008 and spec.md §SC-001, §SC-006.*
