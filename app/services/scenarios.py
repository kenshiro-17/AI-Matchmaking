from app.models import Attendee


MAX_SCENARIO_RESULTS = 120
MAX_PAIR_MATCHES_PER_CTO = 2
MAX_TRIAD_FOUNDERS = 40
MAX_TRIAD_GPS = 20
MAX_TRIAD_LPS = 30


def _is_founder(attendee: Attendee) -> bool:
    role = attendee.role.lower()
    return "founder" in role or "ceo" in role


def _is_gp_investor(attendee: Attendee) -> bool:
    role = attendee.role.lower()
    company = attendee.company.lower()
    return ("partner" in role or "invest" in role) and ("vc" in company or "capital" in company)


def _is_lp_profile(attendee: Attendee) -> bool:
    role = attendee.role.lower()
    company = attendee.company.lower()
    return any(x in role for x in ("managing director", "head", "director")) and any(
        x in company for x in ("sovereign", "bank", "fund", "institutional")
    )


def _has_tokens(attendee: Attendee, tokens: tuple[str, ...]) -> bool:
    secondary_goals = attendee.secondary_goals or ""
    blob = " ".join(
        [attendee.focus_text, attendee.seek_text, attendee.offer_text, attendee.primary_goal, secondary_goals]
    ).lower()
    return any(t in blob for t in tokens)


def _bank_compliance_fit(cto: Attendee, bank: Attendee) -> bool:
    return _has_tokens(cto, ("l2", "zk", "compliance", "infrastructure")) and _has_tokens(
        bank, ("bank", "custody", "compliant", "regulatory", "institutional")
    )


def _funding_chain_fit(founder: Attendee, gp: Attendee, lp: Attendee) -> bool:
    founder_ready = _has_tokens(founder, ("investment", "investor", "fundraising", "series", "raise"))
    return founder_ready and _is_gp_investor(gp) and _is_lp_profile(lp)


def strategic_scenarios(attendees: list[Attendee], max_results: int = MAX_SCENARIO_RESULTS) -> list[dict]:
    scenarios: list[dict] = []

    # Scenario type 1: Compliance infrastructure fit for institutional bank.
    ctos = [a for a in attendees if "cto" in a.role.lower()]
    banks = [
        a
        for a in attendees
        if "bank" in a.company.lower() or "digital assets" in a.role.lower()
    ]
    for cto in ctos:
        pair_count = 0
        if not _has_tokens(cto, ("l2", "zk", "compliance", "infrastructure")):
            continue
        for bank in banks:
            if cto.id == bank.id:
                continue
            if _bank_compliance_fit(cto, bank):
                scenarios.append(
                    {
                        "type": "pair_synergy",
                        "title": "Compliance Infrastructure Fit",
                        "participants": [cto.name, bank.name],
                        "explanation": (
                            f"{cto.name}'s compliance-focused infrastructure aligns with {bank.name}'s institutional custody/"
                            "compliant deployment needs."
                        ),
                    }
                )
                pair_count += 1
                if pair_count >= MAX_PAIR_MATCHES_PER_CTO:
                    break
                if len(scenarios) >= max_results:
                    break
        if len(scenarios) >= max_results:
            break

    # Scenario type 2: Funding chain Founder <- GP <- LP
    founders = [a for a in attendees if _is_founder(a) and _has_tokens(a, ("investment", "investor", "fundraising", "series", "raise"))]
    gps = [a for a in attendees if _is_gp_investor(a)]
    lps = [a for a in attendees if _is_lp_profile(a)]
    founder_pool = founders[:MAX_TRIAD_FOUNDERS]
    gp_pool = gps[:MAX_TRIAD_GPS]
    lp_pool = lps[:MAX_TRIAD_LPS]
    for founder in founder_pool:
        for gp in gp_pool:
            if founder.id == gp.id:
                continue
            for lp in lp_pool:
                if lp.id in (founder.id, gp.id):
                    continue
                if _funding_chain_fit(founder, gp, lp):
                    scenarios.append(
                        {
                            "type": "triad_synergy",
                            "title": "Series Pathway Chain",
                            "participants": [founder.name, gp.name, lp.name],
                            "explanation": (
                                f"{gp.name}'s fund can evaluate {founder.name}'s round, with {lp.name} as a strong LP-side"
                                " institutional context bridge."
                            ),
                        }
                    )
                    break
            if len(scenarios) >= max_results:
                break
        if len(scenarios) >= max_results:
            break

    # Remove near-duplicates while preserving order.
    deduped = []
    seen = set()
    for s in scenarios:
        key = (s["type"], tuple(s["participants"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)
    return deduped[:max_results]


def scenarios_for_attendee(attendee: Attendee, attendees: list[Attendee]) -> list[dict]:
    all_scenarios = strategic_scenarios(attendees)
    return [s for s in all_scenarios if attendee.name in s["participants"]]
