from dataclasses import dataclass


@dataclass(frozen=True)
class Bucket:
    key: str
    label: str
    patterns: tuple[str, ...]
    """SQL LIKE patterns, matched against the lowercase concept."""


# In order: a concept goes to the first bucket that matches it, so it is
# counted once. From Laravel's UtilitiesReport and TrackerService.
BUCKETS = (
    Bucket("pool", "Pool", ("%pool%",)),
    Bucket("landscaping", "Landscaping", ("%landscaping%", "frondoso", "greennature")),
    Bucket("cfe", "CFE", ("cfe",)),
    Bucket("property_mgmt", "Property Mgmt", ("property management",)),
    Bucket("pest_control", "Pest Control", ("%pest%", "%fumig%", "%plagas%", "mep")),
    Bucket("internet", "Internet", ("telmex%", "%internet%", "starlink")),
    Bucket("water", "Water", ("%water%", "%omsapas%", "%pipas%")),
    Bucket(
        "gas",
        "Gas",
        (
            "caligas",
            "cali gas",
            "global gas",
            "globa gas",
            "glogal gas",
            "temogas",
            "propane gas",
            "baja gas",
            "diesgas",
        ),
    ),
    Bucket("hoa", "HOA", ("%hoa%",)),
    Bucket("housekeeping", "Housekeeping", ("housekeeping%",)),
    Bucket("staff", "Staff", ("staff",)),
)
BY_KEY = {bucket.key: bucket for bucket in BUCKETS}
UTILITIES = tuple(b.key for b in BUCKETS if b.key not in {"housekeeping", "staff"})
"""What the utilities breakdown shows unless asked for others."""
