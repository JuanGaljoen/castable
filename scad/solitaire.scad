// ============================================================================
// Parametric solitaire ring template  (RNG-1)
//
// Lost-wax castable by construction: one watertight manifold, min wall 0.8mm,
// min prong tip 0.7mm. Constraints are enforced in geometry via max() clamps,
// not as UI hints. The seat is modelled empty (no stone is cast).
//
// Drive headless, e.g.:
//   openscad -D 'prong_count=6' -D 'inner_diameter=18' -o ring.stl solitaire.scad
//
// Orientation: finger axis = Z (band in the XY plane). The setting points
// radially outward along +X, so the bare band's -X extent equals outer_r.
// ============================================================================

// ---- User parameters (overridable via -D) ---------------------------------
inner_diameter = 16.5;   // finger size (mm) — US6
band_width     = 2.2;    // shank width along finger axis (mm), at the base
band_thickness = 1.9;    // shank radial thickness (mm, >= 0.8), at the base
stone_diameter = 6.5;    // basket / seat diameter (mm)
stone_height   = 4;      // stone height (mm)
prong_count    = 6;      // 4 or 6 only
setting_height = 6;      // head height: band shoulder -> prong tip (mm)

// Extra shaping control (beyond the canonical 7) for the tapered shank.
shank_taper    = 1.7;    // shoulder flare: cross-section scale toward the head

$fn = 64;                // facet resolution (overridden by render harness)

// Mesh resolution scales with $fn, so tests render fast at low $fn while hero
// renders stay smooth at high $fn — topology (and thus castability) is identical.
RES_A = max(round($fn * 2.2), 48);   // tapered-band segments around the ring
RES_B = max(round($fn * 0.75), 14);  // tapered-band cross-section segments
WFN   = max(round($fn * 0.40), 10);  // claw wire / bead facets
CFN   = max(round($fn * 1.10), 24);  // seat-ring revolve facets

// ---- Casting constraints (hard limits, mm) --------------------------------
MIN_WALL      = 0.8;     // minimum wall thickness everywhere
MIN_PRONG_TIP = 0.7;     // minimum prong tip diameter
OVERLAP       = 0.4;     // module interpenetration for clean manifold unions

// ---- Clamp inputs so geometry is always castable --------------------------
id_c = max(inner_diameter, 5);        // never degenerate / inverted
bt_c = max(band_thickness, MIN_WALL); // min wall thickness  (AC3)
bw_c = max(band_width, MIN_WALL);
sd_c = max(stone_diameter, 1);
sht_c = max(stone_height, 0.5);
gh_c = max(setting_height, MIN_WALL); // gallery height

taper_c = max(shank_taper, 1.0);      // never taper below the base size
inner_r = id_c / 2;
outer_r = inner_r + bt_c;             // bare band outer radius at the base
head_r  = inner_r + bt_c * taper_c;   // flared outer radius at the head shoulder

// Tapered-shank helpers: head_t == 1 at the head (a=0), 0 at the base (a=180).
function tlerp(a, b, t) = a + (b - a) * t;
function head_t(a) = pow((1 + cos(a)) / 2, 1.5);

// ---- prong_count: 4 or 6 only, else snap to 4 + warn  (AC5) ---------------
valid_prongs = (prong_count == 4 || prong_count == 6);
prong_n = valid_prongs ? prong_count : 4;
if (!valid_prongs)
    echo(str("WARNING: prong_count must be 4 or 6; snapping to 4 (got ",
             prong_count, ")"));

// ---- Oversized stone warning (valid but ungainly)  (AC6) ------------------
if (sd_c >= id_c * 0.9)
    echo(str("WARNING: stone_diameter (", sd_c,
             ") is large for inner_diameter (", id_c,
             "); geometry is valid but may be ungainly"));

// ---- Derived setting dimensions (open claw basket) ------------------------
stone_r   = sd_c / 2;
ring_z    = gh_c * 0.5;                     // girdle / seat-ring height above band
claw_rise = gh_c * 0.5;                     // claw rise above the girdle
wire_r    = max(MIN_WALL / 2 + 0.1, 0.5);  // claw wire radius (dia >= 0.8mm)
tip_r     = max(MIN_PRONG_TIP / 2, 0.4);   // claw tip radius (dia >= 0.7mm)  (AC4)
base_r    = max(stone_r * 0.20, MIN_WALL); // basket convergence radius at band
collar_tr = max(MIN_WALL / 2, 0.45);       // seat-ring tube radius (dia >= 0.8mm)

// ============================================================================
// Modules
// ============================================================================

// Shank: tapered round band, built as ONE swept polyhedron — an oval cross
// section revolved around the ring, scaled toward the head (taper_c). A single
// mesh is watertight and cheap (no boolean union of many solids). The inner edge
// stays at inner_r (finger hole); the base section (a=180) is unscaled, so the
// -X extent still equals outer_r and the min-wall check stays valid.
NA = RES_A;   // segments around the ring (scales with $fn)
NB = RES_B;   // segments around the oval cross-section (scales with $fn)

function band_vertex(a, b) =
    let (t  = head_t(a),
         th = tlerp(bt_c, bt_c * taper_c, t),     // radial thickness here
         w  = tlerp(bw_c, bw_c * taper_c, t),     // axial width here
         rc = inner_r + th / 2,
         rr = rc + (th / 2) * cos(b),
         z  = (w / 2) * sin(b))
    [rr * cos(a), rr * sin(a), z];

module shank() {
    pts = [ for (i = [0 : NA - 1], j = [0 : NB - 1])
                band_vertex(i * 360 / NA, j * 360 / NB) ];
    faces = [ for (i = [0 : NA - 1], j = [0 : NB - 1])
                let (i2 = (i + 1) % NA, j2 = (j + 1) % NB,
                     a = i * NB + j, b = i * NB + j2,
                     c = i2 * NB + j, d = i2 * NB + j2)
                each [ [a, c, d], [a, d, b] ] ];
    polyhedron(points = pts, faces = faces, convexity = 6);
}

// segment: a tapered capsule between two points — the smooth, watertight
// building block for the claw wires (hull of two spheres).
module segment(p1, r1, p2, r2) {
    hull() {
        translate(p1) sphere(r = r1, $fn = WFN);
        translate(p2) sphere(r = r2, $fn = WFN);
    }
}

// Gallery: small central peg where the band, claw wires and seat ring converge.
// Kept deliberately small so the head reads as an open basket, not a solid plug;
// its real job is to bind everything into one casting-safe solid.
// Authored in a local +Z frame; setting() places it radially outward.
module gallery() {
    cylinder(h = max(ring_z * 0.4, 1.0) + OVERLAP,
             r1 = base_r + wire_r, r2 = base_r);
}

// Seat: open seat ring (collar) at the girdle that the stone rests on. No solid
// cup — the stone's pavilion hangs through, exactly like a real claw setting.
module seat() {
    translate([0, 0, ring_z])
        rotate_extrude($fn = CFN)
            translate([stone_r, 0, 0])
                circle(r = collar_tr, $fn = WFN);
}

// Prongs: prong_n continuous claw wires. Each converges to the peg near the
// band, sweeps out to the girdle (joining the seat ring), then curls inward
// over the stone, finished with a rounded bead. The gaps between wires give the
// open basket its look.
module prongs() {
    A = [base_r,        0, 0];                          // converged at the band
    B = [stone_r,       0, ring_z];                     // girdle / seat ring
    C = [stone_r,       0, ring_z + claw_rise * 0.55];  // rises near-vertical
    D = [stone_r * 0.88, 0, ring_z + claw_rise];        // slight inward at tip
    for (i = [0 : prong_n - 1]) {
        rotate([0, 0, i * 360 / prong_n]) {
            segment(A, wire_r,        B, wire_r);
            segment(B, wire_r,        C, wire_r * 0.92);
            segment(C, wire_r * 0.92, D, tip_r);
            translate(D) sphere(r = tip_r * 1.45, $fn = WFN);  // claw bead
        }
    }
}

// Place gallery + seat + prongs on the band: local +Z -> global +X.
module setting() {
    translate([head_r - OVERLAP, 0, 0])
        rotate([0, 90, 0]) {
            gallery();
            seat();
            prongs();
        }
}

// ============================================================================
// Assembly: a single watertight manifold
// ============================================================================
module solitaire_ring() {
    union() {
        shank();
        setting();
    }
}

solitaire_ring();
