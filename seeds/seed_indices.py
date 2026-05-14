"""
Seed RBI/JPC index data extracted from BCT-24-25-252 workbook (Dec-2024 base month).

Coverage: Dec-2024 through Dec-2025 (13 months).
RBI series: all 13 months present.
JPC series: Dec-2024 (base) + Q2-2025 (Apr-Jun) + Q4-2025 (Oct-Dec) only.
  Q1 and Q3 JPC values not published in this workbook — add from JPC publications when available.

Run: uv run python seeds/seed_indices.py (from repo root or backend/)
Idempotent: INSERT ... ON CONFLICT DO NOTHING
"""

import asyncio
import os
import sys
from datetime import date
from pathlib import Path

# Allow running from repo root or backend/
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env", override=True)

import asyncpg
from sqlalchemy.engine.url import make_url

SERIES = [
    ("labour",           "RBI"),
    ("plant_machinery",  "RBI"),
    ("fuel",             "RBI"),
    ("other_materials",  "RBI"),
    ("cement",           "RBI"),
    ("steel_tmt",        "JPC"),
    ("steel_angles",     "JPC"),
    ("steel_plates",     "JPC"),
    ("steel_other_sections", "JPC"),
]

# Rows: (month_str, labour, plant_machinery, fuel, other_materials, cement,
#         steel_tmt, steel_angles, steel_plates, steel_other_sections)
# None = no observation for that series/month in this workbook
OBSERVATIONS = [
    # Base month
    ("2024-12", 143.7,  160.0,   160.48, 155.7,  130.2,  57812.5,  58000.0,   57370.0,   57727.5),
    # Q1 2025 — RBI only (JPC not in workbook for this quarter)
    ("2025-01", 143.2,  161.0,   160.48, 155.0,  130.2,  None,     None,      None,      None),
    ("2025-02", 142.8,  161.4,   160.48, 154.16, 132.8,  None,     None,      None,      None),
    ("2025-03", 143.0,  161.6,   160.48, 154.8,  131.0,  None,     None,      None,      None),
    # Q2 2025 — both RBI and JPC (1st bill: measurement_date 2025-06-18)
    ("2025-04", 143.5,  162.3,   160.48, 154.2,  130.5,  61917.5,  61133.33,  62902.5,   61984.44),
    ("2025-05", 144.0,  162.5,   160.51, 153.7,  133.0,  59765.0,  60928.33,  63637.5,   61443.61),
    ("2025-06", 145.0,  162.7,   160.53, 153.7,  132.8,  56690.0,  59205.0,   62385.0,   59426.67),
    # Q3 2025 — RBI only (JPC not in workbook for this quarter)
    ("2025-07", 146.5,  163.0,   160.52, 154.4,  133.1,  None,     None,      None,      None),
    ("2025-08", 147.1,  162.16,  160.53, 155.2,  133.5,  None,     None,      None,      None),
    ("2025-09", 147.3,  162.16,  160.53, 154.16, 133.7,  None,     None,      None,      None),
    # Q4 2025 — both RBI and JPC (2nd bill: measurement_date 2025-11-04)
    ("2025-10", 147.7,  163.0,   160.53, 155.1,  131.3,  52752.5,  55820.0,   59850.0,   56140.83),
    ("2025-11", 148.2,  163.3,   160.53, 156.2,  130.5,  51980.0,  54800.0,   58202.5,   54994.17),
    ("2025-12", 148.2,  163.1,   160.53, 157.2,  130.3,  52435.0,  54476.67,  56785.0,   54565.56),
]

SERIES_NAMES = [
    "labour", "plant_machinery", "fuel", "other_materials", "cement",
    "steel_tmt", "steel_angles", "steel_plates", "steel_other_sections",
]


async def seed():
    raw = os.environ["DATABASE_URL"].strip()
    u = make_url(raw)

    conn = await asyncpg.connect(
        host=u.host,
        port=u.port,
        user=u.username,
        password=str(u.password),
        database=u.database,
    )

    try:
        # Upsert series
        series_ids = {}
        for name, source in SERIES:
            row = await conn.fetchrow(
                """
                INSERT INTO index_series (name, source_publication)
                VALUES ($1, $2::index_source)
                ON CONFLICT (name) DO UPDATE SET source_publication = EXCLUDED.source_publication
                RETURNING id
                """,
                name, source,
            )
            series_ids[name] = row["id"]
            print(f"  series: {name} ({source}) → {row['id']}")

        # Insert observations
        inserted = 0
        skipped = 0
        for obs in OBSERVATIONS:
            month_str = obs[0]
            year, month = month_str.split("-")
            month_date = date(int(year), int(month), 1)
            values = dict(zip(SERIES_NAMES, obs[1:]))

            for series_name, value in values.items():
                if value is None:
                    continue
                result = await conn.execute(
                    """
                    INSERT INTO index_observations (series_id, month, value, source_ref)
                    VALUES ($1, $2::date, $3, $4)
                    ON CONFLICT (series_id, month) DO NOTHING
                    """,
                    series_ids[series_name],
                    month_date,
                    value,
                    "BCT-24-25-252 workbook",
                )
                if result == "INSERT 0 1":
                    inserted += 1
                else:
                    skipped += 1

        total = sum(1 for obs in OBSERVATIONS for v in obs[1:] if v is not None)
        print(f"\nDone. {inserted} inserted, {skipped} already existed. {total} total observations.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
