"""Audit bundled team identity labels without adding historical unit fixtures."""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
# Accepted geographic abbreviations, including established source conventions.
COMMON = {
    "49ers": ("SF", "SFO"), "Bears": ("CHI",), "Bengals": ("CIN",),
    "Bills": ("BUF",), "Broncos": ("DEN",), "Browns": ("CLE",),
    "Buccaneers": ("TB", "TAM"), "Chiefs": ("KC", "KAN"),
    "Cowboys": ("DAL",), "Dolphins": ("MIA",), "Eagles": ("PHI",),
    "Falcons": ("ATL",), "Giants": ("NYG",), "Jets": ("NYJ",),
    "Lions": ("DET",), "Packers": ("GB", "GNB"), "Patriots": ("NE", "NWE"),
    "Saints": ("NO", "NOR"), "Seahawks": ("SEA",), "Steelers": ("PIT",),
    "Vikings": ("MIN",),
}


def audit(root: Path = ROOT / "seasons") -> list[str]:
    """Return errors for missing teams, wrong nicknames or era-mismatched labels."""
    errors = []
    for year in (1977, 1983, 2024):
        identities = dict(COMMON)
        identities.update({
            "Cardinals": ("ARI",) if year == 2024 else ("STL",),
            "Chargers": ("LAC",) if year == 2024 else ("SD", "SDG"),
            "Colts": ("IND",) if year == 2024 else ("BAL",),
            "Raiders": {1977: ("OAK",), 1983: ("LA",), 2024: ("LV",)}[year],
            "Rams": ("LAR", "RAM", "LA"),
        })
        if year == 2024:
            identities.update({
                "Commanders": ("WAS", "WSH"), "Jaguars": ("JAX", "JAC"),
                "Panthers": ("CAR",), "Ravens": ("BAL",),
                "Texans": ("HOU",), "Titans": ("TEN",),
            })
        else:
            identities.update({"Oilers": ("HOU",), "Redskins": ("WAS", "WSH")})
        directory = root / str(year)
        actual = {path.parent.name for path in directory.glob("*/team.yaml")}
        if actual != identities.keys():
            errors.append(f"{year}: missing {sorted(identities.keys() - actual)}, "
                          f"unexpected {sorted(actual - identities.keys())}")
        for team, abbreviations in identities.items():
            path = directory / team / "team.yaml"
            if not path.exists():
                continue
            data = yaml.safe_load(path.read_text())
            expected = [f"{abbr} '{year % 100:02d}" for abbr in abbreviations]
            if data.get("short_name") not in expected:
                errors.append(f"{year}/{team}: {data.get('short_name')!r}; expected {expected}")
            for key in ("team_name", "nickname"):
                if data.get(key) != team:
                    errors.append(f"{year}/{team}: unexpected {key} {data.get(key)!r}")
    for team, name, short in (
        ("Ironclads", "Harbor Bay Ironclads", "HBI"),
        ("Thunderhawks", "Metro City Thunderhawks", "MCT"),
    ):
        path = root / "2026" / team / "team.yaml"
        data = yaml.safe_load(path.read_text())
        if (data.get("team_name"), data.get("short_name")) != (name, short):
            errors.append(f"2026/{team}: incorrect public sample identity")
    return errors


if __name__ == "__main__":
    failures = audit()
    print("\n".join(failures) if failures else "PASS: all 90 bundled team identities")
    sys.exit(bool(failures))
