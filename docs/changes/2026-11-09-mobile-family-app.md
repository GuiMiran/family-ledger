# Mobile family application · contract before implementation

Owner authorizes adopting the supplied visual reference: white cards, soft
background, bottom navigation and prominent receipt capture. Reuse current
private profiles, receipt persistence and comparator; do not restore an older
ZIP, owner data or mock results into the live application.

1. Five primary views: Home, Pantry, Capture, Menus and Savings. Comparator and
   profile settings remain accessible without losing functionality.
2. Views read authenticated APIs. Empty receipts, stock and charts remain empty;
   no invented expenses, savings, menus, expiry predictions or freezer stock.
3. Home shows confirmed spending and pending receipt counts from available data;
   pantry shows the existing confirmed-purchase projection explicitly, not a
   physical consumption balance. Freezer/consumption remain pending capabilities.
4. Capture supports real image extraction through an OCR port. Local Tesseract
   is the initial adapter, bounded by input bytes, image dimensions and timeout.
   Do not send images to an external AI service implicitly. JPEG/PNG/WebP only;
   unsupported/illegible receipts ask for another capture, never full manual entry.
5. Extraction is authenticated and has no database side effects. Temporary input
   is cleaned up. It returns a draft and genuinely ambiguous fields. Original
   image retention is not claimed until private object storage is implemented.
6. Review lets the family resolve ambiguous supported fields, keeps detected lines
   visible, and persists through existing idempotent commands. Unresolved review
   cannot be labelled confirmed. Financial validation remains server authoritative.
7. Menus and advanced savings clearly explain availability; no simulated action
   reports a successful freeze/menu/achieved saving. No global personal defaults.
8. Validate OCR failure boundaries, no unintended writes, family access, frontend
   compilation, existing regression and PostgreSQL. Source docs/trace/baseline
   record the intentional change; no history rewrite or deployment implied by UI.
