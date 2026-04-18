"""Test the document upload pipeline with the seed docx."""
import httpx
import asyncio
import json


async def test():
    with open(r"e:\MUM-CR-2024-0847_CrimeScopeSeed.docx", "rb") as f:
        doc_bytes = f.read()

    print("=== STEP 1: Upload Document ===")
    async with httpx.AsyncClient(timeout=120.0) as client:
        files = [
            (
                "docs",
                (
                    "MUM-CR-2024-0847.docx",
                    doc_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            )
        ]
        data = {
            "question": (
                "Based on the Worli Seaface hit-and-run incident, simulate "
                "stakeholder interactions and predict conviction likelihood, "
                "political consequences, and road safety impact."
            )
        }

        r = await client.post(
            "http://127.0.0.1:5001/api/v1/upload/documents",
            files=files,
            data=data,
        )
        print("Status:", r.status_code)
        if r.status_code != 200:
            print("ERROR:", r.text[:500])
            return

        result = r.json()
        print("Response keys:", list(result.keys()))
        case_id = result.get("id", "MISSING")
        print("Case ID:", case_id)
        print("Title:", result.get("title", "?"))
        print("Mode:", result.get("mode", "?"))
        print("Status:", result.get("status", "?"))

        seed = result.get("seed_packet", {})
        if seed:
            print("Seed entities:", len(seed.get("entities", [])))
            print("Seed facts:", len(seed.get("facts", [])))
            print("Seed hypotheses:", len(seed.get("initial_hypotheses", [])))
            print("Seed key_persons:", len(seed.get("key_persons", [])))
            if seed.get("entities"):
                names = [e.get("name", "?") for e in seed["entities"][:5]]
                print("First 5 entities:", names)
            if seed.get("initial_hypotheses"):
                print("Hypotheses:", seed["initial_hypotheses"][:3])
            summary = seed.get("evidence_summary", "")[:300]
            print("Evidence summary:", summary)
        else:
            print("WARNING: No seed_packet in response!")

        print()
        print("=== STEP 2: Verify Case Listed ===")
        r2 = await client.get("http://127.0.0.1:5001/api/v1/cases")
        cases = r2.json()
        print("Total cases:", len(cases))
        for c in cases:
            cid = c.get("id", "?")
            ct = c.get("title", "?")
            cm = c.get("mode", "?")
            print(f"  - {cid}: {ct} (mode={cm})")

        print()
        print("=== STEP 3: Retrieve Case by ID ===")
        r3 = await client.get(f"http://127.0.0.1:5001/api/v1/cases/{case_id}")
        print("Status:", r3.status_code)
        if r3.status_code == 200:
            case_data = r3.json()
            print("Case found:", case_data.get("title"))
            has_seed = "seed_packet" in case_data
            print("Has seed_packet:", has_seed)

        # Save case_id for later
        with open("test_case_id.txt", "w") as f:
            f.write(case_id)
        print()
        print("Case ID saved to test_case_id.txt:", case_id)


if __name__ == "__main__":
    asyncio.run(test())
