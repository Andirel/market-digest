"""Deterministic thematic tagging from real metadata (company name, sector,
industry). No model calls -- these are transparent keyword rules, so a stock's
tags are reproducible and auditable rather than guessed.

A stock can carry several themes (e.g. NVDA -> AI + Semiconductors).
"""
import re

# theme -> list of lowercase substrings matched against "name | sector | industry".
THEME_RULES = {
    "AI": ["artificial intelligence", " ai ", "machine learning", "generative"],
    "Semiconductors": ["semiconductor", "chip", "foundry", "lithography", "wafer", "gpu"],
    "Cloud": ["cloud", "data center", "datacenter", "hyperscal"],
    "SaaS": ["software", "saas", "application software", "platform"],
    "Cybersecurity": ["cyber", "security software", "endpoint", "firewall", "identity"],
    "Fintech": ["fintech", "payment", "digital bank", "neobank", "financial technology"],
    "EV": ["electric vehicle", " ev ", "battery", "charging", "lithium"],
    "Robotics": ["robot", "automation", "industrial automation"],
    "Quantum": ["quantum"],
    "Nuclear": ["nuclear", "uranium", "reactor"],
    "Defense": ["defense", "defence", "aerospace & defense", "weapon", "missile"],
    "Space": ["space", "satellite", "launch", "orbital"],
    "GLP-1": ["glp-1", "glp 1", "obesity", "diabetes care", "semaglutide", "tirzepatide"],
    "Crypto": ["crypto", "bitcoin", "blockchain", "digital asset", "miner"],
    "Energy": ["oil", "gas", "energy", "petroleum", "refin", "drilling", "pipeline"],
    "Infrastructure": ["engineering & construction", "construction & engineering",
                       "building materials", "heavy machinery", "infrastructure fund"],
    "Biotech": ["biotech", "biopharma", "pharmaceutic", "therapeutic", "genomic"],
}

# Themes implied directly by GICS-style sector, when keywords miss.
_SECTOR_HINT = {
    "Energy": "Energy",
    "Technology": None,  # too broad to tag wholesale
}


def tag(name: str, sector: str = "", industry: str = "") -> list:
    hay = " ".join(x for x in (name, sector, industry) if x).lower()
    hay = f" {re.sub(r'[^a-z0-9- ]', ' ', hay)} "
    found = []
    for theme, kws in THEME_RULES.items():
        if any(kw in hay for kw in kws):
            found.append(theme)
    if not found:
        hint = _SECTOR_HINT.get(sector)
        if hint:
            found.append(hint)
    return found
