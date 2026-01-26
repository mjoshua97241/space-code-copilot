Use VLM where **OCR stops**: structure, semantics, and reasoning.

Right now you’re mixing two separate concerns:

* “How do I get numbers out of the drawing?” → OCR / geometry
* “How do I turn what I see into *code-relevant* structure + explanations?” → VLM

You don’t need VLM to read “12.0 m²”.
You need VLM to **understand what that 12.0 m² belongs to and what it means** in the context of building code.

Use that, and make *that* the feature.

---

## 1. What OCR gives you vs what VLM gives you

**Plain OCR / low-level CV** can give you:

* Text tokens: `"Room 101"`, `"Office"`, `"12.0 m²"`, `"3.0"`, `"4.0"`.
* Maybe table-like extractions, if you invest in heuristics.

It does **not**:

* Decide which numbers belong to which room.
* Understand that “12.0 m²” is usable area, not some random note.
* Understand that “Office” = room type with specific code rules.
* Combine dimensions (“3.0m x 4.0m”) into area and then into a violation explanation.
* Answer: “Is this particular room non-compliant, and why?”

A **VLM** (or multimodal LLM call) can:

* See **the whole composition**:

  * box shape + label “Office 101” + dimension strings around it.

* Produce **structured JSON** in one hit:

  ```json
  {
    "rooms": [
      {
        "name": "Office 101",
        "type": "office",
        "level": "L2",
        "width_m": 3.0,
        "depth_m": 4.0,
        "area_m2": 12.0,
        "notes": "single occupant office"
      }
    ]
  }
  ```

* And optionally already apply **rules**:

  ```json
  {
    "rooms": [...],
    "issues": [
      {
        "element_id": "Office 101",
        "rule_id": "OFFICE_MIN_AREA",
        "message": "Office 101 appears to be 12.0 m², below the 13.0 m² requirement."
      }
    ]
  }
  ```

That’s beyond OCR. That’s **vision + domain reasoning + structuring**.

---

## 2. Reframe the VLM feature around *what only a VLM reasonably does*

Stop selling “VLM does geometry better than CV”.
Sell this:

> “Upload a blueprint → the system visually understands rooms (labels, type, dimensions) and runs code checks, with explanations, with almost zero manual setup.”

Concrete, VLM-centric functions:

1. **Room semantic extraction**

   * Read room labels: “Office 101”, “Meeting Room”, “Server”, “WC”.
   * Classify them into your rule types: `office`, `meeting`, `support`, `toilet`, etc.
   * Combine scattered text into a consistent room record (even if labels are not in a nice table).

2. **Dimension-aware inference**

   * Plans often have **dimensions**, not areas:

     * “3.0” along one side, “4.0” along another, tiny arrow markers.
   * OCR alone doesn’t know which dimension belongs to which wall.
   * VLM can be prompted:

     * “For each room, read the dimensions that appear as arrows on its sides and compute width/height/area.”
   * Area is then either:

     * computed by you from the JSON dimensions, or
     * requested explicitly in the VLM’s JSON output.

3. **Visual + code-aware explanation**

   * When you highlight Office 101 and show an issue, the VLM answers:

     * “Office 101 appears to be approximately 3.0 m × 4.0 m (≈ 12.0 m²). The minimum required area for an office in this code is 13.0 m², so this room is undersized.”
   * That explanation comes from:

     * reading the plan,
     * reading your rule thresholds,
     * connecting them.

4. **Cross-check against your CSV / schedule**

   * CSV pipeline is ground truth.
   * VLM pipeline is “visual sanity check”:

     * “Are there rooms in the plan that are not in the schedule?”
     * “Does any office *look* significantly smaller than what the schedule says?”
   * That’s a classic *vision + text consistency* use case, which OCR alone is very painful for.

---

## 3. Make VLM the *front* of the feature, not the math engine

You already have:

* A **compliance engine** that takes `Room` objects with `area_m2` and applies rules.
* A **CSV schedule pipeline** that populates Room objects.

Make the VLM story:

> “Instead of asking the architect to build a special CSV, we let them throw in a plan image, and a multimodal LLM does the heavy lifting of *structuring and interpreting* the plan into something the compliance engine can use.”

Architecture:

* **Path A (ground truth)**
  `CSV → Rooms → check_compliance → Issues`

* **Path B (VLM)**
  `Image → VLM → ExtractedDesign (rooms with type + dimensions / area) → Rooms → check_compliance → Issues`

The **VLM is the differentiator** in Path B, not the pixel-area math.

If you still want geometry+scale:

* Use OpenCV to propose rough polygons,
* Use VLM to:

  * assign names / types to those regions,
  * read dimension annotations near those polygons,
  * refine area estimates.

But the “selling point” to the bootcamp is:

* You integrated a **multimodal LLM**,
* You designed a **structured JSON schema**,
* You built a pipeline from **blueprint image → structured room data → code issues**.

That’s the lesson application.

---

## 4. How to describe this in your MVP narrative

Phrase it like this, without overclaiming:

```text
Multimodal Feature: Visual Room Extraction and Code Pre-check

The user uploads an architectural floor plan image.
A vision language model analyzes the plan and returns a structured JSON
representation of rooms:

- room name / label (e.g. "Office 101", "Meeting Room"),
- room type mapped to our internal categories (office, meeting, support),
- approximate geometry information (dimensions or area in m²),
- optional notes for ambiguous cases.

We convert this JSON into our Room models and feed it into the same
compliance engine used for the CSV schedule.

This shows how a vision LLM can reduce setup friction: instead of
manually preparing a schedule, the architect can start from a blueprint
image and still get code-related feedback and explanations.

The CSV-based path remains the primary ground truth for accuracy, while
the multimodal path is an experimental but high-leverage entry point that
demonstrates the value of multimodal LLMs in AEC.
```

This is honest, VLM-centric, and directly showcases the course’s multimodal theme.

You don’t win points for pretending the VLM is a perfect geometric engine.
You win points for designing a **clean, structured multimodal pipeline** that links blueprint → structured data → code reasoning, and for measuring how close that is to your CSV ground truth.
