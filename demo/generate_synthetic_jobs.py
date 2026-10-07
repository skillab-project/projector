#!/usr/bin/env python3
"""Generate a deterministic, region-aware synthetic Tracker jobs dataset."""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path


SKILL_BASE = "http://data.europa.eu/esco/skill"
OCCUPATION_BASE = "http://data.europa.eu/esco/occupation"
NACE_BASE = "http://data.europa.eu/ux2/nace2.1"


def skill_uri(slug: str) -> str:
    return f"{SKILL_BASE}/demo-{slug}"


def occupation_uri(slug: str) -> str:
    return f"{OCCUPATION_BASE}/demo-{slug}"


SKILLS = {
    skill_uri("python"): "Python",
    skill_uri("sql"): "SQL",
    skill_uri("data-analysis"): "data analysis",
    skill_uri("artificial-intelligence"): "artificial intelligence",
    skill_uri("machine-learning"): "machine learning",
    skill_uri("pytorch"): "PyTorch",
    skill_uri("cloud-computing"): "cloud computing",
    skill_uri("docker"): "Docker",
    skill_uri("kubernetes"): "Kubernetes",
    skill_uri("cybersecurity"): "cybersecurity",
    skill_uri("software-development"): "software development",
    skill_uri("git"): "Git",
    skill_uri("agile-methods"): "agile methods",
    skill_uri("financial-analysis"): "financial analysis",
    skill_uri("risk-management"): "risk management",
    skill_uri("business-intelligence"): "business intelligence",
    skill_uri("manufacturing-processes"): "manufacturing processes",
    skill_uri("automotive-engineering"): "automotive engineering",
    skill_uri("industrial-automation"): "industrial automation",
    skill_uri("quality-control"): "quality control",
    skill_uri("cad"): "computer-aided design",
    skill_uri("project-management"): "project management",
    skill_uri("consulting"): "management consulting",
    skill_uri("stakeholder-management"): "stakeholder management",
    skill_uri("sustainability"): "sustainability",
    skill_uri("renewable-energy"): "renewable energy",
    skill_uri("carbon-accounting"): "carbon accounting",
    skill_uri("circular-economy"): "circular economy",
    skill_uri("healthcare-management"): "healthcare management",
    skill_uri("patient-care"): "patient care",
    skill_uri("public-administration"): "public administration",
    skill_uri("policy-analysis"): "policy analysis",
    skill_uri("tourism-management"): "tourism management",
    skill_uri("customer-service"): "customer service",
    skill_uri("hospitality"): "hospitality operations",
    skill_uri("communication"): "communication",
    skill_uri("teamwork"): "teamwork",
    skill_uri("english"): "English",
    skill_uri("problem-solving"): "problem solving",
    skill_uri("excel"): "Microsoft Excel",
}


SECTORS = {
    "6201": "Computer programming activities",
    "6202": "Computer consultancy activities",
    "6419": "Other monetary intermediation",
    "7022": "Business and other management consultancy activities",
    "7112": "Engineering activities and related technical consultancy",
    "2910": "Manufacture of motor vehicles",
    "2829": "Manufacture of other general-purpose machinery",
    "8610": "Hospital activities",
    "8411": "General public administration activities",
    "5510": "Hotels and similar accommodation",
}


ROLES = {
    "software_engineer": {
        "title": "Software Engineer",
        "occupation": "software-developer",
        "occupation_label": "software developer",
        "sector": "6201",
        "description": "Build reliable software applications and digital services using modern engineering practices.",
        "skills": ["software-development", "python", "git", "agile-methods", "docker"],
    },
    "data_analyst": {
        "title": "Data Analyst",
        "occupation": "data-analyst",
        "occupation_label": "data analyst",
        "sector": "6202",
        "description": "Analyse business data, build dashboards and translate evidence into clear recommendations.",
        "skills": ["data-analysis", "sql", "python", "business-intelligence", "excel"],
    },
    "machine_learning_engineer": {
        "title": "Machine Learning Engineer",
        "occupation": "machine-learning-engineer",
        "occupation_label": "machine learning engineer",
        "sector": "6201",
        "description": "Develop artificial intelligence applications and production machine learning services.",
        "skills": ["python", "artificial-intelligence", "machine-learning", "pytorch", "cloud-computing"],
    },
    "cloud_engineer": {
        "title": "Cloud Engineer",
        "occupation": "cloud-engineer",
        "occupation_label": "ICT system developer",
        "sector": "6202",
        "description": "Design cloud computing platforms, container workloads and secure deployment automation.",
        "skills": ["cloud-computing", "docker", "kubernetes", "cybersecurity", "python"],
    },
    "financial_analyst": {
        "title": "Financial Analyst",
        "occupation": "financial-analyst",
        "occupation_label": "financial analyst",
        "sector": "6419",
        "description": "Prepare financial analysis, risk scenarios and management reporting for investment decisions.",
        "skills": ["financial-analysis", "risk-management", "excel", "sql", "communication"],
    },
    "consultant": {
        "title": "Business Consultant",
        "occupation": "management-consultant",
        "occupation_label": "management consultant",
        "sector": "7022",
        "description": "Deliver consulting projects, analyse operating models and support executive stakeholders.",
        "skills": ["consulting", "project-management", "stakeholder-management", "data-analysis", "communication"],
    },
    "manufacturing_engineer": {
        "title": "Manufacturing Engineer",
        "occupation": "manufacturing-engineer",
        "occupation_label": "industrial and production engineer",
        "sector": "2829",
        "description": "Improve manufacturing processes, production quality and industrial equipment performance.",
        "skills": ["manufacturing-processes", "quality-control", "industrial-automation", "cad", "problem-solving"],
    },
    "automotive_engineer": {
        "title": "Automotive Engineer",
        "occupation": "automotive-engineer",
        "occupation_label": "mechanical engineer",
        "sector": "2910",
        "description": "Engineer automotive systems, automated production lines and vehicle quality processes.",
        "skills": ["automotive-engineering", "manufacturing-processes", "industrial-automation", "cad", "quality-control"],
    },
    "sustainability_engineer": {
        "title": "Sustainability Engineer",
        "occupation": "environmental-engineer",
        "occupation_label": "environmental engineer",
        "sector": "7112",
        "description": "Plan sustainability programmes for renewable energy, carbon reduction and circular production.",
        "skills": ["sustainability", "renewable-energy", "carbon-accounting", "circular-economy", "project-management"],
    },
    "healthcare_coordinator": {
        "title": "Healthcare Services Coordinator",
        "occupation": "healthcare-manager",
        "occupation_label": "health services manager",
        "sector": "8610",
        "description": "Coordinate patient care services, healthcare teams and operational improvement initiatives.",
        "skills": ["healthcare-management", "patient-care", "project-management", "communication", "teamwork"],
    },
    "public_policy_officer": {
        "title": "Public Policy Officer",
        "occupation": "policy-officer",
        "occupation_label": "policy administration professional",
        "sector": "8411",
        "description": "Support public administration programmes through policy analysis and stakeholder coordination.",
        "skills": ["public-administration", "policy-analysis", "project-management", "stakeholder-management", "communication"],
    },
    "tourism_manager": {
        "title": "Tourism Operations Manager",
        "occupation": "tourism-manager",
        "occupation_label": "hotel manager",
        "sector": "5510",
        "description": "Manage tourism and hospitality operations, guest experience and seasonal service teams.",
        "skills": ["tourism-management", "hospitality", "customer-service", "project-management", "english"],
    },
}


REGIONS = {
    "ITF4": {
        "name": "Puglia",
        "country": "IT",
        "nuts1": "ITF",
        "nuts2": "ITF4",
        "locations": [("Bari, Italy", "ITF47"), ("Lecce, Italy", "ITF45"), ("Taranto, Italy", "ITF43")],
        "employer_prefix": "Puglia",
        "roles": {
            "tourism_manager": 18,
            "healthcare_coordinator": 16,
            "public_policy_officer": 14,
            "data_analyst": 9,
            "software_engineer": 8,
            "consultant": 7,
            "sustainability_engineer": 7,
            "manufacturing_engineer": 6,
            "financial_analyst": 5,
            "cloud_engineer": 4,
            "automotive_engineer": 3,
            "machine_learning_engineer": 3,
        },
        "boost": ["tourism-management", "healthcare-management", "public-administration", "project-management", "sql"],
    },
    "ITC4": {
        "name": "Lombardia",
        "country": "IT",
        "nuts1": "ITC",
        "nuts2": "ITC4",
        "locations": [("Milano, Italy", "ITC4C"), ("Bergamo, Italy", "ITC46"), ("Brescia, Italy", "ITC47")],
        "employer_prefix": "Lombardia",
        "roles": {
            "software_engineer": 15,
            "financial_analyst": 15,
            "manufacturing_engineer": 14,
            "data_analyst": 11,
            "consultant": 8,
            "cloud_engineer": 8,
            "machine_learning_engineer": 7,
            "automotive_engineer": 7,
            "sustainability_engineer": 6,
            "healthcare_coordinator": 4,
            "public_policy_officer": 3,
            "tourism_manager": 2,
        },
        "boost": ["software-development", "financial-analysis", "manufacturing-processes", "sql", "business-intelligence"],
    },
    "DE30": {
        "name": "Berlin",
        "country": "DE",
        "nuts1": "DE3",
        "nuts2": "DE30",
        "locations": [
            ("Berlin Mitte, Germany", "DE300"),
            ("Berlin Friedrichshain-Kreuzberg, Germany", "DE300"),
            ("Berlin Charlottenburg-Wilmersdorf, Germany", "DE300"),
        ],
        "employer_prefix": "Berlin",
        "roles": {
            "software_engineer": 16,
            "machine_learning_engineer": 16,
            "cloud_engineer": 15,
            "data_analyst": 12,
            "consultant": 8,
            "financial_analyst": 7,
            "tourism_manager": 6,
            "sustainability_engineer": 5,
            "manufacturing_engineer": 5,
            "healthcare_coordinator": 4,
            "automotive_engineer": 3,
            "public_policy_officer": 3,
        },
        "boost": ["python", "artificial-intelligence", "cloud-computing", "docker", "cybersecurity"],
    },
    "DE21": {
        "name": "Oberbayern",
        "country": "DE",
        "nuts1": "DE2",
        "nuts2": "DE21",
        "locations": [("Munich, Germany", "DE212"), ("Ingolstadt, Germany", "DE211"), ("Rosenheim, Germany", "DE213")],
        "employer_prefix": "Bavaria",
        "roles": {
            "automotive_engineer": 18,
            "manufacturing_engineer": 17,
            "sustainability_engineer": 10,
            "software_engineer": 10,
            "cloud_engineer": 8,
            "data_analyst": 8,
            "consultant": 8,
            "machine_learning_engineer": 6,
            "financial_analyst": 5,
            "healthcare_coordinator": 4,
            "public_policy_officer": 3,
            "tourism_manager": 3,
        },
        "boost": ["automotive-engineering", "manufacturing-processes", "industrial-automation", "quality-control", "cad"],
    },
    "FR10": {
        "name": "Ile-de-France",
        "country": "FR",
        "nuts1": "FR1",
        "nuts2": "FR10",
        "locations": [("Paris, France", "FR101"), ("Boulogne-Billancourt, France", "FR105"), ("Nanterre, France", "FR105")],
        "employer_prefix": "Ile-de-France",
        "roles": {
            "financial_analyst": 15,
            "data_analyst": 15,
            "consultant": 14,
            "software_engineer": 12,
            "machine_learning_engineer": 8,
            "cloud_engineer": 7,
            "public_policy_officer": 7,
            "tourism_manager": 6,
            "sustainability_engineer": 5,
            "healthcare_coordinator": 4,
            "manufacturing_engineer": 4,
            "automotive_engineer": 3,
        },
        "boost": ["financial-analysis", "data-analysis", "consulting", "business-intelligence", "stakeholder-management"],
    },
    "FRK2": {
        "name": "Rhone-Alpes",
        "country": "FR",
        "nuts1": "FRK",
        "nuts2": "FRK2",
        "locations": [("Lyon, France", "FRK26"), ("Grenoble, France", "FRK24"), ("Saint-Etienne, France", "FRK25")],
        "employer_prefix": "Rhone-Alpes",
        "roles": {
            "manufacturing_engineer": 16,
            "sustainability_engineer": 15,
            "automotive_engineer": 12,
            "data_analyst": 9,
            "software_engineer": 8,
            "consultant": 8,
            "cloud_engineer": 7,
            "machine_learning_engineer": 5,
            "financial_analyst": 5,
            "tourism_manager": 5,
            "healthcare_coordinator": 5,
            "public_policy_officer": 5,
        },
        "boost": ["manufacturing-processes", "sustainability", "renewable-energy", "industrial-automation", "circular-economy"],
    },
}


YEAR_WEIGHTS = {2020: 8, 2021: 9, 2022: 10, 2023: 12, 2024: 16, 2025: 20, 2026: 25}
REGION_WEIGHTS = {"ITF4": 14, "ITC4": 19, "DE30": 18, "DE21": 17, "FR10": 18, "FRK2": 14}
ROLE_YEAR_MULTIPLIERS = {
    2020: {
        "software_engineer": 0.72,
        "data_analyst": 0.68,
        "machine_learning_engineer": 0.35,
        "cloud_engineer": 0.52,
        "financial_analyst": 0.92,
        "consultant": 0.88,
        "manufacturing_engineer": 0.86,
        "automotive_engineer": 0.96,
        "sustainability_engineer": 0.38,
        "healthcare_coordinator": 1.22,
        "public_policy_officer": 1.16,
        "tourism_manager": 0.62,
    },
    2021: {
        "software_engineer": 0.78,
        "data_analyst": 0.74,
        "machine_learning_engineer": 0.42,
        "cloud_engineer": 0.60,
        "financial_analyst": 0.94,
        "consultant": 0.91,
        "manufacturing_engineer": 0.91,
        "automotive_engineer": 1.00,
        "sustainability_engineer": 0.44,
        "healthcare_coordinator": 1.18,
        "public_policy_officer": 1.13,
        "tourism_manager": 0.72,
    },
    2022: {
        "software_engineer": 0.84,
        "data_analyst": 0.80,
        "machine_learning_engineer": 0.50,
        "cloud_engineer": 0.66,
        "financial_analyst": 0.96,
        "consultant": 0.95,
        "manufacturing_engineer": 0.95,
        "automotive_engineer": 1.04,
        "sustainability_engineer": 0.51,
        "healthcare_coordinator": 1.10,
        "public_policy_officer": 1.10,
        "tourism_manager": 0.80,
    },
    2023: {
        "software_engineer": 0.90,
        "data_analyst": 0.86,
        "machine_learning_engineer": 0.60,
        "cloud_engineer": 0.72,
        "financial_analyst": 0.98,
        "consultant": 0.98,
        "manufacturing_engineer": 0.98,
        "automotive_engineer": 1.08,
        "sustainability_engineer": 0.59,
        "healthcare_coordinator": 1.02,
        "public_policy_officer": 1.09,
        "tourism_manager": 0.86,
    },
    2024: {
        "software_engineer": 0.95,
        "data_analyst": 0.92,
        "machine_learning_engineer": 0.70,
        "cloud_engineer": 0.78,
        "financial_analyst": 1.00,
        "consultant": 1.02,
        "manufacturing_engineer": 1.00,
        "automotive_engineer": 1.12,
        "sustainability_engineer": 0.68,
        "healthcare_coordinator": 0.96,
        "public_policy_officer": 1.08,
        "tourism_manager": 0.92,
    },
    2025: {
        "software_engineer": 1.05,
        "data_analyst": 1.08,
        "machine_learning_engineer": 1.00,
        "cloud_engineer": 1.02,
        "financial_analyst": 1.00,
        "consultant": 1.00,
        "manufacturing_engineer": 1.03,
        "automotive_engineer": 1.00,
        "sustainability_engineer": 1.00,
        "healthcare_coordinator": 1.03,
        "public_policy_officer": 1.00,
        "tourism_manager": 1.04,
    },
    2026: {
        "software_engineer": 1.18,
        "data_analyst": 1.24,
        "machine_learning_engineer": 1.52,
        "cloud_engineer": 1.38,
        "financial_analyst": 1.03,
        "consultant": 0.98,
        "manufacturing_engineer": 1.08,
        "automotive_engineer": 0.88,
        "sustainability_engineer": 1.48,
        "healthcare_coordinator": 1.12,
        "public_policy_officer": 0.94,
        "tourism_manager": 1.15,
    },
}
TREND_PROBABILITIES = {
    "artificial-intelligence": {
        2020: 0.02,
        2021: 0.03,
        2022: 0.04,
        2023: 0.055,
        2024: 0.07,
        2025: 0.11,
        2026: 0.17,
    },
    "cloud-computing": {
        2020: 0.06,
        2021: 0.075,
        2022: 0.09,
        2023: 0.105,
        2024: 0.12,
        2025: 0.18,
        2026: 0.25,
    },
    "sustainability": {
        2020: 0.04,
        2021: 0.05,
        2022: 0.065,
        2023: 0.08,
        2024: 0.09,
        2025: 0.13,
        2026: 0.18,
    },
}
ROLE_EMPLOYER_GROUPS = {
    "software_engineer": "technology",
    "data_analyst": "technology",
    "machine_learning_engineer": "technology",
    "cloud_engineer": "technology",
    "financial_analyst": "finance",
    "consultant": "consulting",
    "manufacturing_engineer": "industry",
    "automotive_engineer": "industry",
    "sustainability_engineer": "sustainability",
    "healthcare_coordinator": "healthcare",
    "public_policy_officer": "public",
    "tourism_manager": "tourism",
}

EMPLOYER_SUFFIXES = {
    "technology": ["Digital Labs", "Cloud Systems"],
    "finance": ["Capital Partners", "Risk Analytics"],
    "consulting": ["Advisory Group", "Strategy Partners"],
    "industry": ["Industrial Works", "Automation Systems"],
    "sustainability": ["Green Transition", "Renewable Solutions"],
    "healthcare": ["Health Services", "Care Network"],
    "public": ["Public Innovation Agency", "Policy Institute"],
    "tourism": ["Hospitality Group", "Tourism Services"],
}


def allocate_counts(total: int, weights: dict, minimum: int = 0) -> dict:
    if not weights:
        return {}
    if total < minimum * len(weights):
        minimum = 0
    weight_total = sum(weights.values())
    remaining = total - (minimum * len(weights))
    exact = {key: remaining * weight / weight_total for key, weight in weights.items()}
    counts = {key: minimum + int(value) for key, value in exact.items()}
    remainder = total - sum(counts.values())
    order = sorted(weights, key=lambda key: exact[key] - int(exact[key]), reverse=True)
    for key in order[:remainder]:
        counts[key] += 1
    return counts


def random_date(rng: random.Random, year: int, end_date: date) -> date:
    first = date(year, 1, 1)
    last = min(date(year, 12, 31), end_date)
    span = max((last - first).days, 0)
    return first + timedelta(days=rng.randint(0, span))


def unique_skills(slugs: list[str]) -> list[str]:
    return [skill_uri(slug) for slug in dict.fromkeys(slugs)]


def role_weights_for_year(region: dict, year: int) -> dict[str, float]:
    multipliers = ROLE_YEAR_MULTIPLIERS[year]
    return {
        role_key: base_weight * multipliers[role_key]
        for role_key, base_weight in region["roles"].items()
    }


def employer_for_job(region_code: str, region: dict, role_key: str, sequence: int) -> tuple[int, str]:
    employer_group = ROLE_EMPLOYER_GROUPS[role_key]
    group_index = list(EMPLOYER_SUFFIXES).index(employer_group)
    variants = EMPLOYER_SUFFIXES[employer_group]
    variant_index = sequence % len(variants)
    employer_id = 1000 + (list(REGIONS).index(region_code) * 100) + (group_index * 10) + variant_index
    employer_name = f"{region['employer_prefix']} {variants[variant_index]}"
    return employer_id, employer_name


def build_job(
    rng: random.Random,
    job_id: int,
    year: int,
    end_date: date,
    region_code: str,
    role_key: str,
    sequence: int,
) -> dict:
    region = REGIONS[region_code]
    role = ROLES[role_key]
    location, nuts3 = region["locations"][sequence % len(region["locations"])]
    organization_id, organization_name = employer_for_job(region_code, region, role_key, sequence)

    base_skills = list(role["skills"])
    extra_skills = []
    for boosted_skill in region["boost"]:
        if rng.random() < 0.34:
            extra_skills.append(boosted_skill)
    for trending_skill, yearly_probability in TREND_PROBABILITIES.items():
        if rng.random() < yearly_probability[year]:
            extra_skills.append(trending_skill)
    if rng.random() < 0.58:
        extra_skills.append("communication")
    if rng.random() < 0.46:
        extra_skills.append("teamwork")
    if rng.random() < 0.31:
        extra_skills.append("english")
    if rng.random() < 0.29:
        extra_skills.append("problem-solving")

    extra_skills = [slug for slug in dict.fromkeys(extra_skills) if slug not in base_skills]
    rng.shuffle(extra_skills)
    skill_slugs = base_skills + extra_skills[:3]

    labels = [SKILLS[skill_uri(slug)] for slug in skill_slugs]
    description = role["description"]
    if "artificial-intelligence" in skill_slugs and "artificial intelligence" not in description.lower():
        description += " The role contributes to artificial intelligence adoption and responsible automation."
    description += f" Key skills include {', '.join(labels)}."

    sector_code = role["sector"]
    distribution_index = (job_id - 10001) % 100
    experience_level = (
        "Entry-level" if distribution_index < 22
        else "Mid-level" if distribution_index < 70
        else "Senior" if distribution_index < 94
        else "Manager"
    )
    return {
        "id": job_id,
        "organization": organization_id,
        "organization_name": organization_name,
        "title": role["title"],
        "description": description,
        "experience_level": experience_level,
        "type": "Full-time" if distribution_index < 88 else "Part-time",
        "location": location,
        "location_code": region["country"],
        "country_code": region["country"],
        "nuts1": region["nuts1"],
        "nuts2": region["nuts2"],
        "nuts3": nuts3,
        "upload_date": random_date(rng, year, end_date).isoformat(),
        "source": "demo",
        "source_id": f"demo-{job_id}",
        "skills": unique_skills(skill_slugs),
        "occupations": [occupation_uri(role["occupation"])],
        "sectors": [
            {
                "code": f"{NACE_BASE}/{sector_code}",
                "label": SECTORS[sector_code],
            }
        ],
    }


def generate_jobs(count: int, seed: int, end_date: date) -> list[dict]:
    rng = random.Random(seed)
    year_weights = {year: weight for year, weight in YEAR_WEIGHTS.items() if year <= end_date.year}
    year_counts = allocate_counts(count, year_weights, minimum=1)
    jobs = []
    next_id = 10001
    for year in sorted(year_counts):
        region_counts = allocate_counts(year_counts[year], REGION_WEIGHTS, minimum=1)
        for region_code in REGIONS:
            region = REGIONS[region_code]
            role_counts = allocate_counts(
                region_counts[region_code],
                role_weights_for_year(region, year),
                minimum=1,
            )
            role_schedule = [
                role_key
                for role_key, role_count in role_counts.items()
                for _ in range(role_count)
            ]
            rng.shuffle(role_schedule)
            for sequence, role_key in enumerate(role_schedule):
                jobs.append(
                    build_job(
                        rng,
                        next_id,
                        year,
                        end_date,
                        region_code,
                        role_key,
                        sequence,
                    )
                )
                next_id += 1
    rng.shuffle(jobs)
    return jobs


def occupation_catalog() -> dict[str, str]:
    return {
        occupation_uri(role["occupation"]): role["occupation_label"]
        for role in ROLES.values()
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="demo/data/synthetic_jobs.json")
    parser.add_argument("--count", type=int, default=8000)
    parser.add_argument("--seed", type=int, default=20261007)
    parser.add_argument("--end-date", type=date.fromisoformat, default=date(2026, 10, 7))
    parser.add_argument(
        "--if-missing",
        action="store_true",
        help="Keep an existing non-empty dataset instead of replacing it.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = Path(args.output)
    if args.if_missing and output.exists() and output.stat().st_size > 0:
        print(f"Synthetic dataset already present: {output}")
        return
    if args.count < 1:
        raise ValueError("--count must be greater than zero")

    jobs = generate_jobs(args.count, args.seed, args.end_date)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(jobs, stream, ensure_ascii=False, separators=(",", ":"))
    temporary.replace(output)
    print(f"Generated {len(jobs)} synthetic jobs in {output}")


if __name__ == "__main__":
    main()
