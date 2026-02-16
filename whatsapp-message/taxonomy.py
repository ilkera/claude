from __future__ import annotations

ECONOMIC_CATEGORIES: dict[str, list[str]] = {
    "Trade & Tariffs": [
        "Tariff Announcements/Threats",
        "Trade Deals/Negotiations",
        "Sanctions",
        "Import/Export Restrictions",
        "Country-Specific Trade (China, EU, etc.)",
    ],
    "Monetary Policy & The Fed": [
        "Interest Rate Commentary",
        "Fed Chair Criticism/Praise",
        "Inflation",
        "Dollar Strength/Weakness",
        "Quantitative Easing/Tightening",
    ],
    "Tax Policy": [
        "Corporate Tax",
        "Individual Tax Cuts/Hikes",
        "Capital Gains",
        "Tax Incentives/Credits",
        "Estate Tax",
    ],
    "Stock Market & Equities": [
        "General Market Commentary",
        "Specific Company Callouts",
        "Sector Remarks (Tech, Energy, Defense, Pharma)",
        "IPO/Listing Commentary",
    ],
    "Housing & Real Estate": [
        "Mortgage Rates",
        "Housing Affordability",
        "Construction/Development Policy",
        "Fannie Mae/Freddie Mac",
        "Rent Control",
    ],
    "Government Spending & Fiscal Policy": [
        "Budget Proposals",
        "Debt Ceiling",
        "Deficit Commentary",
        "Infrastructure Spending",
        "DOGE/Cost-Cutting Initiatives",
        "Government Shutdowns",
    ],
    "Industry & Sector Regulation": [
        "Energy/Oil & Gas",
        "Banking/Financial Regulation",
        "Tech/Antitrust",
        "Pharma/Drug Pricing",
        "Auto Industry",
        "Crypto/Digital Assets",
    ],
    "Jobs & Labor": [
        "Employment Numbers",
        "Wage Commentary",
        "Immigration Impact on Labor",
        "Manufacturing Jobs",
        "Union-Related",
    ],
    "International Economic Relations": [
        "BRICS/De-dollarization",
        "Foreign Investment",
        "Bilateral Economic Relationships",
        "NATO Spending/Burden-Sharing",
    ],
    "Crypto & Digital Assets": [
        "Bitcoin/Crypto Endorsements",
        "Regulatory Stance",
        "CBDCs",
        "Specific Token Mentions",
    ],
}

NON_ECONOMIC_CATEGORIES: list[str] = [
    "Immigration & Border",
    "Foreign Policy & Military",
    "Legal & Judicial",
    "Elections & Politics",
    "Culture War & Social Issues",
    "Personal & Self-Promotion",
    "Law Enforcement & Crime",
    "Healthcare",
    "Energy & Environment (Non-Economic)",
]


def get_taxonomy_text() -> str:
    """Format the full taxonomy as human-readable text for prompt injection."""
    lines = ["ECONOMIC CATEGORIES:"]
    for category, subcategories in ECONOMIC_CATEGORIES.items():
        lines.append(f"  {category}:")
        for sub in subcategories:
            lines.append(f"    - {sub}")
    lines.append("")
    lines.append("NON-ECONOMIC CATEGORIES:")
    for category in NON_ECONOMIC_CATEGORIES:
        lines.append(f"  - {category}")
    return "\n".join(lines)
