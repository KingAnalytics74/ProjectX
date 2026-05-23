"""
One-time script: populates risk_assessments.csv with all 10 BFH hazards
from the NEBOSH IG2 assessment (Beto Farm Holding Ltd, Akure, Nigeria).
Run from the project root:  python3 seed_bfh.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from data_manager import COLUMNS, classify_risk

DATA_FILE = "risk_assessments.csv"

COMMON = {
    "assessor":   "Babatope Bakare",
    "department": "Operations",
    "location":   "Beto Farm Holding Ltd — Field & Processing Plant, Akure, Nigeria",
    "date":       "2021-04-14",
    "review_date": "2022-04-14",
    "status":     "Open",
    "last_edited_by": "",
    "last_edited_at": "",
}

HAZARDS = [
    # ── H1 · Hazardous Substances ──────────────────────────────────────────
    {
        "hazard_category":    "Chemical / COSHH",
        "hazard_description": (
            "Use of methyl bromide and peracetic acid (PAA) in crop spraying "
            "and processing plant. Workers spraying indiscriminately without "
            "adequate PPE or formal training. Minimum 3 spray cycles per 2 months, "
            "each lasting 2–3 hours."
        ),
        "activity":    "Crop spraying and processing plant preservation",
        "who_harmed":  (
            "Field and processing plant workers — inhalation of methyl bromide "
            "and PAA causes nausea, fatigue, mental impairment, and neurological "
            "effects. High concentrations can cause pulmonary injury and death."
        ),
        "likelihood": 4, "severity": 5,
        "existing_controls": (
            "Some farm spraying PPE available but insufficient for the number of "
            "workers on the ground. No formal COSHH assessment or training in place."
        ),
        "further_controls": (
            "Full PPE ensemble (coverall, gloves, goggles, boots) mandatory for all "
            "spraying activities; formal COSHH risk assessment; structured chemical "
            "handling training programme; fit-tested RPE (FFP3 or full-face) for "
            "processing workers; hazard warning signage at entry points."
        ),
        "action_timescale":   "1–2 months",
        "responsible_person": "Assistant Manager / Store Manager",
        "residual_likelihood": 2, "residual_severity": 3,
    },

    # ── H2 · Working at Height ─────────────────────────────────────────────
    {
        "hazard_category":    "Working at Height",
        "hazard_description": (
            "Workers accessing fragile roofing structures via ladders. Many "
            "structures are not weight-bearing and are easily lifted by wind. "
            "No edge protection, fall arrest systems, or permit-to-work controls."
        ),
        "activity":    "Roof access and maintenance",
        "who_harmed":  (
            "Workers ascending ladders or walking on damaged roofs — risk of "
            "fatal falls causing death, multiple fractures, paralysis, or brain damage."
        ),
        "likelihood": 4, "severity": 5,
        "existing_controls": (
            "Roof access is informally discouraged. No physical fall protection, "
            "permit-to-work system, or formal WAH assessment in place."
        ),
        "further_controls": (
            "Implement Permit-to-Work system for all roof access; install perimeter "
            "edge protection on all rooflines; provide roofing ladders and crawl boards "
            "to distribute load across fragile surfaces; conduct formal Working at "
            "Height risk assessment; inspect all roof structures annually."
        ),
        "action_timescale":   "2 months",
        "responsible_person": "Store Manager",
        "residual_likelihood": 2, "residual_severity": 4,
    },

    # ── H3 · Work Equipment & Machinery ───────────────────────────────────
    {
        "hazard_category":    "Machinery / Equipment",
        "hazard_description": (
            "Agricultural tractor operation on rough terrain — risks include "
            "run-over, entanglement in PTO shaft, rollover on inclines, and "
            "being struck by the vehicle during mounting/dismounting."
        ),
        "activity":    "Ploughing, harrowing, and farm transport",
        "who_harmed":  (
            "Tractor operators and nearby field workers — being struck or run "
            "over by vehicle can cause death, crush injuries, or multiple fractures."
        ),
        "likelihood": 3, "severity": 5,
        "existing_controls": (
            "Safe stop procedure enforced before leaving vehicle; competent "
            "operators only; mounting/dismounting a moving tractor prohibited; "
            "workers with loose clothing, long chains, or long hair barred from operating."
        ),
        "further_controls": (
            "Provide hi-vis clothing for all field workers; introduce pre-use "
            "inspection checklist for tractor and attachments; define and enforce "
            "exclusion zones around operating machinery; produce written Safe System "
            "of Work (SSOW); record and verify operator competency."
        ),
        "action_timescale":   "1 month",
        "responsible_person": "Farm Manager",
        "residual_likelihood": 2, "residual_severity": 4,
    },

    # ── H4 · Poultry Dust / Airborne Particles ────────────────────────────
    {
        "hazard_category":    "Dust / Airborne Particles",
        "hazard_description": (
            "High concentrations of organic dust (feathers, faecal matter, "
            "endotoxins, microorganisms) in poultry houses during bedding, "
            "populating, routine maintenance, catching/depopulation, litter "
            "removal, and post-depopulation cleaning."
        ),
        "activity":    "Poultry house operations — bedding, cleaning, depopulation",
        "who_harmed":  (
            "All poultry farm workers — chronic inhalation causes asthma, "
            "occupational hypersensitivity pneumonitis, and lung function "
            "impairment. Acute exposure causes respiratory irritation."
        ),
        "likelihood": 4, "severity": 4,
        "existing_controls": (
            "Basic surgical masks worn by some workers during cleaning. "
            "No formal respiratory protection programme in place."
        ),
        "further_controls": (
            "Issue fit-tested FFP2/FFP3 RPE to all workers in poultry houses; "
            "introduce wet-suppression methods during litter removal; "
            "install mechanical ventilation in enclosed houses; "
            "establish health surveillance programme (baseline and periodic spirometry); "
            "provide dust awareness training."
        ),
        "action_timescale":   "2 months",
        "responsible_person": "Farm Manager",
        "residual_likelihood": 2, "residual_severity": 3,
    },

    # ── H5 · Livestock Handling ───────────────────────────────────────────
    {
        "hazard_category":    "Livestock / Animal Handling",
        "hazard_description": (
            "Cattle roaming freely across the farm with no containment facilities. "
            "Workers and veterinary staff approach animals in an uncontrolled "
            "environment, particularly during milking, veterinary procedures, "
            "and herding — when cattle are most aggressive."
        ),
        "activity":    "Cattle herding, milking, and veterinary treatment",
        "who_harmed":  (
            "Workers and veterinary staff — cattle kicks to the head or chest "
            "can cause brain, heart, or lung trauma. Handlers can be pinned, "
            "crushed, or suffer cuts, bruises, fractures, sprains, and strains "
            "from butting."
        ),
        "likelihood": 5, "severity": 4,
        "existing_controls": (
            "Aggressive cattle culled reactively; only experienced workers handle "
            "cattle during milking and oestrus; cattle allowed to range on large "
            "open land to reduce concentration."
        ),
        "further_controls": (
            "Construct purpose-built cattle handling facility comprising collecting "
            "pen, forcing pen, race, and head restraint — designed to ILO code of "
            "practice standards; install gating to prevent forward charge during "
            "veterinary procedures; develop written SSOW for all livestock activities; "
            "formal training and retraining programme for all handlers."
        ),
        "action_timescale":   "4 months",
        "responsible_person": "Farm Manager / Assistant Manager",
        "residual_likelihood": 2, "residual_severity": 3,
    },

    # ── H6 · Whole-Body Vibration ─────────────────────────────────────────
    {
        "hazard_category":    "Noise & Vibration",
        "hazard_description": (
            "Whole-body vibration (WBV) from operating tractor over rough, "
            "uneven terrain during land preparation activities (ploughing, "
            "harrowing) and carrying farm utilities. Tractor used daily for "
            "an average of 2 hours."
        ),
        "activity":    "Tractor operation — ploughing, harrowing, carrying loads",
        "who_harmed":  (
            "Tractor operators — prolonged WBV exposure causes lower back pain, "
            "abdominal, chest and testicular pain, increased stress and tension, "
            "spinal deformation, localised fatigue, and permanent disability."
        ),
        "likelihood": 4, "severity": 3,
        "existing_controls": (
            "Regular preventive maintenance administered to the tractor; "
            "exposure limited by rotating workers between driving and other activities."
        ),
        "further_controls": (
            "Assess daily vibration exposure against EAV (0.5 m/s²) and ELV "
            "(1.15 m/s²) limits; implement health surveillance for exposed operators; "
            "provide operator training on vibration risks and driving technique; "
            "plan procurement of low-vibration replacement tractor."
        ),
        "action_timescale":   "1–2 months",
        "responsible_person": "Supervisor / Farm Manager",
        "residual_likelihood": 2, "residual_severity": 2,
    },

    # ── H7 · Noise ────────────────────────────────────────────────────────
    {
        "hazard_category":    "Noise & Vibration",
        "hazard_description": (
            "Sustained noise exposure from old tractor engine (elevated output "
            "due to age and wear) and high-density poultry farm operations "
            "including feed trucks, loading equipment, bird vocalisations, "
            "and clean-out machinery."
        ),
        "activity":    "Tractor operation and poultry farm work",
        "who_harmed":  (
            "Tractor operators and poultry farm workers — noise-induced hearing "
            "loss (NIHL), inability to hear approaching vehicles or warning "
            "signals, reduced concentration, and psychological stress from "
            "prolonged high noise exposure."
        ),
        "likelihood": 4, "severity": 3,
        "existing_controls": (
            "Rota system limits individual exposure to tractor driving; "
            "ear muffs mandatory for old tractor operator; time in poultry "
            "farm limited; all farm equipment regularly maintained."
        ),
        "further_controls": (
            "Conduct noise exposure assessment across all work areas; "
            "designate and sign hearing protection zones; plan procurement "
            "of low-noise tractor; formal hearing protection programme."
        ),
        "action_timescale":   "3 months",
        "responsible_person": "Farm Manager",
        "residual_likelihood": 2, "residual_severity": 2,
    },

    # ── H8 · Health, Welfare & Work Environment ───────────────────────────
    {
        "hazard_category":    "Welfare / Work Environment",
        "hazard_description": (
            "Field workers exposed to high ambient temperatures and direct "
            "sunlight during extended outdoor agricultural operations. "
            "Separately, improper fertiliser storage creates a fire and "
            "contamination risk."
        ),
        "activity":    "All outdoor field operations; fertiliser storage and handling",
        "who_harmed":  (
            "All field workers and visiting professionals (veterinary, contractors) "
            "— heat rash, heat cramps, heat exhaustion, and potentially fatal "
            "heat stroke. Improper fertiliser storage risks fire, explosion, "
            "and waterway contamination."
        ),
        "likelihood": 3, "severity": 4,
        "existing_controls": (
            "Workers advised to hydrate frequently and rest when experiencing "
            "heat illness symptoms; fertiliser stored away from water courses "
            "and combustion materials; storage marked with hazard warnings; "
            "sex-segregated welfare and changing facilities provided."
        ),
        "further_controls": (
            "Issue sun-protective PPE (wide-brim hats, UV-resistant coveralls) "
            "to all field workers; introduce structured rest/shade breaks during "
            "peak heat hours; monitor workers for heat illness symptoms; "
            "formalise fertiliser storage inspection regime."
        ),
        "action_timescale":   "3 weeks",
        "responsible_person": "Supervisor",
        "residual_likelihood": 2, "residual_severity": 2,
    },

    # ── H9 · Violence at Work ─────────────────────────────────────────────
    {
        "hazard_category":    "Violence & Aggression",
        "hazard_description": (
            "Risk of verbal abuse, threatening behaviour, intimidation, "
            "physical assault, and property damage within the workforce "
            "and towards visitors — including shoving, punching, "
            "condescending language, and destruction of property."
        ),
        "activity":    "All workplace interactions — workers, supervisors, visitors",
        "who_harmed":  (
            "All workers, supervisors, and visitors — physical injury, "
            "psychological trauma, post-traumatic stress, and death in "
            "extreme cases."
        ),
        "likelihood": 3, "severity": 3,
        "existing_controls": (
            "Written behaviour policy defining conduct considered "
            "unacceptable by management; clear reporting structure for "
            "violence incidents."
        ),
        "further_controls": (
            "Conflict resolution and de-escalation training for supervisors; "
            "formal incident reporting and investigation procedure; "
            "lone worker protocol for roles with elevated exposure; "
            "anonymous reporting channel."
        ),
        "action_timescale":   "Ongoing",
        "responsible_person": "Farm Manager",
        "residual_likelihood": 2, "residual_severity": 2,
    },

    # ── H10 · Manual Handling ──────────────────────────────────────────────
    {
        "hazard_category":    "Manual Handling",
        "hazard_description": (
            "Repetitive and heavy lifting, carrying, pushing, pulling, and "
            "lowering of farm produce (sacks, bales), bagged chemicals, "
            "fertiliser, hay bales, and farm implements — often in awkward "
            "postures or over long distances."
        ),
        "activity":    "Harvesting, loading, and handling of farm produce and inputs",
        "who_harmed":  (
            "Field and processing plant workers — musculoskeletal disorders "
            "(MSDs) affecting the back, shoulders, and upper limbs; acute "
            "strains, sprains, and disc injuries from heavy or repetitive loads."
        ),
        "likelihood": 3, "severity": 3,
        "existing_controls": (
            "Tractor and mechanical handling aids used where accessible; "
            "manual tasks avoided where possible; where unavoidable, basic "
            "control measures in place."
        ),
        "further_controls": (
            "Deliver manual handling training to all workers — with emphasis "
            "on areas inaccessible to mechanical aids; carry out ergonomic "
            "assessment of high-frequency repetitive tasks; consider use of "
            "team lifting, trolleys, or conveyor systems for heavy loads."
        ),
        "action_timescale":   "3 weeks",
        "responsible_person": "Assistant Manager",
        "residual_likelihood": 2, "residual_severity": 2,
    },
]


def build_entry(i, h):
    entry = {**COMMON, **h}
    entry["id"]                  = i + 1
    entry["risk_score"]          = entry["likelihood"] * entry["severity"]
    entry["residual_risk_score"] = entry["residual_likelihood"] * entry["residual_severity"]
    entry["risk_level"], _       = classify_risk(entry["risk_score"])
    entry["residual_risk_level"], _ = classify_risk(entry["residual_risk_score"])
    # ensure all columns present
    for col in COLUMNS:
        entry.setdefault(col, "")
    return {col: entry[col] for col in COLUMNS}


def main():
    rows = [build_entry(i, h) for i, h in enumerate(HAZARDS)]
    df   = pd.DataFrame(rows)

    out = os.path.join(os.path.dirname(__file__), DATA_FILE)
    df.to_csv(out, index=False)
    print(f"✅  Written {len(df)} BFH hazard records → {out}")
    for _, r in df.iterrows():
        print(f"  [{int(r['id']):2d}] {r['hazard_category']:<30}  "
              f"Score {int(r['risk_score']):>2} ({r['risk_level']:<9})  "
              f"→ Residual {int(r['residual_risk_score'])} ({r['residual_risk_level']})")


if __name__ == "__main__":
    main()
